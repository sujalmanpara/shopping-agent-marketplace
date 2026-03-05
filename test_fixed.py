import asyncio
import os
import sys
import httpx
sys.path.insert(0, 'agent')

# Import FIXED scraper
import importlib.util
spec = importlib.util.spec_from_file_location("scrapers_fixed", "agent/scrapers_fixed.py")
scrapers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scrapers)

from agent.analyzers import *

async def main(url):
    asin = scrapers.extract_asin(url)
    print(f"🔗 ASIN: {asin}\n")
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("⏳ Scraping Amazon India...")
        amazon_data = await scrapers.scrape_amazon(client, asin)
        
        print(f"\n📦 Product: {amazon_data.get('title')}")
        print(f"💰 Price: {amazon_data.get('price')}")
        print(f"⭐ Rating: {amazon_data.get('rating')}/5 ({amazon_data.get('review_count'):,} reviews)")
        print(f"📝 Reviews extracted: {len(amazon_data.get('reviews', []))}")
        
        if amazon_data.get('title') != "Unknown Product":
            print("\n✅ Scraping SUCCESS!")
            
            # Run all features
            print("\n⏳ Running all 10 features...")
            product_name = amazon_data.get('title')
            brand = product_name.split()[0]
            
            reddit_data = await scrapers.scrape_reddit(client, product_name)
            youtube_data = await scrapers.scrape_youtube(client, product_name)
            fake_analysis = analyze_fake_reviews(amazon_data.get('reviews', []))
            regret = analyze_regret_pattern(amazon_data.get('reviews', []))
            confidence = calculate_confidence(amazon_data, reddit_data, youtube_data, {})
            price_pred = await scrapers.scrape_price_history(client, asin)
            alternatives = await scrapers.find_alternatives(client, product_name, amazon_data.get('price'))
            coupons = await scrapers.find_coupons(client, product_name, asin)
            ethics = await scrapers.calculate_ethics_score(client, product_name, brand)
            
            # AI Verdict
            api_key = os.getenv("OPENAI_API_KEY")
            context = f"Product: {product_name[:100]}\nPrice: {amazon_data.get('price')}\nRating: {amazon_data.get('rating')}/5\nFake Risk: {fake_analysis['risk']}\nVerdict (BUY/WAIT/AVOID, 2 sentences):"
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": context}], "max_tokens": 150})
            verdict = resp.json()["choices"][0]["message"]["content"]
            
            print("\n" + "━"*60)
            print("🛒 COMPLETE ANALYSIS")
            print("━"*60)
            print(f"\n📊 Multi-Platform: {amazon_data.get('review_count'):,} Amazon reviews | {reddit_data.get('found')} Reddit | {youtube_data.get('found')} YouTube")
            print(f"🕵️ Fake Reviews: {fake_analysis['risk'].upper()} risk ({fake_analysis['score']}%)")
            print(f"🎯 Confidence: {confidence}%")
            if price_pred.get('prediction'):
                print(f"💰 Price: {price_pred['prediction']['advice']}")
            if alternatives['found'] > 0:
                print(f"🔄 Alternatives: {alternatives['found']} cheaper options found")
            if coupons['found'] > 0:
                print(f"🎟️ Coupons: {coupons['coupons'][0]['code']} ({coupons['coupons'][0]['discount']})")
            print(f"🌍 Ethics: Grade {ethics['ethics']['grade']} | {ethics['carbon_footprint']['co2_kg']}kg CO2")
            print(f"\n🤖 AI VERDICT:\n{verdict}")
            print("━"*60)
        else:
            print("\n❌ Scraping FAILED - couldn't extract data")

asyncio.run(main(sys.argv[1]))
