#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.insert(0, 'agent')

import httpx
from agent.scrapers import *
from agent.analyzers import *

def format_output(amazon_data, fake_analysis, regret_analysis, confidence, reddit_data, youtube_data, twitter_data, price_prediction, alternatives, coupons, ethics, ai_verdict):
    output = []
    output.append("━" * 60)
    output.append("🛒 SHOPPING TRUTH AGENT - COMPLETE ANALYSIS")
    output.append("━" * 60)
    output.append(f"\n📦 **Product:** {amazon_data.get('title', 'Unknown')}")
    output.append(f"💰 **Price:** {amazon_data.get('price', 'N/A')}")
    output.append(f"⭐ **Rating:** {amazon_data.get('rating', 0)}/5 ({amazon_data.get('review_count', 0):,} reviews)")
    output.append("\n" + "─" * 60)
    output.append("📊 MULTI-PLATFORM ANALYSIS (Features 1-2)")
    output.append("─" * 60)
    output.append(f"✅ Amazon: {amazon_data.get('review_count', 0):,} reviews")
    output.append(f"✅ Reddit: {reddit_data.get('found', 0)} mentions")
    output.append(f"✅ YouTube: {youtube_data.get('found', 0)} video reviews")
    output.append(f"✅ Twitter: {twitter_data.get('found', 0)} tweets")
    output.append("\n" + "─" * 60)
    output.append("🕵️ FAKE REVIEW DETECTION (Feature 3)")
    output.append("─" * 60)
    risk_emoji = "🔴" if fake_analysis['risk'] == "high" else "🟡" if fake_analysis['risk'] == "medium" else "🟢"
    output.append(f"{risk_emoji} **Risk Level:** {fake_analysis['risk'].upper()}")
    output.append(f"📊 **Fake Score:** {fake_analysis['score']}% suspicious")
    output.append("\n" + "─" * 60)
    output.append("⏰ REGRET DETECTOR (Feature 4)")
    output.append("─" * 60)
    if regret_analysis.get('warning'):
        output.append(f"⚠️  {regret_analysis['warning']}")
    else:
        output.append("✅ **No regret detected** - Ratings stable")
    output.append("\n" + "─" * 60)
    output.append("🎯 CONFIDENCE SCORE (Feature 5)")
    output.append("─" * 60)
    conf_emoji = "🟢" if confidence >= 70 else "🟡" if confidence >= 50 else "🔴"
    output.append(f"{conf_emoji} **Confidence:** {confidence}%")
    if price_prediction and price_prediction.get('prediction'):
        output.append("\n" + "─" * 60)
        output.append("💰 PRICE DROP PREDICTION (Feature 7)")
        output.append("─" * 60)
        pred = price_prediction['prediction']
        output.append(f"🎯 **Event:** {pred['event']}")
        output.append(f"💡 **Advice:** {pred['advice']}")
    if alternatives and alternatives.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🔄 BETTER ALTERNATIVES (Feature 8)")
        output.append("─" * 60)
        for i, alt in enumerate(alternatives.get('alternatives', [])[:2], 1):
            output.append(f"{i}. {alt['title'][:50]}...")
            output.append(f"   💰 {alt['price']} | ⭐ {alt['rating']}/5 | 💵 {alt['savings']}")
    if coupons and coupons.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🎟️  COUPON CODES (Feature 9)")
        output.append("─" * 60)
        for coupon in coupons.get('coupons', []):
            output.append(f"💰 {coupon['code']}: {coupon['discount']}")
    if ethics and ethics.get('carbon_footprint'):
        output.append("\n" + "─" * 60)
        output.append("🌍 CARBON & ETHICS (Feature 10)")
        output.append("─" * 60)
        output.append(f"🌍 Carbon: {ethics['carbon_footprint']['co2_kg']} kg CO2")
        if ethics.get('ethics'):
            output.append(f"🏷️  Ethics: Grade {ethics['ethics']['grade']}")
    output.append("\n" + "─" * 60)
    output.append("🤖 AI VERDICT (Feature 6)")
    output.append("─" * 60)
    if "BUY" in ai_verdict.upper() and "AVOID" not in ai_verdict.upper():
        output.append("\n✅ **BUY**")
    elif "AVOID" in ai_verdict.upper():
        output.append("\n❌ **AVOID**")
    else:
        output.append("\n⏳ **WAIT**")
    output.append(f"\n{ai_verdict}")
    output.append("\n" + "━" * 60)
    return "\n".join(output)

async def main(url):
    asin = extract_asin(url)
    if not asin:
        print("❌ Invalid Amazon URL")
        return
    
    async with httpx.AsyncClient(timeout=30) as client:
        amazon_data = await scrape_amazon(client, asin)
        if "error" in amazon_data:
            print(f"❌ {amazon_data['error']}")
            return
        
        product_name = amazon_data.get('title', '')
        brand = product_name.split()[0] if product_name else ''
        
        reddit_data = await scrape_reddit(client, product_name)
        youtube_data = await scrape_youtube(client, product_name)
        twitter_data = await scrape_twitter(client, product_name)
        fake_analysis = analyze_fake_reviews(amazon_data.get('reviews', []))
        regret_analysis = analyze_regret_pattern(amazon_data.get('reviews', []))
        confidence = calculate_confidence(amazon_data, reddit_data, youtube_data, twitter_data)
        price_pred = await scrape_price_history(client, asin)
        alternatives = await find_alternatives(client, product_name, amazon_data.get('price', ''))
        coupons = await find_coupons(client, product_name, asin)
        ethics = await calculate_ethics_score(client, product_name, brand)
        
        api_key = os.getenv("OPENAI_API_KEY")
        context = f"Product: {product_name}\nPrice: {amazon_data.get('price')}\nRating: {amazon_data.get('rating')}/5\nFake Risk: {fake_analysis['risk']}\nGive verdict: BUY/WAIT/AVOID (3 sentences max)"
        try:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "You are a shopping advisor."}, {"role": "user", "content": context}], "max_tokens": 200, "temperature": 0.3})
            ai_verdict = resp.json()["choices"][0]["message"]["content"]
        except:
            ai_verdict = "AI verdict unavailable"
        
        print(format_output(amazon_data, fake_analysis, regret_analysis, confidence, reddit_data, youtube_data, twitter_data, price_pred, alternatives, coupons, ethics, ai_verdict))

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else input("Enter URL: ")))
