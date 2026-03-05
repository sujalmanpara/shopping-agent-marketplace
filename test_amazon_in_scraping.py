#!/usr/bin/env python3
import asyncio
from scrapling import Fetcher

async def test_amazon_in():
    asin = "B00V4L6JC2"
    url = f"https://www.amazon.in/dp/{asin}"
    
    print(f"🔍 Scraping: {url}")
    print("=" * 60)
    
    fetcher = Fetcher()
    response = await asyncio.to_thread(fetcher.get, url, timeout=30)
    
    print(f"✅ Status: {response.status}")
    print(f"📄 HTML Length: {len(response.text)} bytes")
    print("\n🔎 Looking for product data...")
    
    # Debug: Find title element
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Try multiple selectors
    title_selectors = [
        "#productTitle",
        "span#productTitle",
        ".product-title-word-break",
        "[data-feature-name='title']"
    ]
    
    for selector in title_selectors:
        elem = soup.select_one(selector)
        if elem:
            print(f"✅ Found title with: {selector}")
            print(f"   → {elem.get_text(strip=True)[:80]}")
            break
    else:
        print("❌ Title not found with any selector")
        
        # Show what we got
        print("\n🔍 HTML snippet (first 1000 chars):")
        print(response.text[:1000])

asyncio.run(test_amazon_in())
