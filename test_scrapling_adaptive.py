#!/usr/bin/env python3
import asyncio
from scrapling import Fetcher

async def test_adaptive():
    asin = "B00V4L6JC2"
    url = f"https://www.amazon.in/dp/{asin}"
    
    print("🧪 Testing Scrapling Adaptive Mode")
    print("=" * 60)
    
    # Configure Fetcher for Amazon
    Fetcher.configure(
        headers={'Accept-Language': 'en-US,en;q=0.9'},
        verify=True
    )
    
    fetcher = Fetcher(adaptive=True)  # Enable adaptive mode
    
    print(f"🔍 Fetching: {url}")
    response = await asyncio.to_thread(fetcher.get, url, timeout=30)
    
    print(f"✅ Status: {response.status}")
    print(f"📄 Content type: {response.headers.get('content-type', 'unknown')}")
    print(f"📏 Response length: {len(response.text)} bytes")
    
    if len(response.text) > 0:
        # Check for bot detection
        if 'robot' in response.text.lower() or 'captcha' in response.text.lower():
            print("❌ Bot detection triggered!")
        else:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.select_one("#productTitle")
            if title:
                print(f"✅ Product title: {title.get_text(strip=True)[:80]}")
            else:
                print("⚠️  Title not found (checking HTML structure...)")
                # Show first few tags
                print(f"   First tags: {[tag.name for tag in soup.find_all()[:20]]}")
    else:
        print("❌ Empty response!")

asyncio.run(test_adaptive())
