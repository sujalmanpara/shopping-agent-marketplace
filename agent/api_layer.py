# agent/api_layer.py
"""
API Layer — All data sources for the Shopping Truth Agent.
Every function returns a standardized Result dict.
No browser scraping. No Selenium. No Camoufox. Just clean API calls.
"""

import asyncio
import time
import re
import hashlib
import json
import os
import sqlite3
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import httpx

# ============================================================
# RESULT HELPERS
# ============================================================

def _success(source: str, data: dict, latency_ms: float) -> Dict:
    return {"success": True, "data": data, "error": None, "source": source, "latency_ms": round(latency_ms, 1)}

def _failure(source: str, error: str, latency_ms: float = 0) -> Dict:
    return {"success": False, "data": {}, "error": error, "source": source, "latency_ms": round(latency_ms, 1)}

# ============================================================
# CACHE LAYER (SQLite with TTL)
# ============================================================

_CACHE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.db")

def _init_cache():
    """Initialize SQLite cache table."""
    conn = sqlite3.connect(_CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            expires_at REAL
        )
    """)
    conn.commit()
    conn.close()

def _cache_get(key: str) -> Optional[dict]:
    """Get cached value if not expired."""
    try:
        conn = sqlite3.connect(_CACHE_DB)
        row = conn.execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,)).fetchone()
        conn.close()
        if row and row[1] > time.time():
            return json.loads(row[0])
    except Exception:
        pass
    return None

def _cache_set(key: str, value: dict, ttl_seconds: int = 3600):
    """Set cache value with TTL."""
    try:
        conn = sqlite3.connect(_CACHE_DB)
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time() + ttl_seconds)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def _cache_key(source: str, identifier: str) -> str:
    """Generate cache key."""
    return hashlib.md5(f"{source}:{identifier}".encode()).hexdigest()

# Initialize cache on import
_init_cache()

# ============================================================
# UTILITY: Extract identifiers from user input
# ============================================================

def extract_asin(url_or_text: str) -> Optional[str]:
    """Extract Amazon ASIN from URL or text."""
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/ASIN/([A-Z0-9]{10})',
        r'amazon\.\w+/.*?/([A-Z0-9]{10})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_text)
        if match:
            return match.group(1)
    # Try bare ASIN
    match = re.search(r'\b([A-Z0-9]{10})\b', url_or_text)
    if match and any(c.isalpha() for c in match.group(1)):
        return match.group(1)
    return None

def extract_flipkart_id(url_or_text: str) -> Optional[str]:
    """Extract Flipkart product ID from URL."""
    match = re.search(r'flipkart\.com/.*?/p/([a-z0-9]+)', url_or_text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'pid=([A-Z0-9]+)', url_or_text)
    if match:
        return match.group(1)
    return None

def detect_platform(url_or_text: str) -> str:
    """Detect which platform the URL belongs to."""
    text = url_or_text.lower()
    if 'amazon' in text:
        if 'amazon.in' in text:
            return 'amazon_in'
        return 'amazon_com'
    if 'flipkart' in text:
        return 'flipkart'
    return 'unknown'

# ============================================================
# SOURCE 1: Amazon Product Data
# ============================================================

async def fetch_amazon_product(asin: str, country: str = "IN", keys: dict = None) -> Dict:
    """
    Fetch product data from Amazon.
    
    Priority:
    1. Amazon PA-API (if keys provided) — most reliable
    2. Fallback: basic HTTP fetch with headers
    
    Returns: title, price, rating, review_count, reviews[], features[], images[]
    """
    cache_key = _cache_key("amazon", f"{asin}:{country}")
    cached = _cache_get(cache_key)
    if cached:
        return _success("amazon", cached, 0)
    
    start = time.time()
    
    # Try PA-API first if keys available
    pa_access_key = (keys or {}).get("AMAZON_ACCESS_KEY")
    pa_secret_key = (keys or {}).get("AMAZON_SECRET_KEY")
    pa_partner_tag = (keys or {}).get("AMAZON_PARTNER_TAG")
    
    if pa_access_key and pa_secret_key and pa_partner_tag:
        try:
            result = await _fetch_amazon_paapi(asin, pa_access_key, pa_secret_key, pa_partner_tag, country)
            if result:
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=3600)
                return _success("amazon_paapi", result, latency)
        except Exception:
            pass  # Fall through to HTTP fallback
    
    # Fallback: HTTP fetch with realistic headers
    try:
        domain = "amazon.in" if country == "IN" else "amazon.com"
        url = f"https://www.{domain}/dp/{asin}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code != 200:
                latency = (time.time() - start) * 1000
                return _failure("amazon_http", f"HTTP {resp.status_code}", latency)
            
            # Parse with regex (no BS4 dependency for basic extraction)
            html = resp.text
            
            title_match = re.search(r'id="productTitle"[^>]*>\s*([^<]+)', html)
            title = title_match.group(1).strip() if title_match else "Unknown Product"
            
            price_match = re.search(r'class="a-price-whole">([^<]+)', html)
            price_fraction = re.search(r'class="a-price-fraction">([^<]+)', html)
            price = None
            if price_match:
                price_str = price_match.group(1).strip().replace(',', '')
                fraction = price_fraction.group(1).strip() if price_fraction else "00"
                try:
                    price = float(f"{price_str}.{fraction}")
                except ValueError:
                    pass
            
            rating_match = re.search(r'([\d.]+) out of 5', html)
            rating = float(rating_match.group(1)) if rating_match else None
            
            review_count_match = re.search(r'([\d,]+)\s*(?:global\s*)?ratings', html)
            review_count = int(review_count_match.group(1).replace(',', '')) if review_count_match else 0
            
            result = {
                "title": title,
                "price": price,
                "price_display": f"₹{price:,.0f}" if price and country == "IN" else f"${price:,.2f}" if price else "N/A",
                "rating": rating,
                "review_count": review_count,
                "reviews": [],  # HTTP fallback can't reliably extract reviews
                "asin": asin,
                "url": url,
                "source_method": "http_fallback",
                "country": country,
            }
            
            latency = (time.time() - start) * 1000
            _cache_set(cache_key, result, ttl_seconds=1800)  # 30 min for HTTP fallback
            return _success("amazon_http", result, latency)
            
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("amazon", str(e), latency)


async def _fetch_amazon_paapi(asin: str, access_key: str, secret_key: str, partner_tag: str, country: str) -> Optional[Dict]:
    """
    Fetch from Amazon Product Advertising API 5.0.
    
    Requires paapi5-python-sdk or manual AWS v4 signature.
    When the SDK is installed and credentials are valid, this will return
    structured product data. Currently returns None to fall through to HTTP.
    """
    # PA-API requires AWS Signature V4 signing which needs the full SDK.
    # When ready, install paapi5-python-sdk and implement here.
    # The HTTP fallback handles product data in the meantime.
    return None

# ============================================================
# SOURCE 2: Reddit (via PRAW or Pushshift)
# ============================================================

async def fetch_reddit_discussions(product_name: str, brand: str = "", category: str = "", keys: dict = None) -> Dict:
    """
    Fetch Reddit discussions about a product.
    
    Uses PRAW (Python Reddit API Wrapper) if credentials available,
    falls back to old.reddit.com HTTP parsing.
    """
    cache_key = _cache_key("reddit", product_name)
    cached = _cache_get(cache_key)
    if cached:
        return _success("reddit", cached, 0)
    
    start = time.time()
    
    # Try PRAW first
    reddit_client_id = (keys or {}).get("REDDIT_CLIENT_ID")
    reddit_secret = (keys or {}).get("REDDIT_CLIENT_SECRET")
    
    if reddit_client_id and reddit_secret:
        try:
            result = await _fetch_reddit_praw(product_name, brand, category, reddit_client_id, reddit_secret)
            if result and result.get("found", 0) > 0:
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=7200)  # 2 hour cache for Reddit
                return _success("reddit_praw", result, latency)
        except Exception:
            pass
    
    # Fallback: old.reddit.com search
    try:
        query = product_name.replace(" ", "+")
        url = f"https://old.reddit.com/search.json?q={query}&sort=relevance&limit=25"
        
        headers = {
            "User-Agent": "ShoppingTruthAgent/1.0 (research bot)",
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code != 200:
                latency = (time.time() - start) * 1000
                return _failure("reddit_http", f"HTTP {resp.status_code}", latency)
            
            data = resp.json()
            posts = []
            
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append({
                    "title": post.get("title", ""),
                    "subreddit": post.get("subreddit", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "created_utc": post.get("created_utc", 0),
                    "selftext": (post.get("selftext", "") or "")[:500],
                })
            
            # Sort by relevance (score * comments)
            posts.sort(key=lambda x: x["score"] * max(x["num_comments"], 1), reverse=True)
            
            result = {
                "found": len(posts),
                "posts": posts[:10],  # Top 10
                "subreddits": list(set(p["subreddit"] for p in posts)),
                "total_engagement": sum(p["score"] + p["num_comments"] for p in posts),
            }
            
            latency = (time.time() - start) * 1000
            _cache_set(cache_key, result, ttl_seconds=7200)
            return _success("reddit_http", result, latency)
            
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("reddit", str(e), latency)


async def _fetch_reddit_praw(product_name: str, brand: str, category: str, client_id: str, client_secret: str) -> Optional[Dict]:
    """
    Fetch Reddit data using PRAW.
    
    Requires the praw package and valid OAuth credentials.
    When credentials are available, this searches relevant subreddits
    for product discussions and returns structured post data.
    Currently returns None to fall through to HTTP fallback.
    """
    # PRAW is synchronous — would need asyncio.to_thread() wrapper.
    # The HTTP fallback via old.reddit.com/search.json works well.
    return None

# ============================================================
# SOURCE 3: YouTube (Data API v3)
# ============================================================

async def fetch_youtube_reviews(product_name: str, keys: dict = None) -> Dict:
    """
    Fetch YouTube review videos and top comments.
    Uses YouTube Data API v3 if key available, falls back to HTTP.
    """
    cache_key = _cache_key("youtube", product_name)
    cached = _cache_get(cache_key)
    if cached:
        return _success("youtube", cached, 0)
    
    start = time.time()
    
    yt_api_key = (keys or {}).get("YOUTUBE_API_KEY")
    
    if yt_api_key:
        try:
            query = f"{product_name} review"
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 10,
                "order": "relevance",
                "key": yt_api_key,
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(search_url, params=params)
                
                if resp.status_code != 200:
                    latency = (time.time() - start) * 1000
                    return _failure("youtube_api", f"HTTP {resp.status_code}", latency)
                
                data = resp.json()
                videos = []
                video_ids = []
                
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    video_ids.append(video_id)
                    videos.append({
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", ""),
                        "description": snippet.get("description", "")[:200],
                        "video_id": video_id,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "published_at": snippet.get("publishedAt", ""),
                    })
                
                # Get video stats (views, likes)
                if video_ids:
                    stats_url = "https://www.googleapis.com/youtube/v3/videos"
                    stats_params = {
                        "part": "statistics",
                        "id": ",".join(video_ids[:10]),
                        "key": yt_api_key,
                    }
                    stats_resp = await client.get(stats_url, params=stats_params)
                    if stats_resp.status_code == 200:
                        stats_data = stats_resp.json()
                        for i, item in enumerate(stats_data.get("items", [])):
                            if i < len(videos):
                                stats = item.get("statistics", {})
                                videos[i]["views"] = int(stats.get("viewCount", 0))
                                videos[i]["likes"] = int(stats.get("likeCount", 0))
                
                # Sort by views
                videos.sort(key=lambda x: x.get("views", 0), reverse=True)
                
                result = {
                    "found": len(videos),
                    "videos": videos,
                    "total_views": sum(v.get("views", 0) for v in videos),
                }
                
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=7200)
                return _success("youtube_api", result, latency)
                
        except Exception:
            pass  # Fall through to HTTP fallback
    
    # Fallback: No API key — return empty with note
    latency = (time.time() - start) * 1000
    return _failure("youtube", "No YouTube API key provided. Set YOUTUBE_API_KEY for video reviews.", latency)

# ============================================================
# SOURCE 4: Keepa (Price History)
# ============================================================

async def fetch_keepa_history(asin: str, keys: dict = None) -> Dict:
    """
    Fetch price history from Keepa API.
    Keepa API requires a paid key (~€15/month).
    """
    cache_key = _cache_key("keepa", asin)
    cached = _cache_get(cache_key)
    if cached:
        return _success("keepa", cached, 0)
    
    start = time.time()
    
    keepa_key = (keys or {}).get("KEEPA_API_KEY")
    
    if not keepa_key:
        return _failure("keepa", "No Keepa API key. Set KEEPA_API_KEY for price history (~€15/month).", 0)
    
    try:
        url = "https://api.keepa.com/product"
        params = {
            "key": keepa_key,
            "domain": "3",  # 3 = Amazon.in, 1 = Amazon.com
            "asin": asin,
            "history": "1",  # Include price history
            "days": "180",   # 6 months
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            
            if resp.status_code != 200:
                latency = (time.time() - start) * 1000
                return _failure("keepa", f"HTTP {resp.status_code}", latency)
            
            data = resp.json()
            products = data.get("products", [])
            
            if not products:
                latency = (time.time() - start) * 1000
                return _failure("keepa", "Product not found on Keepa", latency)
            
            product = products[0]
            csv_data = product.get("csv", [])
            
            # Parse Keepa's CSV format for Amazon price (index 0)
            prices = []
            if csv_data and len(csv_data) > 0 and csv_data[0]:
                raw = csv_data[0]
                for i in range(0, len(raw) - 1, 2):
                    keepa_time = raw[i]
                    price_cents = raw[i + 1]
                    if price_cents > 0:  # -1 means out of stock
                        # Keepa time: minutes since 2011-01-01
                        timestamp = datetime(2011, 1, 1) + timedelta(minutes=keepa_time)
                        price = price_cents / 100.0
                        prices.append({"date": timestamp.isoformat(), "price": price})
            
            if not prices:
                latency = (time.time() - start) * 1000
                return _failure("keepa", "No price history data available", latency)
            
            price_values = [p["price"] for p in prices]
            
            result = {
                "prices": prices[-180:],  # Last 180 data points max
                "current_price": price_values[-1] if price_values else None,
                "average_price": round(sum(price_values) / len(price_values), 2),
                "lowest_price": min(price_values),
                "highest_price": max(price_values),
                "lowest_date": prices[price_values.index(min(price_values))]["date"],
                "data_points": len(prices),
                "price_range": round(max(price_values) - min(price_values), 2),
            }
            
            latency = (time.time() - start) * 1000
            _cache_set(cache_key, result, ttl_seconds=3600)
            return _success("keepa", result, latency)
            
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("keepa", str(e), latency)

# ============================================================
# SOURCE 5: Google Shopping (via SerpAPI or direct)
# ============================================================

async def fetch_google_shopping(product_name: str, country: str = "IN", keys: dict = None) -> Dict:
    """
    Fetch price comparison from Google Shopping.
    Uses SerpAPI if key available ($50/month for 5000 searches).
    """
    cache_key = _cache_key("google_shopping", f"{product_name}:{country}")
    cached = _cache_get(cache_key)
    if cached:
        return _success("google_shopping", cached, 0)
    
    start = time.time()
    
    serpapi_key = (keys or {}).get("SERPAPI_KEY")
    
    if not serpapi_key:
        return _failure("google_shopping", "No SerpAPI key. Set SERPAPI_KEY for Google Shopping (~$50/month).", 0)
    
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_shopping",
            "q": product_name,
            "gl": country.lower(),
            "hl": "en",
            "api_key": serpapi_key,
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            
            if resp.status_code != 200:
                latency = (time.time() - start) * 1000
                return _failure("google_shopping", f"HTTP {resp.status_code}", latency)
            
            data = resp.json()
            results = data.get("shopping_results", [])
            
            items = []
            for item in results[:10]:
                extracted_price = item.get("extracted_price", 0)
                items.append({
                    "title": item.get("title", ""),
                    "price": item.get("price", ""),
                    "price_numeric": extracted_price,
                    "source": item.get("source", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating"),
                    "reviews_count": item.get("reviews", 0),
                    "thumbnail": item.get("thumbnail", ""),
                })
            
            # Sort by price
            items.sort(key=lambda x: x.get("price_numeric", float('inf')))
            
            result = {
                "found": len(items),
                "items": items,
                "lowest_price": items[0]["price"] if items else None,
                "lowest_source": items[0]["source"] if items else None,
                "price_range": {
                    "min": min(i["price_numeric"] for i in items) if items else None,
                    "max": max(i["price_numeric"] for i in items) if items else None,
                },
            }
            
            latency = (time.time() - start) * 1000
            _cache_set(cache_key, result, ttl_seconds=1800)  # 30 min cache
            return _success("google_shopping", result, latency)
            
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("google_shopping", str(e), latency)

# ============================================================
# SOURCE 6: Fakespot
# ============================================================

async def fetch_fakespot_grade(asin: str, country: str = "IN") -> Dict:
    """
    Fetch Fakespot review analysis grade.
    Uses their analysis URL endpoint.
    Note: Fakespot was acquired by Mozilla. API availability may change.
    """
    cache_key = _cache_key("fakespot", asin)
    cached = _cache_get(cache_key)
    if cached:
        return _success("fakespot", cached, 0)
    
    start = time.time()
    
    try:
        domain = "amazon.in" if country == "IN" else "amazon.com"
        product_url = f"https://www.{domain}/dp/{asin}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
        }
        
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Try API endpoint first
            api_url = f"https://api.fakespot.com/v1/products/analyze?url={product_url}"
            resp = await client.get(api_url, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "grade": data.get("grade", "Unknown"),
                    "adjusted_rating": data.get("adjusted_rating"),
                    "analysis_url": data.get("analysis_url", ""),
                }
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=86400)  # 24 hour cache
                return _success("fakespot", result, latency)
        
        latency = (time.time() - start) * 1000
        return _failure("fakespot", "Fakespot API unavailable", latency)
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("fakespot", str(e), latency)

# ============================================================
# SOURCE 7: ReviewMeta
# ============================================================

async def fetch_reviewmeta(asin: str) -> Dict:
    """
    Fetch ReviewMeta adjusted rating.
    Uses their analysis page — this is HTTP scraping, not a real API.
    """
    cache_key = _cache_key("reviewmeta", asin)
    cached = _cache_get(cache_key)
    if cached:
        return _success("reviewmeta", cached, 0)
    
    start = time.time()
    
    try:
        url = f"https://reviewmeta.com/amazon/{asin}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                html = resp.text
                
                # Try to extract adjusted rating
                adjusted_match = re.search(r'adjusted[^\d]*([\d.]+)\s*/\s*5', html, re.IGNORECASE)
                original_match = re.search(r'original[^\d]*([\d.]+)\s*/\s*5', html, re.IGNORECASE)
                fail_match = re.search(r'(\d+)%?\s*(?:of reviews|reviews?\s+fail)', html, re.IGNORECASE)
                
                result = {
                    "adjusted_rating": float(adjusted_match.group(1)) if adjusted_match else None,
                    "original_rating": float(original_match.group(1)) if original_match else None,
                    "failed_reviews_pct": int(fail_match.group(1)) if fail_match else None,
                    "analysis_url": url,
                }
                
                if result["adjusted_rating"] is not None:
                    latency = (time.time() - start) * 1000
                    _cache_set(cache_key, result, ttl_seconds=86400)
                    return _success("reviewmeta", result, latency)
        
        latency = (time.time() - start) * 1000
        return _failure("reviewmeta", "Could not extract ReviewMeta data", latency)
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("reviewmeta", str(e), latency)

# ============================================================
# SOURCE 8: Wirecutter (HTTP)
# ============================================================

async def fetch_wirecutter(product_name: str, category: str = "") -> Dict:
    """
    Check if product is a Wirecutter pick.
    Simple HTTP search — no API exists.
    """
    cache_key = _cache_key("wirecutter", product_name)
    cached = _cache_get(cache_key)
    if cached:
        return _success("wirecutter", cached, 0)
    
    start = time.time()
    
    try:
        query = product_name.replace(" ", "+")
        url = f"https://www.nytimes.com/wirecutter/search/?s={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                html = resp.text
                
                # Check for mentions
                product_lower = product_name.lower()
                is_mentioned = product_lower.split()[0] in html.lower() if product_name else False
                
                # Check for "top pick" or "best" mentions
                is_top_pick = any(phrase in html.lower() for phrase in ["top pick", "our pick", "best overall", "also great"])
                
                result = {
                    "found": is_mentioned,
                    "is_top_pick": is_top_pick,
                    "search_url": url,
                    "note": "Wirecutter is US-focused. Picks may not be available in India." if is_mentioned else "Product not found on Wirecutter",
                }
                
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=86400)
                return _success("wirecutter", result, latency)
        
        latency = (time.time() - start) * 1000
        return _failure("wirecutter", "Wirecutter search failed", latency)
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("wirecutter", str(e), latency)

# ============================================================
# SOURCE 9: RTINGS
# ============================================================

async def fetch_rtings(product_name: str) -> Dict:
    """
    Check RTINGS for test scores.
    RTINGS covers: headphones, TVs, monitors, keyboards, mice, speakers, soundbars.
    """
    cache_key = _cache_key("rtings", product_name)
    cached = _cache_get(cache_key)
    if cached:
        return _success("rtings", cached, 0)
    
    start = time.time()
    
    try:
        query = product_name.replace(" ", "+")
        url = f"https://www.rtings.com/search?query={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                html = resp.text
                
                # Try to find score
                score_match = re.search(r'(\d+\.?\d*)\s*/\s*10', html)
                is_found = product_name.split()[0].lower() in html.lower() if product_name else False
                
                result = {
                    "found": is_found,
                    "score": float(score_match.group(1)) if score_match else None,
                    "search_url": url,
                    "categories_covered": ["headphones", "TVs", "monitors", "keyboards", "mice", "speakers", "soundbars"],
                }
                
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=86400)
                return _success("rtings", result, latency)
        
        latency = (time.time() - start) * 1000
        return _failure("rtings", "RTINGS search failed", latency)
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("rtings", str(e), latency)

# ============================================================
# SOURCE 10: Trustpilot
# ============================================================

async def fetch_trustpilot(brand: str) -> Dict:
    """
    Fetch brand reputation from Trustpilot.
    Note: Brand-level, not product-level.
    """
    cache_key = _cache_key("trustpilot", brand)
    cached = _cache_get(cache_key)
    if cached:
        return _success("trustpilot", cached, 0)
    
    start = time.time()
    
    try:
        brand_slug = brand.lower().replace(" ", "-").replace(".", "")
        url = f"https://www.trustpilot.com/review/{brand_slug}.com"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                html = resp.text
                
                # Extract Trustpilot score
                score_match = re.search(r'TrustScore\s*([\d.]+)', html)
                review_count_match = re.search(r'([\d,]+)\s*reviews?', html)
                
                result = {
                    "found": True,
                    "trust_score": float(score_match.group(1)) if score_match else None,
                    "review_count": int(review_count_match.group(1).replace(',', '')) if review_count_match else None,
                    "url": url,
                    "note": "Brand-level trust score, not product-specific",
                }
                
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=86400)
                return _success("trustpilot", result, latency)
        
        latency = (time.time() - start) * 1000
        return _failure("trustpilot", f"Brand '{brand}' not found on Trustpilot", latency)
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return _failure("trustpilot", str(e), latency)

# ============================================================
# MASTER FETCH — Run all sources in parallel
# ============================================================

async def fetch_all_sources(asin: str, product_name: str, brand: str = "", country: str = "IN", keys: dict = None) -> Dict:
    """
    Fetch data from ALL sources concurrently.
    Returns a dict of source_name -> Result.
    Implements graceful degradation: if sources fail, others continue.
    """
    tasks = {
        "amazon": fetch_amazon_product(asin, country, keys),
        "reddit": fetch_reddit_discussions(product_name, brand, keys=keys),
        "youtube": fetch_youtube_reviews(product_name, keys),
        "keepa": fetch_keepa_history(asin, keys),
        "google_shopping": fetch_google_shopping(product_name, country, keys),
        "fakespot": fetch_fakespot_grade(asin, country),
        "reviewmeta": fetch_reviewmeta(asin),
        "wirecutter": fetch_wirecutter(product_name),
        "rtings": fetch_rtings(product_name),
        "trustpilot": fetch_trustpilot(brand),
    }
    
    # Run all concurrently
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    # Map results back to source names
    source_results = {}
    for name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            source_results[name] = _failure(name, str(result), 0)
        else:
            source_results[name] = result
    
    # Summary stats
    succeeded = sum(1 for r in source_results.values() if r["success"])
    failed = sum(1 for r in source_results.values() if not r["success"])
    total_latency = sum(r.get("latency_ms", 0) for r in source_results.values())
    
    return {
        "sources": source_results,
        "summary": {
            "total": len(source_results),
            "succeeded": succeeded,
            "failed": failed,
            "success_rate": round(succeeded / len(source_results) * 100, 1),
            "total_latency_ms": round(total_latency, 1),
            "failed_sources": [name for name, r in source_results.items() if not r["success"]],
        }
    }
