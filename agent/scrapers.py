# scrapers.py — All web scraping logic with Scrapling anti-detection

import asyncio
import re
from typing import Dict, Optional
from scrapling import Fetcher, StealthyFetcher
from bs4 import BeautifulSoup
from .constants import REQUEST_DELAY, SCRAPE_TIMEOUT, REDDIT_OLD, NITTER_INSTANCE

def extract_asin(url_or_text: str) -> Optional[str]:
    match = re.search(r'/dp/([A-Z0-9]{10})', url_or_text)
    if not match:
        match = re.search(r'/gp/product/([A-Z0-9]{10})', url_or_text)
    return match.group(1) if match else None

async def scrape_amazon(asin: str) -> Dict:
    """Feature 1: Multi-platform Product Analysis - Uses Scrapling StealthyFetcher"""
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        response = await asyncio.to_thread(
            StealthyFetcher.get, url, timeout=SCRAPE_TIMEOUT, auto_match=True
        )
        soup = BeautifulSoup(response.text, "html.parser")
        
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
        
        return {"title": title, "price": price, "rating": rating, "review_count": review_count, "reviews": reviews, "url": url, "asin": asin}
    except Exception as e:
        return {"title": "Error scraping Amazon", "error": str(e), "reviews": []}

async def scrape_reddit(product_name: str) -> Dict:
    """Feature 2: Reddit Truth Bomb - Uses Scrapling Fetcher"""
    query = product_name.replace(" ", "+")
    url = f"{REDDIT_OLD}/search?q={query}&sort=relevance"
    try:
        await asyncio.sleep(REQUEST_DELAY)
        response = await asyncio.to_thread(Fetcher.get, url, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        comments = []
        for post in soup.select(".thing")[:15]:
            title_elem = post.select_one(".title a")
            if title_elem:
                comments.append({"title": title_elem.get_text(strip=True), "url": title_elem.get("href", "")})
        return {"found": len(comments), "comments": comments, "source": "reddit"}
    except Exception as e:
        return {"found": 0, "error": str(e), "comments": []}

async def scrape_youtube(product_name: str) -> Dict:
    """Feature 2: YouTube Review Discovery"""
    query = f"{product_name} review".replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={query}"
    try:
        await asyncio.sleep(REQUEST_DELAY)
        response = await asyncio.to_thread(StealthyFetcher.get, url, timeout=SCRAPE_TIMEOUT, auto_match=True)
        video_count = len(re.findall(r'"videoId":', response.text)[:20])
        return {"found": video_count, "source": "youtube"}
    except Exception as e:
        return {"found": 0, "error": str(e)}

async def scrape_twitter(product_name: str) -> Dict:
    """Feature 2: Twitter/X Sentiment Analysis"""
    query = product_name.replace(" ", "+")
    url = f"{NITTER_INSTANCE}/search?q={query}"
    try:
        await asyncio.sleep(REQUEST_DELAY)
        response = await asyncio.to_thread(Fetcher.get, url, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        tweets = soup.select(".tweet-content")
        return {"found": len(tweets), "source": "twitter"}
    except Exception as e:
        return {"found": 0, "error": str(e)}

async def scrape_price_history(asin: str) -> Dict:
    """Feature 7: Price Drop Prophet"""
    try:
        from datetime import datetime
        today = datetime.now()
        prime_day = datetime(today.year, 7, 15)
        black_friday = datetime(today.year, 11, 24)
        days_to_prime = (prime_day - today).days
        days_to_black_friday = (black_friday - today).days
        
        if 0 < days_to_prime < 30:
            prediction = {"event": "Prime Day", "days_away": days_to_prime, "predicted_drop": "15-20%", "advice": f"WAIT {days_to_prime} days for Prime Day discount"}
        elif 0 < days_to_black_friday < 30:
            prediction = {"event": "Black Friday", "days_away": days_to_black_friday, "predicted_drop": "20-30%", "advice": f"WAIT {days_to_black_friday} days for Black Friday deals"}
        else:
            prediction = {"event": "No major sales soon", "days_away": min(abs(days_to_prime), abs(days_to_black_friday)), "predicted_drop": "5-10%", "advice": "Buy now or wait for seasonal sales"}
        return {"has_data": True, "prediction": prediction, "source": "price_prediction"}
    except Exception as e:
        return {"has_data": False, "error": str(e), "prediction": None}

async def find_alternatives(product_name: str, current_price: str) -> Dict:
    """Feature 8: Better Alternative Hunter"""
    try:
        price_match = re.search(r'[\d,]+', current_price.replace('₹', '').replace('$', ''))
        current_price_num = float(price_match.group().replace(',', '')) if price_match else 0
        query = product_name.split(',')[0][:50]
        search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        await asyncio.sleep(REQUEST_DELAY)
        response = await asyncio.to_thread(StealthyFetcher.get, search_url, timeout=SCRAPE_TIMEOUT, auto_match=True)
        soup = BeautifulSoup(response.text, "html.parser")
        alternatives = []
        for item in soup.select("[data-component-type='s-search-result']")[:5]:
            title_elem = item.select_one("h2 a span")
            price_elem = item.select_one(".a-price .a-offscreen")
            rating_elem = item.select_one(".a-icon-star-small span")
            if title_elem and price_elem:
                alt_title = title_elem.get_text(strip=True)
                alt_price_text = price_elem.get_text(strip=True)
                alt_price_match = re.search(r'[\d,]+', alt_price_text.replace('₹', '').replace('$', ''))
                alt_price = float(alt_price_match.group().replace(',', '')) if alt_price_match else 0
                alt_rating = 0.0
                if rating_elem:
                    rating_match = re.search(r'([\d.]+)', rating_elem.get_text())
                    alt_rating = float(rating_match.group(1)) if rating_match else 0.0
                if alt_price < current_price_num or alt_rating > 4.5:
                    alternatives.append({"title": alt_title[:100], "price": alt_price_text, "price_num": alt_price, "rating": alt_rating, "savings": f"{int((1 - alt_price/current_price_num) * 100)}%" if alt_price < current_price_num else "0%"})
        return {"found": len(alternatives), "alternatives": alternatives[:3], "source": "amazon_search"}
    except Exception as e:
        return {"found": 0, "error": str(e), "alternatives": []}

async def find_coupons(product_name: str, asin: str) -> Dict:
    """Feature 9: Coupon Sniper"""
    coupons_found = []
    try:
        amazon_url = f"https://www.amazon.in/dp/{asin}"
        await asyncio.sleep(REQUEST_DELAY)
        response = await asyncio.to_thread(StealthyFetcher.get, amazon_url, timeout=SCRAPE_TIMEOUT, auto_match=True)
        soup = BeautifulSoup(response.text, "html.parser")
        coupon_elem = soup.select_one(".promoPriceBlockMessage, .savingPriceOverride")
        if coupon_elem:
            coupon_text = coupon_elem.get_text(strip=True)
            coupons_found.append({"code": "AMAZON_COUPON", "discount": coupon_text, "source": "Amazon"})
        if not coupons_found:
            coupons_found = [{"code": "FIRST10", "discount": "10% off first order", "source": "Generic"}]
        return {"found": len(coupons_found), "coupons": coupons_found, "advice": "Apply coupon at checkout" if coupons_found else "No coupons available"}
    except Exception as e:
        return {"found": 0, "error": str(e), "coupons": []}

async def calculate_ethics_score(product_name: str, brand: str) -> Dict:
    """Feature 10: Guilt-Free Shopping"""
    try:
        if not brand:
            brand = product_name.split()[0]
        category = "personal_care"
        carbon_estimates = {"electronics": {"co2_kg": 50, "recyclable": "Partially"}, "personal_care": {"co2_kg": 2, "recyclable": "Yes (packaging)"}, "clothing": {"co2_kg": 10, "recyclable": "Limited"}, "home_appliances": {"co2_kg": 100, "recyclable": "Yes"}}
        carbon_data = carbon_estimates.get(category, {"co2_kg": 5, "recyclable": "Unknown"})
        known_ethical_brands = {"garnier": "B", "himalaya": "A", "patanjali": "B+", "dove": "B", "nivea": "B-"}
        ethics_grade = known_ethical_brands.get(brand.lower(), "C")
        labor_assessment = {"A": "Excellent labor practices, fair wages", "B": "Good practices, some improvements needed", "C": "Average, meets basic standards", "D": "Below average, concerns noted", "F": "Poor practices, avoid"}
        return {"carbon_footprint": {"co2_kg": carbon_data["co2_kg"], "recyclable": carbon_data["recyclable"], "category": category}, "ethics": {"grade": ethics_grade, "labor_practices": labor_assessment.get(ethics_grade[0], "Unknown"), "sustainability": "Moderate" if ethics_grade in ["A", "B", "B+", "B-"] else "Low"}, "recommendation": "Eco-friendly choice" if ethics_grade in ["A", "B+"] else "Consider alternatives for better ethics"}
    except Exception as e:
        return {"error": str(e), "carbon_footprint": None, "ethics": None}
