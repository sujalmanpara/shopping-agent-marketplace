# agent/api_layer.py
"""
API Layer — All data sources for the Shopping Truth Agent.
Every function returns a standardized Result dict.
No browser scraping. Just clean API calls.
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

def detect_platform(url_or_text: str) -> str:
    """Detect which platform the URL belongs to. Amazon only for now."""
    text = url_or_text.lower()
    if 'amazon' in text:
        if 'amazon.in' in text:
            return 'amazon_in'
        return 'amazon_com'
    return 'amazon_in'  # Default to Amazon IN

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

    # ── Tier 1: Rainforest API (most trusted, enterprise-grade) ──
    rainforest_key = (keys or {}).get("RAINFOREST_API_KEY")
    if rainforest_key:
        try:
            result = await _fetch_amazon_rainforest(asin, rainforest_key, country)
            if result:
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=3600)
                return _success("amazon_rainforest", result, latency)
        except Exception:
            pass  # Fall through

    # ── Tier 2: ScrapingDog API (reliable, free tier 1000/mo) ──
    scrapingdog_key = (keys or {}).get("SCRAPINGDOG_API_KEY")
    if scrapingdog_key:
        try:
            result = await _fetch_amazon_scrapingdog(asin, scrapingdog_key, country)
            if result:
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=3600)
                return _success("amazon_scrapingdog", result, latency)
        except Exception:
            pass  # Fall through

    # ── Tier 3: Stealth browser fallback (Camoufox/Playwright on port 9222) ──
    camoufox_token = (keys or {}).get("CAMOUFOX_TOKEN", "")
    camoufox_port = int((keys or {}).get("CAMOUFOX_PORT", "9222"))
    if not camoufox_token:
        # Try reading from the default token file
        try:
            with open("/data/browser-server-token", "r") as f:
                camoufox_token = f.read().strip()
        except Exception:
            pass
    if camoufox_token:
        try:
            result = await _fetch_amazon_camoufox(asin, camoufox_token, camoufox_port, country)
            if result:
                latency = (time.time() - start) * 1000
                _cache_set(cache_key, result, ttl_seconds=3600)
                return _success("amazon_camoufox", result, latency)
        except Exception:
            pass  # Fall through

    # ── Tier 4: HTTP fallback (works on residential IPs) ──
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


async def _fetch_amazon_rainforest(asin: str, api_key: str, country: str = "IN") -> Optional[Dict]:
    """
    Fetch Amazon product data via Rainforest API (trajectdata.com).
    Enterprise-grade, built specifically for Amazon. Recommended for production.
    Signup: https://www.rainforestapi.com/ — plans from ~$100/mo
    """
    domain = "amazon.in" if country == "IN" else "amazon.com"
    url = "https://api.rainforestapi.com/request"
    params = {
        "api_key": api_key,
        "type": "product",
        "asin": asin,
        "amazon_domain": domain,
        "include_summarization_attributes": "true",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("request_info", {}).get("success", False):
            return None
        p = data.get("product", {})
        if not p:
            return None

        # Extract price from buybox
        price = None
        buybox = p.get("buybox_winner", {})
        if buybox:
            price_obj = buybox.get("price", {})
            price = price_obj.get("value")

        # Extract reviews
        reviews = []
        for r in p.get("top_reviews", []):
            reviews.append({
                "body": r.get("body", ""),
                "rating": r.get("rating", 0),
                "date": r.get("date", {}).get("utc", ""),
                "title": r.get("title", ""),
                "verified": r.get("verified_purchase", False),
            })

        return {
            "title": p.get("title", ""),
            "price": price,
            "price_display": f"₹{price:,.0f}" if price and country == "IN" else f"${price:,.2f}" if price else "N/A",
            "rating": p.get("rating"),
            "review_count": p.get("ratings_total", 0),
            "reviews": reviews,
            "asin": asin,
            "url": p.get("link", f"https://www.{domain}/dp/{asin}"),
            "source_method": "rainforest_api",
            "country": country,
            "brand": p.get("brand", ""),
            "main_image": p.get("main_image", {}).get("link", ""),
        }


async def _fetch_amazon_scrapingdog(asin: str, api_key: str, country: str = "IN") -> Optional[Dict]:
    """
    Fetch Amazon product data via ScrapingDog API.
    Free tier: 1,000 requests/month. Paid from $30/month.
    Signup: https://www.scrapingdog.com/amazon-scraper
    """
    domain = "amazon.in" if country == "IN" else "amazon.com"
    url = "https://api.scrapingdog.com/amazon/product"
    params = {
        "api_key": api_key,
        "asin": asin,
        "domain": domain,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("success", True) == False and "title" not in data:
            return None

        # Extract price
        price = None
        price_raw = data.get("price") or data.get("current_price")
        if price_raw:
            price_str = str(price_raw).replace("₹", "").replace("$", "").replace(",", "").strip()
            try:
                price = float(price_str)
            except ValueError:
                pass

        # Extract reviews
        reviews = []
        for r in data.get("reviews", []):
            reviews.append({
                "body": r.get("review_text", r.get("body", "")),
                "rating": float(r.get("rating", 0)),
                "date": r.get("date", ""),
                "title": r.get("review_title", r.get("title", "")),
                "verified": r.get("verified_purchase", False),
            })

        return {
            "title": data.get("title", data.get("product_title", "")),
            "price": price,
            "price_display": f"₹{price:,.0f}" if price and country == "IN" else f"${price:,.2f}" if price else "N/A",
            "rating": data.get("rating", data.get("stars")),
            "review_count": data.get("total_reviews", data.get("review_count", 0)),
            "reviews": reviews,
            "asin": asin,
            "url": f"https://www.{domain}/dp/{asin}",
            "source_method": "scrapingdog_api",
            "country": country,
            "brand": data.get("brand", ""),
        }

async def _fetch_amazon_reviews_scrapingdog(
    asin: str, api_key: str, country: str = "IN", max_pages: int = 10
) -> List[Dict]:
    """
    Fetch bulk Amazon reviews via ScrapingDog Reviews API.
    Dedicated endpoint: /amazon/reviews — returns ~10 reviews per page.
    Paginate up to max_pages (default 10 = ~100 reviews).
    Each page costs 1 API credit.
    """
    domain = "amazon.in" if country == "IN" else "amazon.com"
    domain_code = "in" if country == "IN" else "com"
    all_reviews = []

    async with httpx.AsyncClient(timeout=20) as client:
        for page in range(1, max_pages + 1):
            params = {
                "api_key": api_key,
                "asin": asin,
                "domain": domain_code,
                "page": str(page),
            }
            try:
                resp = await client.get(
                    "https://api.scrapingdog.com/amazon/reviews", params=params
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                reviews = data.get("customer_reviews", [])
                if not reviews:
                    break  # No more reviews

                for r in reviews:
                    # Parse rating — could be "5.0 out of 5 stars" or just "5.0"
                    rating_raw = str(r.get("rating", "0"))
                    try:
                        rating = float(rating_raw.split(" ")[0])
                    except (ValueError, IndexError):
                        rating = 0.0

                    # Check verified purchase
                    extension = r.get("extension", "")
                    verified = "verified" in str(extension).lower()

                    all_reviews.append({
                        "body": r.get("review", r.get("review_text", "")),
                        "rating": rating,
                        "title": r.get("title", r.get("review_title", "")),
                        "date": r.get("date", ""),
                        "author": r.get("user", r.get("customer_name", "")),
                        "verified": verified,
                        "source": "scrapingdog_reviews_api",
                    })

                # If we got fewer than 8 reviews, probably last page
                if len(reviews) < 8:
                    break

            except Exception:
                break  # Network error, stop pagination

    return all_reviews


async def _fetch_amazon_camoufox(asin: str, token: str, port: int = 9222, country: str = "IN") -> Optional[Dict]:
    """
    Fetch Amazon product data via Camoufox stealth browser (local server on port 9222).
    Bypasses CAPTCHAs and bot detection. Zero external API cost.
    Requires Camoufox browser server running locally.
    """
    domain = "amazon.in" if country == "IN" else "amazon.com"
    product_url = f"https://www.{domain}/dp/{asin}"
    base = f"http://localhost:{port}?token={token}"

    # JavaScript to extract product data + reviews (IIFE, no arrow functions — Camoufox compat)
    js_extract = """(function() {
        var data = {
            title: (document.querySelector('#productTitle') || {}).textContent || '',
            price_whole: (document.querySelector('.a-price-whole') || {}).textContent || '',
            price_fraction: (document.querySelector('.a-price-fraction') || {}).textContent || '',
            rating: '',
            review_count: (document.querySelector('#acrCustomerReviewText') || {}).textContent || '',
            brand: (document.querySelector('#bylineInfo') || {}).textContent || '',
            main_image: (document.querySelector('#landingImage') || {}).src || ''
        };
        var ratingEl = document.querySelector('#acrPopover span.a-size-base');
        if (ratingEl) data.rating = ratingEl.textContent.trim();
        var featureEls = document.querySelectorAll('#feature-bullets li span');
        data.features = [];
        for (var i = 0; i < featureEls.length; i++) {
            var t = featureEls[i].textContent.trim();
            if (t.length > 5) data.features.push(t);
        }
        data.title = data.title.trim();
        data.price_whole = data.price_whole.trim();
        data.price_fraction = data.price_fraction.trim();
        data.review_count = data.review_count.trim();
        data.brand = data.brand.trim();

        // Extract reviews from product page
        data.reviews = [];
        var reviewEls = document.querySelectorAll('[data-hook="review"]');
        for (var i = 0; i < reviewEls.length && i < 20; i++) {
            var el = reviewEls[i];
            var bodyEl = el.querySelector('[data-hook="review-body"] span');
            var rEl = el.querySelector('[data-hook="review-star-rating"] span, .review-rating span');
            var titleEl = el.querySelector('[data-hook="review-title"] span:last-child');
            var dateEl = el.querySelector('[data-hook="review-date"]');
            var vpEl = el.querySelector('[data-hook="avp-badge"]');
            var body = bodyEl ? bodyEl.textContent.trim() : '';
            var rText = rEl ? rEl.textContent.trim() : '';
            var rNum = parseFloat(rText) || 0;
            data.reviews.push({
                body: body,
                rating: rNum,
                title: titleEl ? titleEl.textContent.trim() : '',
                date: dateEl ? dateEl.textContent.trim().replace('Reviewed in India on ', '').replace('Reviewed in the United States on ', '') : '',
                verified: !!vpEl
            });
        }
        return JSON.stringify(data);
    })()"""

    async with httpx.AsyncClient(timeout=45) as client:
        # Single POST: navigate + wait + evaluate
        payload = {
            "url": product_url,
            "actions": [
                {"type": "wait", "ms": 2000},
                {"type": "evaluate", "script": js_extract},
            ],
            "screenshot": False,
            "timeout": 30000,
        }
        resp = await client.post(base, json=payload)
        if resp.status_code != 200:
            return None

        resp_data = resp.json()
        if not resp_data.get("success", False):
            return None

        page_title = resp_data.get("title", "")
        if "Robot Check" in page_title or "CAPTCHA" in page_title:
            return None

        results = resp_data.get("results", [])
        if not results or not results[0]:
            return None

        try:
            data = json.loads(results[0])
        except (json.JSONDecodeError, TypeError):
            return None

        title = data.get("title", "")
        if not title:
            return None

        # Parse price
        price = None
        price_whole = data.get("price_whole", "").replace(",", "").replace(".", "").strip()
        price_fraction = data.get("price_fraction", "00").strip()
        if price_whole:
            try:
                price = float(f"{price_whole}.{price_fraction}")
            except ValueError:
                pass

        # Parse rating
        rating = None
        rating_str = data.get("rating", "")
        if rating_str:
            try:
                rating = float(rating_str.split()[0])
            except (ValueError, IndexError):
                pass

        # Parse review count
        review_count = 0
        rc_str = data.get("review_count", "")
        if rc_str:
            rc_digits = re.sub(r'[^\d]', '', rc_str)
            if rc_digits:
                review_count = int(rc_digits)

        # Parse extracted reviews
        reviews = []
        for r in data.get("reviews", []):
            body = r.get("body", "")
            if body and len(body) > 5:  # Skip empty/tiny reviews
                reviews.append({
                    "body": body,
                    "rating": r.get("rating", 0),
                    "title": r.get("title", ""),
                    "date": r.get("date", ""),
                    "verified": r.get("verified", False),
                })

        return {
            "title": title,
            "price": price,
            "price_display": f"₹{price:,.0f}" if price and country == "IN" else f"${price:,.2f}" if price else "N/A",
            "rating": rating,
            "review_count": review_count,
            "reviews": reviews,
            "asin": asin,
            "url": product_url,
            "source_method": "camoufox_browser",
            "country": country,
            "brand": data.get("brand", "").replace("Visit the ", "").replace(" Store", ""),
            "main_image": data.get("main_image", ""),
            "features": data.get("features", []),
        }


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
            "User-Agent": "ShoppingTruthAgent/1.0 (by /u/shopping_truth_agent; contact: dev@shoppingtruth.app)",
        }
        
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 403:
                latency = (time.time() - start) * 1000
                return _failure("reddit_http", "Reddit blocks datacenter IPs. Works with PRAW credentials or from non-cloud servers.", latency)
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
    Fakespot was acquired by Mozilla in 2023. Their third-party API is defunct.
    We rely on our own XGBoost model (90.2% accuracy) for fake review detection.
    This function returns a graceful failure — it will be removed in a future cleanup.
    """
    return _failure("fakespot", "Fakespot API discontinued (acquired by Mozilla). Using local ML model instead.", 0)

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
        
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
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
        return _failure("reviewmeta", str(e) or "Request timeout", latency)

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
# SOURCE 11: Alternative Finder
# ============================================================

async def fetch_alternatives(product_name: str, current_price: float = None, category: str = "", country: str = "IN", keys: dict = None) -> Dict:
    """
    Find alternative products that may be cheaper or better rated.
    
    Priority:
    1. Google Shopping via SerpAPI (if key available) — structured data
    2. Amazon search HTTP fallback — always works
    
    Returns top 3-5 alternatives with title, price, rating, source, savings, why_better.
    """
    from .constants import MAX_ALTERNATIVES

    cache_key = _cache_key("alternatives", f"{product_name}:{country}")
    cached = _cache_get(cache_key)
    if cached:
        return _success("alternatives", cached, 0)

    start = time.time()
    alternatives = []

    # Strategy 1: Google Shopping via SerpAPI
    serpapi_key = (keys or {}).get("SERPAPI_KEY")
    if serpapi_key:
        try:
            alternatives = await _fetch_alternatives_google(product_name, current_price, category, country, serpapi_key)
        except Exception:
            alternatives = []

    # Strategy 2: Amazon search fallback
    if len(alternatives) < 2:
        try:
            amazon_alts = await _fetch_alternatives_amazon(product_name, current_price, category, country)
            # Merge, deduplicate by title similarity
            seen_titles = {a["title"].lower()[:30] for a in alternatives}
            for alt in amazon_alts:
                if alt["title"].lower()[:30] not in seen_titles:
                    alternatives.append(alt)
                    seen_titles.add(alt["title"].lower()[:30])
        except Exception:
            pass

    # Score and rank alternatives
    alternatives = _rank_alternatives(alternatives, current_price)

    # Limit to MAX_ALTERNATIVES
    alternatives = alternatives[:MAX_ALTERNATIVES]

    if not alternatives:
        latency = (time.time() - start) * 1000
        return _failure("alternatives", "No alternatives found", latency)

    result = {
        "found": len(alternatives),
        "alternatives": alternatives,
        "search_query": product_name,
    }

    latency = (time.time() - start) * 1000
    _cache_set(cache_key, result, ttl_seconds=3600)
    return _success("alternatives", result, latency)


async def _fetch_alternatives_google(product_name: str, current_price: float, category: str, country: str, serpapi_key: str) -> List[Dict]:
    """Fetch alternatives from Google Shopping via SerpAPI."""
    # Build a search query that finds competitors, not the exact product
    brand_word = product_name.split()[0] if product_name else ""
    # Remove brand from search to find alternatives from OTHER brands
    search_terms = product_name.split()
    if len(search_terms) > 2:
        # Use category keywords without brand: e.g. "wireless earbuds" instead of "Sony WF-1000XM5"
        generic_query = " ".join(search_terms[1:4]) if category else " ".join(search_terms[1:])
    else:
        generic_query = product_name

    if category:
        generic_query = f"best {category} {generic_query}"

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_shopping",
        "q": generic_query,
        "gl": country.lower(),
        "hl": "en",
        "num": 10,
        "api_key": serpapi_key,
    }

    alternatives = []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = data.get("shopping_results", [])

        product_name_lower = product_name.lower()
        for item in results[:10]:
            title = item.get("title", "")
            # Skip the exact same product
            if _is_same_product(title, product_name):
                continue

            price_numeric = item.get("extracted_price", 0)
            if not price_numeric or price_numeric <= 0:
                continue

            rating = item.get("rating")
            source = item.get("source", "Google Shopping")

            savings_pct = 0.0
            if current_price and current_price > 0 and price_numeric < current_price:
                savings_pct = round(((current_price - price_numeric) / current_price) * 100, 1)

            why_better = _determine_why_better(price_numeric, current_price, rating)

            alternatives.append({
                "title": title[:100],
                "price": price_numeric,
                "price_display": f"₹{price_numeric:,.0f}" if country == "IN" else f"${price_numeric:,.2f}",
                "rating": float(rating) if rating else None,
                "source": source,
                "link": item.get("link", ""),
                "savings_percentage": savings_pct,
                "why_better": why_better,
            })

    return alternatives


async def _fetch_alternatives_amazon(product_name: str, current_price: float, category: str, country: str) -> List[Dict]:
    """Fetch alternatives from Amazon search as fallback."""
    # Build generic search query
    search_terms = product_name.split()
    if len(search_terms) > 3:
        query = " ".join(search_terms[1:4])  # Skip brand, take 3 keywords
    else:
        query = product_name

    domain = "amazon.in" if country == "IN" else "amazon.com"
    url = f"https://www.{domain}/s"
    params = {"k": query, "ref": "nb_sb_noss"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    alternatives = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return []

            html = resp.text

            # Parse search results using regex
            # Each result card typically has data-asin attribute
            result_blocks = re.findall(
                r'data-asin="([A-Z0-9]{10})".*?(?=data-asin="|$)',
                html, re.DOTALL
            )

            # Simpler approach: extract product cards
            # Look for title + price pairs
            titles = re.findall(
                r'class="a-size-(?:medium|base-plus|mini)[^"]*"[^>]*>\s*<[^>]*>([^<]+)</(?:a|span)>',
                html
            )
            prices = re.findall(
                r'class="a-price-whole">([^<]+)',
                html
            )
            ratings_raw = re.findall(
                r'([\d.]+) out of 5 stars',
                html
            )

            product_name_lower = product_name.lower()
            for i in range(min(len(titles), len(prices), 8)):
                title = titles[i].strip()
                if not title or len(title) < 10:
                    continue
                # Skip the exact same product
                if _is_same_product(title, product_name):
                    continue

                try:
                    price_str = prices[i].strip().replace(',', '').replace('.', '')
                    price_numeric = float(price_str)
                except (ValueError, IndexError):
                    continue

                if price_numeric <= 0:
                    continue

                rating = None
                if i < len(ratings_raw):
                    try:
                        rating = float(ratings_raw[i])
                    except ValueError:
                        pass

                savings_pct = 0.0
                if current_price and current_price > 0 and price_numeric < current_price:
                    savings_pct = round(((current_price - price_numeric) / current_price) * 100, 1)

                why_better = _determine_why_better(price_numeric, current_price, rating)

                alternatives.append({
                    "title": title[:100],
                    "price": price_numeric,
                    "price_display": f"₹{price_numeric:,.0f}" if country == "IN" else f"${price_numeric:,.2f}",
                    "rating": rating,
                    "source": f"Amazon {'India' if country == 'IN' else 'US'}",
                    "link": f"https://www.{domain}/s?k={query.replace(' ', '+')}",
                    "savings_percentage": savings_pct,
                    "why_better": why_better,
                })

    except Exception:
        pass

    return alternatives


def _is_same_product(title_a: str, title_b: str) -> bool:
    """Check if two product titles refer to the same product."""
    a_words = set(title_a.lower().split()[:5])
    b_words = set(title_b.lower().split()[:5])
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
    return overlap > 0.7


def _determine_why_better(alt_price: float, current_price: float, alt_rating: float = None) -> str:
    """Determine why an alternative might be better."""
    reasons = []

    if current_price and alt_price:
        if alt_price < current_price * 0.85:
            reasons.append("Significantly cheaper")
        elif alt_price < current_price * 0.95:
            reasons.append("Cheaper")

    if alt_rating:
        if alt_rating >= 4.5:
            reasons.append("Highly rated (4.5+★)")
        elif alt_rating >= 4.2:
            reasons.append("Well rated (4.2+★)")

    if not reasons:
        if current_price and alt_price and alt_price <= current_price:
            reasons.append("Competitive price")
        else:
            reasons.append("Popular alternative")

    return " • ".join(reasons)


def _rank_alternatives(alternatives: List[Dict], current_price: float = None) -> List[Dict]:
    """Rank alternatives by a composite score: savings + rating."""
    for alt in alternatives:
        score = 0.0
        # Savings weight (40%)
        if alt.get("savings_percentage", 0) > 0:
            score += min(alt["savings_percentage"] / 50.0, 1.0) * 40
        # Rating weight (35%)
        if alt.get("rating"):
            score += (alt["rating"] / 5.0) * 35
        # Price penalty if MORE expensive (25%)
        if current_price and alt.get("price"):
            if alt["price"] <= current_price:
                score += 25
            else:
                score += max(0, 25 - ((alt["price"] - current_price) / current_price) * 50)
        alt["_score"] = score

    alternatives.sort(key=lambda x: x.get("_score", 0), reverse=True)

    # Remove internal score from output
    for alt in alternatives:
        alt.pop("_score", None)

    return alternatives


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
        # Fakespot removed — API defunct (acquired by Mozilla 2023)
        # Our XGBoost ML model handles fake review detection locally
        # ReviewMeta removed — consistently times out, scraping-based (not a real API)
        # Local XGBoost ML (95.2%) handles fake review detection instead
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
