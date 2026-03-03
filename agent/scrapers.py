# scrapers.py — All web scraping logic (API-free)

import asyncio
import re
import random
from typing import Dict, Optional
import httpx
from bs4 import BeautifulSoup
from .constants import REQUEST_DELAY, USER_AGENTS, SCRAPE_TIMEOUT, REDDIT_OLD, NITTER_INSTANCE

def _random_user_agent() -> str:
    return random.choice(USER_AGENTS)

def extract_asin(url_or_text: str) -> Optional[str]:
    match = re.search(r'/dp/([A-Z0-9]{10})', url_or_text)
    if not match:
        match = re.search(r'/gp/product/([A-Z0-9]{10})', url_or_text)
    return match.group(1) if match else None

async def scrape_amazon(client: httpx.AsyncClient, asin: str) -> Dict:
    url = f"https://www.amazon.com/dp/{asin}"
    headers = {"User-Agent": _random_user_agent()}
    try:
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
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
