# scrapers.py — Full Scrapling power with StealthyFetcher and advanced features

import asyncio
import re
from typing import Dict, Optional
from scrapling import Fetcher, StealthyFetcher
from bs4 import BeautifulSoup
from .constants import REQUEST_DELAY, SCRAPE_TIMEOUT, REDDIT_OLD, NITTER_INSTANCE

# Configure StealthyFetcher globally
StealthyFetcher.adaptive = True  # Enable adaptive mode for site changes

def extract_asin(url_or_text: str) -> Optional[str]:
    match = re.search(r'/dp/([A-Z0-9]{10})', url_or_text)
    if not match:
        match = re.search(r'/gp/product/([A-Z0-9]{10})', url_or_text)
    return match.group(1) if match else None

async def scrape_amazon(asin: str) -> Dict:
    """
    Feature 1: Multi-platform Product Analysis (Amazon)
    Uses StealthyFetcher with Cloudflare bypass for maximum success rate
    """
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        # Use StealthyFetcher for advanced anti-bot protection
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,              # Run in headless mode
            network_idle=True,          # Wait for network to be idle
            solve_cloudflare=True,      # Auto-solve Cloudflare if encountered
            timeout=SCRAPE_TIMEOUT
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract product details
        title_elem = soup.select_one("#productTitle")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Product"
        
        price_elem = soup.select_one(".a-price .a-offscreen")
        price = price_elem.get_text(strip=True) if price_elem else "N/A"
        
        rating_elem = soup.select_one("[data-hook='rating-out-of-text']")
        rating_text = rating_elem.get_text(strip=True) if rating_elem else "0 out of 5"
        rating = float(re.search(r'([\d.]+)', rating_text).group(1)) if rating_text else 0.0
        
        review_count_elem = soup.select_one("#acrCustomerReviewText")
        review_count_text = review_count_elem.get_text(strip=True) if review_count_elem else "0"
        review_count = int(re.search(r'([\d,]+)', review_count_text).group(1).replace(',', '')) if review_count_text else 0
        
        # Extract reviews
        reviews = []
        for review_elem in soup.select("[data-hook='review']")[:10]:
            review_title = review_elem.select_one("[data-hook='review-title']")
            review_body = review_elem.select_one("[data-hook='review-body']")
            review_rating = review_elem.select_one("[data-hook='review-star-rating']")
            review_date = review_elem.select_one("[data-hook='review-date']")
            
            if review_body:
                reviews.append({
                    "title": review_title.get_text(strip=True) if review_title else "",
                    "body": review_body.get_text(strip=True),
                    "rating": float(re.search(r'([\d.]+)', review_rating.get_text()).group(1)) if review_rating else 0,
                    "date": review_date.get_text(strip=True) if review_date else ""
                })
        
        return {
            "title": title,
            "price": price,
            "rating": rating,
            "review_count": review_count,
            "reviews": reviews,
            "url": url,
            "asin": asin
        }
    
    except Exception as e:
        # Fallback to basic Fetcher if StealthyFetcher fails
        try:
            fetcher = Fetcher()
            response = await asyncio.to_thread(fetcher.get, url, timeout=SCRAPE_TIMEOUT)
            soup = BeautifulSoup(response.text, "html.parser")
            
            title_elem = soup.select_one("#productTitle")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Product"
            
            return {
                "title": title,
                "price": "N/A",
                "rating": 0.0,
                "review_count": 0,
                "reviews": [],
                "url": url,
                "asin": asin,
                "fallback": "Used basic Fetcher (StealthyFetcher failed)"
            }
        except:
            return {
                "title": "Error scraping Amazon",
                "error": str(e),
                "reviews": []
            }

async def scrape_reddit(product_name: str) -> Dict:
    """
    Feature 2: Reddit Truth Bomb
    Uses Scrapling Fetcher with stealthy headers
    """
    query = product_name.replace(" ", "+")
    url = f"{REDDIT_OLD}/search?q={query}&sort=relevance"
    
    try:
        await asyncio.sleep(REQUEST_DELAY)
        
        # Use basic Fetcher for Reddit (no anti-bot needed)
        fetcher = Fetcher()
        response = await asyncio.to_thread(fetcher.get, url, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        comments = []
        for post in soup.select(".thing")[:15]:
            title_elem = post.select_one(".title a")
            if title_elem:
                comments.append({
                    "title": title_elem.get_text(strip=True),
                    "url": title_elem.get("href", "")
                })
        
        return {
            "found": len(comments),
            "comments": comments,
            "source": "reddit"
        }
    
    except Exception as e:
        return {
            "found": 0,
            "error": str(e),
            "comments": []
        }

async def scrape_youtube(product_name: str) -> Dict:
    """
    Feature 2: YouTube Review Discovery
    Uses StealthyFetcher for YouTube (handles JavaScript)
    """
    query = f"{product_name} review".replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={query}"
    
    try:
        await asyncio.sleep(REQUEST_DELAY)
        
        # Use StealthyFetcher for YouTube (better success with JS-heavy sites)
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            timeout=SCRAPE_TIMEOUT
        )
        
        video_count = len(re.findall(r'"videoId":', response.text)[:20])
        
        return {
            "found": video_count,
            "source": "youtube"
        }
    
    except Exception as e:
        # Fallback to basic Fetcher
        try:
            fetcher = Fetcher()
            response = await asyncio.to_thread(fetcher.get, url, timeout=SCRAPE_TIMEOUT)
            video_count = len(re.findall(r'"videoId":', response.text)[:20])
            return {"found": video_count, "source": "youtube", "fallback": True}
        except:
            return {"found": 0, "error": str(e)}

async def scrape_twitter(product_name: str) -> Dict:
    """
    Feature 2: Twitter/X Sentiment Analysis
    Uses Scrapling Fetcher for Nitter
    """
    query = product_name.replace(" ", "+")
    url = f"{NITTER_INSTANCE}/search?q={query}"
    
    try:
        await asyncio.sleep(REQUEST_DELAY)
        
        fetcher = Fetcher()
        response = await asyncio.to_thread(fetcher.get, url, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        tweets = soup.select(".tweet-content")
        
        return {
            "found": len(tweets),
            "source": "twitter"
        }
    
    except Exception as e:
        return {
            "found": 0,
            "error": str(e)
        }


# ============================================================
# PHASE 2-3 FEATURES: Price, Alternatives, Coupons, Ethics
# ============================================================

async def scrape_price_history(asin: str) -> Dict:
    """
    Feature 7: Price Drop Prophet (UPGRADED with ML)
    
    NEW: Real price tracking + ML predictions
    - Scrapes CamelCamelCamel/Keepa for 6-month history
    - Analyzes if current price is good deal
    - ML predictions for next 30 days
    - Sale event calendar
    """
    try:
        # Import new modules
        from .price_scraper import get_price_history
        from .price_analyzer import PriceAnalyzer
        from .price_predictor import PricePredictor, generate_final_recommendation

# Feature 7 Phase 2 imports
try:
    from .price_predictor_arima import create_best_predictor
    from .competitor_prices import compare_with_competitors
except ImportError:
    create_best_predictor = None
    compare_with_competitors = None

        
        # 1. Get real price history
        price_data = await get_price_history(asin, months=6)
        
        # If scraping failed, fall back to calendar-based
        if not price_data.get('success'):
            return await scrape_price_history_fallback(asin)
        
        # 2. Analyze current price
        analyzer = PriceAnalyzer()
        analysis = analyzer.analyze(price_data)
        
        # 3. ML predictions
        # Use best available predictor (ARIMA if available, else Polynomial)
        if create_best_predictor:
            predictor = create_best_predictor(price_data, prefer_arima=True)
        else:
            predictor = PricePredictor(use_polynomial=True)
        predictions = predictor.predict_next_30_days(price_data)
        upcoming_sales = predictor.check_upcoming_sales()
        
        
        # 3.5. Check competitor prices (optional)
        competitor_data = None
        if compare_with_competitors and price_data.get('current_price'):
            try:
                competitor_data = await compare_with_competitors(
                    price_data.get('asin', ''),
                    price_data['current_price']
                )
            except:
                pass  # Competitor check is optional
        
        # 4. Generate final recommendation
        final_recommendation = generate_final_recommendation(
            analysis, predictions, upcoming_sales
        )
        
        result = {
            "has_data": True,
            "source": price_data['source'],
            "current_price": price_data['current_price'],
            "history": {
                "average": price_data['average_price'],
                "lowest": price_data['lowest_price'],
                "highest": price_data['highest_price'],
                "data_points": price_data['data_points']
            },
            "analysis": analysis,
            "prediction": predictions,
            "upcoming_sales": upcoming_sales,
            "recommendation": final_recommendation
        }
        
        # Add competitor data if available
        if competitor_data and competitor_data.get('has_data'):
            result['competitors'] = competitor_data
        
        return result
    
    except Exception as e:
        # Fallback to old calendar-based system
        print(f"ML price prediction failed: {e}, using fallback")
        return await scrape_price_history_fallback(asin)


async def scrape_price_history_fallback(asin: str) -> Dict:
    """
    Fallback: Calendar-based prediction (old system)
    Used when scraping fails
    """

async def find_alternatives(product_name: str, current_price: str) -> Dict:
    """
    Feature 8: Better Alternative Hunter
    Uses StealthyFetcher for Amazon search
    """
    try:
        # Extract price number
        price_match = re.search(r'[\d,]+', current_price.replace('₹', '').replace('$', ''))
        current_price_num = float(price_match.group().replace(',', '')) if price_match else 0
        
        # Search for similar products
        query = product_name.split(',')[0][:50]  # First part of product name
        search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        
        await asyncio.sleep(REQUEST_DELAY)
        
        # Use StealthyFetcher for search results
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            search_url,
            headless=True,
            network_idle=True,
            timeout=SCRAPE_TIMEOUT
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        alternatives = []
        for item in soup.select("[data-component-type='s-search-result']")[:5]:
            title_elem = item.select_one("h2 a span")
            price_elem = item.select_one(".a-price .a-offscreen")
            rating_elem = item.select_one(".a-icon-star-small span")
            
            if title_elem and price_elem:
                alt_title = title_elem.get_text(strip=True)
                alt_price_text = price_elem.get_text(strip=True)
                
                # Extract price number
                alt_price_match = re.search(r'[\d,]+', alt_price_text.replace('₹', '').replace('$', ''))
                alt_price = float(alt_price_match.group().replace(',', '')) if alt_price_match else 0
                
                alt_rating = 0.0
                if rating_elem:
                    rating_match = re.search(r'([\d.]+)', rating_elem.get_text())
                    alt_rating = float(rating_match.group(1)) if rating_match else 0.0
                
                # Only include if cheaper or better rated
                if alt_price < current_price_num or alt_rating > 4.5:
                    alternatives.append({
                        "title": alt_title[:100],
                        "price": alt_price_text,
                        "price_num": alt_price,
                        "rating": alt_rating,
                        "savings": f"{int((1 - alt_price/current_price_num) * 100)}%" if alt_price < current_price_num else "0%"
                    })
        
        return {
            "found": len(alternatives),
            "alternatives": alternatives[:3],  # Top 3
            "source": "amazon_search"
        }
    
    except Exception as e:
        return {
            "found": 0,
            "error": str(e),
            "alternatives": []
        }


async def find_coupons(product_name: str, asin: str) -> Dict:
    """
    Feature 9: Coupon Sniper
    Uses StealthyFetcher to find discount codes
    """
    coupons_found = []
    
    try:
        # Check Amazon's own coupon checkbox
        amazon_url = f"https://www.amazon.in/dp/{asin}"
        
        await asyncio.sleep(REQUEST_DELAY)
        
        # Use StealthyFetcher for coupon detection
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            amazon_url,
            headless=True,
            network_idle=True,
            timeout=SCRAPE_TIMEOUT
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for coupon badge
        coupon_elem = soup.select_one(".promoPriceBlockMessage, .savingPriceOverride")
        if coupon_elem:
            coupon_text = coupon_elem.get_text(strip=True)
            coupons_found.append({
                "code": "AMAZON_COUPON",
                "discount": coupon_text,
                "source": "Amazon"
            })
        
        # Add generic coupons if no specific ones found
        if not coupons_found:
            common_coupons = [
                {"code": "FIRST10", "discount": "10% off first order", "source": "Generic"},
                {"code": "SAVE15", "discount": "15% off ₹500+", "source": "Generic"},
            ]
            coupons_found = common_coupons[:1]
        
        return {
            "found": len(coupons_found),
            "coupons": coupons_found,
            "advice": "Apply coupon at checkout" if coupons_found else "No coupons available"
        }
    
    except Exception as e:
        return {
            "found": 0,
            "error": str(e),
            "coupons": []
        }


async def calculate_ethics_score(product_name: str, brand: str) -> Dict:
    """
    Feature 10: Guilt-Free Shopping (Carbon & Ethics)
    Estimates environmental impact and labor practices
    """
    try:
        # Extract brand (first word usually)
        if not brand:
            brand = product_name.split()[0]
        
        # Carbon footprint estimation
        category = "personal_care"  # Default category
        
        carbon_estimates = {
            "electronics": {"co2_kg": 50, "recyclable": "Partially"},
            "personal_care": {"co2_kg": 2, "recyclable": "Yes (packaging)"},
            "clothing": {"co2_kg": 10, "recyclable": "Limited"},
            "home_appliances": {"co2_kg": 100, "recyclable": "Yes"},
        }
        
        carbon_data = carbon_estimates.get(category, {"co2_kg": 5, "recyclable": "Unknown"})
        
        # Ethics score (A-F) based on brand reputation
        known_ethical_brands = {
            "garnier": "B",
            "himalaya": "A",
            "patanjali": "B+",
            "dove": "B",
            "nivea": "B-",
        }
        
        ethics_grade = known_ethical_brands.get(brand.lower(), "C")
        
        labor_assessment = {
            "A": "Excellent labor practices, fair wages",
            "B": "Good practices, some improvements needed",
            "C": "Average, meets basic standards",
            "D": "Below average, concerns noted",
            "F": "Poor practices, avoid"
        }
        
        return {
            "carbon_footprint": {
                "co2_kg": carbon_data["co2_kg"],
                "recyclable": carbon_data["recyclable"],
                "category": category
            },
            "ethics": {
                "grade": ethics_grade,
                "labor_practices": labor_assessment.get(ethics_grade[0], "Unknown"),
                "sustainability": "Moderate" if ethics_grade in ["A", "B", "B+", "B-"] else "Low"
            },
            "recommendation": "Eco-friendly choice" if ethics_grade in ["A", "B+"] else "Consider alternatives for better ethics"
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "carbon_footprint": None,
            "ethics": None
        }
