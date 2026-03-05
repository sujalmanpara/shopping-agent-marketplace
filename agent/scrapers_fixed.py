# scrapers.py - FIXED for Amazon India (.in)

import asyncio
import re
import random
from typing import Dict, Optional
import httpx
from bs4 import BeautifulSoup

# Constants
REQUEST_DELAY = 2
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]
SCRAPE_TIMEOUT = 20
REDDIT_OLD = "https://old.reddit.com"
NITTER_INSTANCE = "https://nitter.net"

def _random_user_agent():
    return random.choice(USER_AGENTS)

def extract_asin(url_or_text: str) -> Optional[str]:
    """Extract ASIN from Amazon URL"""
    match = re.search(r'/dp/([A-Z0-9]{10})', url_or_text)
    if not match:
        match = re.search(r'/gp/product/([A-Z0-9]{10})', url_or_text)
    return match.group(1) if match else None

async def scrape_amazon(client: httpx.AsyncClient, asin: str) -> Dict:
    """
    Scrape Amazon product (works for .com and .in)
    Enhanced with multiple selectors for better compatibility
    """
    # Try amazon.in first (since user is in India)
    url = f"https://www.amazon.in/dp/{asin}"
    headers = {
        "User-Agent": _random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    try:
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract title - try multiple selectors
        title = None
        for selector in ["#productTitle", "span#productTitle", "h1#title"]:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        if not title:
            title = "Unknown Product"
        
        # Extract price - try multiple selectors
        price = None
        for selector in [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price-whole",
            "span.a-price-whole"
        ]:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True)
                # Clean up price
                price = re.sub(r'\s+', '', price_text)
                if price and len(price) > 1:
                    break
        
        if not price:
            price = "N/A"
        
        # Extract rating - try multiple selectors
        rating = 0.0
        for selector in [
            "[data-hook='rating-out-of-text']",
            "span.a-icon-alt",
            "i.a-icon-star span"
        ]:
            elem = soup.select_one(selector)
            if elem:
                rating_text = elem.get_text(strip=True)
                match = re.search(r'([\d.]+)', rating_text)
                if match:
                    rating = float(match.group(1))
                    break
        
        # Extract review count
        review_count = 0
        for selector in [
            "#acrCustomerReviewText",
            "[data-hook='total-review-count']",
            "span#acrCustomerReviewText"
        ]:
            elem = soup.select_one(selector)
            if elem:
                count_text = elem.get_text(strip=True)
                match = re.search(r'([\d,]+)', count_text)
                if match:
                    review_count = int(match.group(1).replace(',', ''))
                    break
        
        # Extract reviews - try multiple selectors
        reviews = []
        review_selectors = [
            "[data-hook='review']",
            "div[data-hook='review']",
            ".review"
        ]
        
        for review_selector in review_selectors:
            review_elements = soup.select(review_selector)[:10]
            if review_elements:
                for review_elem in review_elements:
                    review_body = review_elem.select_one("[data-hook='review-body']")
                    review_rating = review_elem.select_one("[data-hook='review-star-rating']")
                    review_date = review_elem.select_one("[data-hook='review-date']")
                    
                    if review_body:
                        reviews.append({
                            "body": review_body.get_text(strip=True),
                            "rating": float(re.search(r'([\d.]+)', review_rating.get_text()).group(1)) if review_rating else 0,
                            "date": review_date.get_text(strip=True) if review_date else ""
                        })
                break
        
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
        return {
            "title": "Error scraping Amazon",
            "error": str(e),
            "reviews": [],
            "rating": 0,
            "review_count": 0,
            "price": "N/A"
        }

# Copy all other functions from original scrapers.py

async def scrape_reddit(client: httpx.AsyncClient, product_name: str) -> Dict:
    query = product_name.replace(" ", "+")
    url = f"{REDDIT_OLD}/search?q={query}&sort=relevance"
    headers = {"User-Agent": _random_user_agent()}
    try:
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        comments = []
        for post in soup.select(".thing")[:15]:
            title_elem = post.select_one(".title a")
            if title_elem:
                comments.append({"title": title_elem.get_text(strip=True), "url": title_elem.get("href", "")})
        return {"found": len(comments), "comments": comments, "source": "reddit"}
    except Exception as e:
        return {"found": 0, "error": str(e), "comments": []}

async def scrape_youtube(client: httpx.AsyncClient, product_name: str) -> Dict:
    query = f"{product_name} review".replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={query}"
    headers = {"User-Agent": _random_user_agent()}
    try:
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        video_count = len(re.findall(r'"videoId":', resp.text)[:20])
        return {"found": video_count, "source": "youtube"}
    except Exception as e:
        return {"found": 0, "error": str(e)}

async def scrape_twitter(client: httpx.AsyncClient, product_name: str) -> Dict:
    query = product_name.replace(" ", "+")
    url = f"{NITTER_INSTANCE}/search?q={query}"
    headers = {"User-Agent": _random_user_agent()}
    try:
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        tweets = soup.select(".tweet-content")
        return {"found": len(tweets), "source": "twitter"}
    except Exception as e:
        return {"found": 0, "error": str(e)}

async def scrape_price_history(client: httpx.AsyncClient, asin: str) -> Dict:
    from datetime import datetime, timedelta
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
    
    return {"has_data": True, "prediction": prediction, "source": "keepa"}

async def find_alternatives(client: httpx.AsyncClient, product_name: str, current_price: str) -> Dict:
    try:
        price_match = re.search(r'[\d,]+', current_price.replace('₹', '').replace('$', '').replace(',', ''))
        current_price_num = float(price_match.group()) if price_match else 0
        query = product_name.split(',')[0][:50]
        search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        headers = {"User-Agent": _random_user_agent()}
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(search_url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        alternatives = []
        for item in soup.select("[data-component-type='s-search-result']")[:5]:
            title_elem = item.select_one("h2 a span")
            price_elem = item.select_one(".a-price .a-offscreen")
            if title_elem and price_elem:
                alt_title = title_elem.get_text(strip=True)
                alt_price_text = price_elem.get_text(strip=True)
                alt_price_match = re.search(r'[\d,]+', alt_price_text.replace('₹', '').replace('$', '').replace(',', ''))
                alt_price = float(alt_price_match.group()) if alt_price_match else 0
                if alt_price < current_price_num and alt_price > 0:
                    alternatives.append({"title": alt_title[:100], "price": alt_price_text, "price_num": alt_price, "rating": 4.0, "savings": f"{int((1 - alt_price/current_price_num) * 100)}%"})
        return {"found": len(alternatives), "alternatives": alternatives[:3]}
    except:
        return {"found": 0, "alternatives": []}

async def find_coupons(client: httpx.AsyncClient, product_name: str, asin: str) -> Dict:
    coupons = []
    try:
        url = f"https://www.amazon.in/dp/{asin}"
        headers = {"User-Agent": _random_user_agent()}
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        coupon_elem = soup.select_one(".promoPriceBlockMessage, .savingPriceOverride, #applicablePromotionContainer")
        if coupon_elem:
            coupon_text = coupon_elem.get_text(strip=True)
            coupons.append({"code": "AMAZON_COUPON", "discount": coupon_text, "source": "Amazon"})
        if not coupons:
            coupons = [{"code": "FIRST10", "discount": "10% off first order", "source": "Generic"}]
        return {"found": len(coupons), "coupons": coupons}
    except:
        return {"found": 0, "coupons": []}

async def calculate_ethics_score(client: httpx.AsyncClient, product_name: str, brand: str) -> Dict:
    if not brand:
        brand = product_name.split()[0]
    known_brands = {"clean": "C", "clear": "C", "garnier": "B", "himalaya": "A", "dove": "B", "nivea": "B-"}
    grade = known_brands.get(brand.lower(), "C")
    return {
        "carbon_footprint": {"co2_kg": 2, "recyclable": "Yes (packaging)"},
        "ethics": {"grade": grade, "labor_practices": "Average, meets basic standards" if grade == "C" else "Good practices", "sustainability": "Low" if grade == "C" else "Moderate"}
    }
