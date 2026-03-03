#!/usr/bin/env python3
"""
Live test of Shopping Truth Agent
Simulates the full agent workflow
"""

import asyncio
import os
import sys
import httpx
from bs4 import BeautifulSoup
import re
import random
from typing import Dict, List

# Constants
REQUEST_DELAY = 2
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]
SCRAPE_TIMEOUT = 15
REDDIT_OLD = "https://old.reddit.com"

def _random_user_agent():
    return random.choice(USER_AGENTS)

def extract_asin(url_or_text: str):
    match = re.search(r'/dp/([A-Z0-9]{10})', url_or_text)
    if not match:
        match = re.search(r'/gp/product/([A-Z0-9]{10})', url_or_text)
    return match.group(1) if match else None

async def scrape_amazon_mini(client, asin):
    """Lightweight Amazon scraper for testing"""
    url = f"https://www.amazon.com/dp/{asin}"
    headers = {"User-Agent": _random_user_agent()}
    try:
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title_elem = soup.select_one("#productTitle")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        
        price_elem = soup.select_one(".a-price .a-offscreen")
        price = price_elem.get_text(strip=True) if price_elem else "N/A"
        
        rating_elem = soup.select_one("[data-hook='rating-out-of-text']")
        rating_text = rating_elem.get_text(strip=True) if rating_elem else "0 out of 5"
        rating = float(re.search(r'([\d.]+)', rating_text).group(1)) if rating_text else 0.0
        
        return {
            "title": title,
            "price": price,
            "rating": rating,
            "url": url
        }
    except Exception as e:
        return {"error": str(e)}

async def scrape_reddit_mini(client, product_name):
    """Lightweight Reddit scraper"""
    query = product_name.replace(" ", "+")
    url = f"{REDDIT_OLD}/search?q={query}&sort=relevance"
    headers = {"User-Agent": _random_user_agent()}
    try:
        await asyncio.sleep(REQUEST_DELAY)
        resp = await client.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        posts = soup.select(".thing")[:10]
        return {"found": len(posts)}
    except Exception as e:
        return {"found": 0, "error": str(e)}

async def test_agent(product_url: str):
    """Test the full agent workflow"""
    
    print("🛒 Shopping Truth Agent - Live Test")
    print("=" * 60)
    
    # Extract ASIN
    asin = extract_asin(product_url)
    if not asin:
        print("❌ Invalid Amazon URL")
        return
    
    print(f"✅ ASIN extracted: {asin}")
    print(f"🔗 URL: {product_url}\n")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Phase 1: Scrape Amazon
        print("⏳ Scraping Amazon...")
        amazon_data = await scrape_amazon_mini(client, asin)
        
        if "error" in amazon_data:
            print(f"❌ Amazon scraping failed: {amazon_data['error']}")
            return
        
        print(f"✅ Product: {amazon_data['title'][:80]}...")
        print(f"💰 Price: {amazon_data['price']}")
        print(f"⭐ Rating: {amazon_data['rating']}/5\n")
        
        # Phase 2: Scrape Reddit
        print("⏳ Checking Reddit...")
        reddit_data = await scrape_reddit_mini(client, amazon_data['title'])
        print(f"✅ Reddit: {reddit_data['found']} mentions found\n")
        
        # Phase 3: Generate summary (using OpenAI)
        print("⏳ Generating AI summary...")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return
        
        # Simple context for LLM
        context = f"""
Product: {amazon_data['title']}
Price: {amazon_data['price']}
Rating: {amazon_data['rating']}/5
Reddit Mentions: {reddit_data['found']}

Analyze this product and give a verdict: BUY, WAIT, or AVOID.
Be concise (2-3 sentences).
"""
        
        try:
            llm_resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a brutally honest shopping advisor."},
                        {"role": "user", "content": context}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.3
                }
            )
            
            result = llm_resp.json()
            summary = result["choices"][0]["message"]["content"]
            
            print("✅ AI Verdict:")
            print("━" * 60)
            print(summary)
            print("━" * 60)
            
        except Exception as e:
            print(f"❌ LLM API failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Amazon product URL: ")
    
    asyncio.run(test_agent(url))
