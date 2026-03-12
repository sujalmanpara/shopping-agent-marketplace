# stealth_scraper.py — Hybrid Scraping Engine (Scrapling + Camoufox)
#
# Smart routing:
#   EASY sites → Scrapling (fast, lightweight)
#   HARD sites → Camoufox (stealth, undetectable)
#   UNKNOWN    → Scrapling first, Camoufox fallback

import asyncio
import json
import sys
import subprocess
import re
from typing import Dict, Optional, List
from pathlib import Path
from bs4 import BeautifulSoup

# Scrapling imports (fast path)
from scrapling import Fetcher, StealthyFetcher

# Camoufox path
CAMOUFOX_VENV = "/root/.openclaw/workspace/camoufox-env/lib/python3.12/site-packages"
CAMOUFOX_SKILL = "/root/.openclaw/skills/camoufox-browser"

# Site classification
CAMOUFOX_SITES = {
    "amazon", "walmart", "target", "bestbuy", "flipkart",
    "youtube", "tiktok", "twitter", "x.com",
    "consumerreports"
}

SCRAPLING_SITES = {
    "reddit", "wirecutter", "rtings",
    "trustpilot", "fakespot", "bbb"
}


def classify_site(url: str) -> str:
    """Classify URL into easy (scrapling) or hard (camoufox)"""
    url_lower = url.lower()
    for site in CAMOUFOX_SITES:
        if site in url_lower:
            return "camoufox"
    for site in SCRAPLING_SITES:
        if site in url_lower:
            return "scrapling"
    return "auto"  # Try scrapling first, fallback to camoufox


async def scrapling_fetch(url: str, stealthy: bool = False, timeout: int = 15) -> Optional[str]:
    """Fast path: Scrapling fetcher"""
    try:
        if stealthy:
            response = await asyncio.to_thread(
                StealthyFetcher.fetch,
                url,
                headless=True,
                network_idle=True,
                timeout=timeout
            )
        else:
            fetcher = Fetcher()
            response = await asyncio.to_thread(fetcher.get, url, timeout=timeout)
        return response.text if response else None
    except Exception as e:
        return None


async def camoufox_fetch(url: str, timeout: int = 30, wait_for: str = None) -> Optional[str]:
    """
    Stealth path: Camoufox browser fetch
    Runs as subprocess to avoid import conflicts
    """
    script = f"""
import sys
sys.path.insert(0, '{CAMOUFOX_VENV}')
import time
from camoufox.sync_api import Camoufox

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto('{url}', timeout={timeout * 1000})
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except:
        pass
    {"page.wait_for_selector('" + wait_for + "', timeout=10000)" if wait_for else "time.sleep(2)"}
    print(page.content())
"""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 10)
        
        if proc.returncode == 0 and stdout:
            return stdout.decode('utf-8', errors='ignore')
        return None
    except (asyncio.TimeoutError, Exception):
        return None


async def camoufox_screenshot(url: str, output_path: str, timeout: int = 30) -> bool:
    """Take screenshot via Camoufox"""
    script = f"""
import sys
sys.path.insert(0, '{CAMOUFOX_VENV}')
import time
from camoufox.sync_api import Camoufox

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto('{url}', timeout={timeout * 1000})
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except:
        pass
    time.sleep(2)
    page.screenshot(path='{output_path}')
    print('OK')
"""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 10)
        return proc.returncode == 0
    except:
        return False


async def smart_fetch(url: str, timeout: int = 20) -> Optional[str]:
    """
    Smart fetch: Routes to best scraper based on URL
    
    Easy sites → Scrapling (fast)
    Hard sites → Camoufox (stealth)
    Unknown → Scrapling first, Camoufox fallback
    """
    site_type = classify_site(url)
    
    if site_type == "scrapling":
        # Fast path
        html = await scrapling_fetch(url, stealthy=False, timeout=timeout)
        if html and len(html) > 500:
            return html
        # If basic fetch failed, try stealthy
        return await scrapling_fetch(url, stealthy=True, timeout=timeout)
    
    elif site_type == "camoufox":
        # Stealth path
        return await camoufox_fetch(url, timeout=timeout)
    
    else:
        # Auto: Try scrapling first (fast), fallback to camoufox
        html = await scrapling_fetch(url, stealthy=True, timeout=timeout)
        if html and len(html) > 500:
            # Verify we got real content (not a block page)
            if not _is_blocked(html):
                return html
        
        # Fallback to Camoufox
        return await camoufox_fetch(url, timeout=timeout)


def _is_blocked(html: str) -> bool:
    """Check if response is a block/challenge page"""
    block_indicators = [
        "captcha", "challenge", "blocked", "access denied",
        "please verify", "are you a robot", "enable javascript",
        "cloudflare", "security check", "just a moment"
    ]
    html_lower = html.lower()[:2000]  # Check first 2000 chars
    return any(indicator in html_lower for indicator in block_indicators)


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML with BeautifulSoup"""
    return BeautifulSoup(html, "html.parser")


# ============================================================
# High-level scraping functions for specific platforms
# ============================================================

async def scrape_walmart_reviews(product_name: str) -> Dict:
    """Scrape Walmart product reviews"""
    query = product_name.replace(" ", "+")
    url = f"https://www.walmart.com/search?q={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch Walmart", "reviews": [], "source": "walmart"}
    
    soup = parse_html(html)
    
    products = []
    for item in soup.select('[data-item-id], [data-testid="list-view"]')[:5]:
        title_elem = item.select_one('[data-automation-id="product-title"], span.lh-title')
        price_elem = item.select_one('[data-automation-id="product-price"] span, [itemprop="price"]')
        rating_elem = item.select_one('[data-testid="product-ratings"] span, .stars-container')
        
        if title_elem:
            products.append({
                "title": title_elem.get_text(strip=True)[:100],
                "price": price_elem.get_text(strip=True) if price_elem else "N/A",
                "rating": rating_elem.get_text(strip=True) if rating_elem else "N/A",
            })
    
    return {
        "found": len(products),
        "products": products,
        "source": "walmart"
    }


async def scrape_target_reviews(product_name: str) -> Dict:
    """Scrape Target product reviews"""
    query = product_name.replace(" ", "+")
    url = f"https://www.target.com/s?searchTerm={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch Target", "reviews": [], "source": "target"}
    
    soup = parse_html(html)
    
    products = []
    for item in soup.select('[data-test="product-card"], .styles__StyledProductCardContainer-sc')[:5]:
        title_elem = item.select_one('a[data-test="product-title"], .ProductCardTitle')
        price_elem = item.select_one('[data-test="current-price"] span, .styles__PriceFontSize')
        rating_elem = item.select_one('[data-test="ratings"] span')
        
        if title_elem:
            products.append({
                "title": title_elem.get_text(strip=True)[:100],
                "price": price_elem.get_text(strip=True) if price_elem else "N/A",
                "rating": rating_elem.get_text(strip=True) if rating_elem else "N/A",
            })
    
    return {
        "found": len(products),
        "products": products,
        "source": "target"
    }


async def scrape_bestbuy_reviews(product_name: str) -> Dict:
    """Scrape Best Buy product reviews"""
    query = product_name.replace(" ", "+")
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch BestBuy", "reviews": [], "source": "bestbuy"}
    
    soup = parse_html(html)
    
    products = []
    for item in soup.select('.sku-item, .list-item')[:5]:
        title_elem = item.select_one('.sku-title a, .sku-header a')
        price_elem = item.select_one('.priceView-hero-price span, .priceView-customer-price span')
        rating_elem = item.select_one('.c-ratings-reviews .c-stars, .c-ratings-reviews-v4')
        review_elem = item.select_one('.c-ratings-reviews span.c-reviews')
        
        if title_elem:
            products.append({
                "title": title_elem.get_text(strip=True)[:100],
                "price": price_elem.get_text(strip=True) if price_elem else "N/A",
                "rating": rating_elem.get_attribute_list('aria-label')[0] if rating_elem else "N/A",
                "review_count": review_elem.get_text(strip=True) if review_elem else "0",
            })
    
    return {
        "found": len(products),
        "products": products,
        "source": "bestbuy"
    }


async def scrape_flipkart_reviews(product_name: str) -> Dict:
    """Scrape Flipkart product reviews (India)"""
    query = product_name.replace(" ", "+")
    url = f"https://www.flipkart.com/search?q={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch Flipkart", "reviews": [], "source": "flipkart"}
    
    soup = parse_html(html)
    
    products = []
    for item in soup.select('._1AtVbE, ._1xHGtK, [data-id]')[:5]:
        title_elem = item.select_one('._4rR01T, .s1Q9rs, .IRpwTa')
        price_elem = item.select_one('._30jeq3, ._1_WHN1')
        rating_elem = item.select_one('._3LWZlK, .gUuXy-')
        review_elem = item.select_one('._2_R_DZ span, ._13vcmD')
        
        if title_elem:
            products.append({
                "title": title_elem.get_text(strip=True)[:100],
                "price": price_elem.get_text(strip=True) if price_elem else "N/A",
                "rating": rating_elem.get_text(strip=True) if rating_elem else "N/A",
                "reviews": review_elem.get_text(strip=True) if review_elem else "0",
            })
    
    return {
        "found": len(products),
        "products": products,
        "source": "flipkart"
    }


async def scrape_tiktok_reviews(product_name: str) -> Dict:
    """Scrape TikTok product mentions (Camoufox REQUIRED)"""
    query = product_name.replace(" ", "%20")
    url = f"https://www.tiktok.com/search?q={query}%20review"
    
    html = await camoufox_fetch(url, timeout=30)
    if not html:
        return {"found": 0, "error": "Failed to fetch TikTok", "source": "tiktok"}
    
    soup = parse_html(html)
    
    # TikTok uses heavy JS, extract what we can
    video_count = len(re.findall(r'video-card|DivItemCard|tiktok-embed', html))
    
    return {
        "found": video_count,
        "sentiment": "Viral" if video_count > 10 else "Moderate" if video_count > 3 else "Low",
        "source": "tiktok"
    }


async def scrape_trustpilot(brand_name: str) -> Dict:
    """Scrape Trustpilot brand reputation"""
    brand_slug = brand_name.lower().replace(" ", "")
    url = f"https://www.trustpilot.com/review/{brand_slug}.com"
    
    html = await smart_fetch(url)
    if not html:
        # Try search
        url = f"https://www.trustpilot.com/search?query={brand_name}"
        html = await smart_fetch(url)
    
    if not html:
        return {"found": False, "error": "Failed to fetch Trustpilot", "source": "trustpilot"}
    
    soup = parse_html(html)
    
    score_elem = soup.select_one('[data-rating-typography], .typography_heading-m__T_L_7')
    review_count_elem = soup.select_one('[data-reviews-count-typography], .styles_text__W4hWi')
    
    return {
        "found": True,
        "trust_score": score_elem.get_text(strip=True) if score_elem else "N/A",
        "review_count": review_count_elem.get_text(strip=True) if review_count_elem else "N/A",
        "url": url,
        "source": "trustpilot"
    }


async def scrape_wirecutter(product_name: str) -> Dict:
    """Scrape Wirecutter (NYT) recommendations"""
    query = product_name.replace(" ", "+")
    url = f"https://www.nytimes.com/wirecutter/search/?s={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch Wirecutter", "source": "wirecutter"}
    
    soup = parse_html(html)
    
    results = []
    for item in soup.select('.SearchResults-item, .searchResults-item, article')[:5]:
        title_elem = item.select_one('h3, .SearchResults-title, a')
        snippet_elem = item.select_one('p, .SearchResults-snippet')
        
        if title_elem:
            results.append({
                "title": title_elem.get_text(strip=True)[:100],
                "snippet": snippet_elem.get_text(strip=True)[:200] if snippet_elem else "",
            })
    
    return {
        "found": len(results),
        "results": results,
        "source": "wirecutter"
    }


async def scrape_rtings(product_name: str) -> Dict:
    """Scrape RTINGS detailed test results"""
    query = product_name.replace(" ", "+")
    url = f"https://www.rtings.com/search?query={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch RTINGS", "source": "rtings"}
    
    soup = parse_html(html)
    
    results = []
    for item in soup.select('.search-result, .searchResult, .product_card')[:5]:
        title_elem = item.select_one('a, h3, .product_name')
        score_elem = item.select_one('.score, .overall-score, .e-score')
        
        if title_elem:
            results.append({
                "title": title_elem.get_text(strip=True)[:100],
                "score": score_elem.get_text(strip=True) if score_elem else "N/A",
            })
    
    return {
        "found": len(results),
        "results": results,
        "source": "rtings"
    }


async def scrape_consumer_reports(product_name: str) -> Dict:
    """Scrape Consumer Reports (Camoufox for paywall bypass)"""
    query = product_name.replace(" ", "+")
    url = f"https://www.consumerreports.org/search/?query={query}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": 0, "error": "Failed to fetch Consumer Reports", "source": "consumer_reports"}
    
    soup = parse_html(html)
    
    results = []
    for item in soup.select('.search-result-item, .crux-body-copy, article')[:5]:
        title_elem = item.select_one('h3, a, .search-result-title')
        
        if title_elem:
            results.append({
                "title": title_elem.get_text(strip=True)[:100],
            })
    
    return {
        "found": len(results),
        "results": results,
        "source": "consumer_reports"
    }


async def scrape_fakespot(asin: str) -> Dict:
    """Check Fakespot review grade for Amazon product"""
    url = f"https://www.fakespot.com/product/{asin}"
    
    html = await smart_fetch(url)
    if not html:
        return {"found": False, "error": "Failed to fetch Fakespot", "source": "fakespot"}
    
    soup = parse_html(html)
    
    grade_elem = soup.select_one('.grade-box, .review-grade, [class*="grade"]')
    
    return {
        "found": True if grade_elem else False,
        "grade": grade_elem.get_text(strip=True) if grade_elem else "N/A",
        "url": url,
        "source": "fakespot"
    }


# ============================================================
# Multi-Platform Aggregator
# ============================================================

async def scrape_all_platforms(product_name: str, asin: str = None, brand: str = None) -> Dict:
    """
    Scrape ALL 15 platforms concurrently using hybrid approach
    
    Returns aggregated data from all sources
    """
    
    # Build tasks
    tasks = {}
    
    # E-Commerce (Camoufox)
    tasks["walmart"] = scrape_walmart_reviews(product_name)
    tasks["target"] = scrape_target_reviews(product_name)
    tasks["bestbuy"] = scrape_bestbuy_reviews(product_name)
    tasks["flipkart"] = scrape_flipkart_reviews(product_name)
    
    # Social (Mixed)
    tasks["tiktok"] = scrape_tiktok_reviews(product_name)
    
    # Expert (Scrapling)
    tasks["wirecutter"] = scrape_wirecutter(product_name)
    tasks["rtings"] = scrape_rtings(product_name)
    tasks["consumer_reports"] = scrape_consumer_reports(product_name)
    
    # Trust (Scrapling)
    if brand:
        tasks["trustpilot"] = scrape_trustpilot(brand)
    if asin:
        tasks["fakespot"] = scrape_fakespot(asin)
    
    # Run all concurrently
    keys = list(tasks.keys())
    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    # Compile results
    results = {}
    successful = 0
    failed = 0
    
    for key, result in zip(keys, results_list):
        if isinstance(result, Exception):
            results[key] = {"error": str(result), "source": key}
            failed += 1
        else:
            results[key] = result
            if result.get("found", 0) or result.get("products", []):
                successful += 1
            else:
                failed += 1
    
    return {
        "platforms_scraped": len(keys),
        "successful": successful,
        "failed": failed,
        "success_rate": f"{(successful / len(keys) * 100):.0f}%",
        "data": results
    }
