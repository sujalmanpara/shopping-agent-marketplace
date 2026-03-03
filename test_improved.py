#!/usr/bin/env python3
import asyncio
import os
import httpx
from bs4 import BeautifulSoup
import re

async def test_amazon_in(asin):
    """Test with Amazon India"""
    url = f"https://www.amazon.in/dp/{asin}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    print(f"🔍 Testing Amazon India scraper...")
    print(f"URL: {url}\n")
    
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Try multiple selectors for title
            title = None
            for selector in ["#productTitle", "#title", "h1.product-title"]:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    break
            
            # Try multiple selectors for price
            price = None
            for selector in [".a-price .a-offscreen", "#priceblock_ourprice", ".a-price-whole"]:
                elem = soup.select_one(selector)
                if elem:
                    price = elem.get_text(strip=True)
                    break
            
            # Try multiple selectors for rating
            rating = 0.0
            for selector in ["[data-hook='rating-out-of-text']", ".a-icon-star", "#acrPopover"]:
                elem = soup.select_one(selector)
                if elem:
                    rating_text = elem.get_text(strip=True)
                    match = re.search(r'([\d.]+)', rating_text)
                    if match:
                        rating = float(match.group(1))
                        break
            
            # Review count
            review_count = 0
            for selector in ["#acrCustomerReviewText", "[data-hook='total-review-count']"]:
                elem = soup.select_one(selector)
                if elem:
                    count_text = elem.get_text(strip=True)
                    match = re.search(r'([\d,]+)', count_text)
                    if match:
                        review_count = int(match.group(1).replace(',', ''))
                        break
            
            print("✅ Scraped data:")
            print(f"   Title: {title or 'Not found'}")
            print(f"   Price: {price or 'Not found'}")
            print(f"   Rating: {rating}/5")
            print(f"   Reviews: {review_count:,}")
            
            if not title:
                print("\n⚠️ Could not extract title. Showing page snippet:")
                print(soup.get_text()[:500])
            
            # Now generate verdict
            if title and rating > 0:
                api_key = os.getenv("OPENAI_API_KEY")
                context = f"""
Product: {title}
Price: {price or 'Not shown'}
Rating: {rating}/5 ({review_count:,} reviews)
Platform: Amazon India

Analyze this product and give a verdict: BUY, WAIT, or AVOID.
Be specific about value for money and any red flags.
2-3 sentences max.
"""
                
                print("\n⏳ Asking AI for verdict...")
                llm_resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a shopping advisor for Indian consumers."},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 200,
                        "temperature": 0.3
                    }
                )
                
                result = llm_resp.json()
                verdict = result["choices"][0]["message"]["content"]
                
                print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print("🤖 AI Verdict:")
                print(verdict)
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_amazon_in("B00V4L6JC2"))
