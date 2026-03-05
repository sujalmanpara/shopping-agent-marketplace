#!/usr/bin/env python3
"""
Final complete test with beautiful output
Testing: Garnier Men Face Wash
"""

import asyncio
import os
import sys
sys.path.insert(0, 'agent')

import httpx
from agent.scrapers import (
    extract_asin, scrape_amazon, scrape_reddit, scrape_youtube, scrape_twitter,
    scrape_price_history, find_alternatives, find_coupons, calculate_ethics_score
)
from agent.analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence

# Standalone formatter (since we can't import from app.core)
def format_beautiful_output(
    amazon_data, fake_analysis, regret_analysis, confidence,
    reddit_data, youtube_data, twitter_data,
    price_prediction, alternatives, coupons, ethics, ai_verdict
):
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
    output.append(f"⚠️  **Suspicious Reviews:** {fake_analysis.get('suspicious_count', 0)}/{fake_analysis.get('total_analyzed', 0)}")
    
    output.append("\n" + "─" * 60)
    output.append("⏰ REGRET DETECTOR (Feature 4)")
    output.append("─" * 60)
    if regret_analysis.get('warning'):
        output.append(f"⚠️  **Warning:** {regret_analysis['warning']}")
        output.append(f"📉 **Severity:** {regret_analysis['severity'].upper()}")
    else:
        output.append("✅ **No regret detected** - Ratings stable over time")
    
    output.append("\n" + "─" * 60)
    output.append("🎯 CONFIDENCE SCORE (Feature 5)")
    output.append("─" * 60)
    conf_emoji = "🟢" if confidence >= 70 else "🟡" if confidence >= 50 else "🔴"
    output.append(f"{conf_emoji} **Confidence:** {confidence}%")
    sources_count = sum([
        1 if amazon_data.get('rating', 0) > 0 else 0,
        1 if reddit_data.get('found', 0) > 0 else 0,
        1 if youtube_data.get('found', 0) > 0 else 0,
        1 if twitter_data.get('found', 0) > 0 else 0
    ])
    output.append(f"📊 **Sources Verified:** {sources_count}/4")
    
    if price_prediction and price_prediction.get('prediction'):
        output.append("\n" + "─" * 60)
        output.append("💰 PRICE DROP PREDICTION (Feature 7)")
        output.append("─" * 60)
        pred = price_prediction['prediction']
        output.append(f"🎯 **Event:** {pred['event']}")
        output.append(f"📉 **Predicted Drop:** {pred['predicted_drop']}")
        output.append(f"💡 **Advice:** {pred['advice']}")
    
    if alternatives and alternatives.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🔄 BETTER ALTERNATIVES (Feature 8)")
        output.append("─" * 60)
        output.append(f"✅ **Found:** {alternatives['found']} cheaper/better options\n")
        for i, alt in enumerate(alternatives.get('alternatives', [])[:3], 1):
            output.append(f"{i}. {alt['title'][:60]}...")
            output.append(f"   💰 {alt['price']} | ⭐ {alt['rating']}/5 | 💵 Save {alt['savings']}\n")
    
    if coupons and coupons.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🎟️  COUPON CODES (Feature 9)")
        output.append("─" * 60)
        for coupon in coupons.get('coupons', []):
            output.append(f"💰 **{coupon['code']}:** {coupon['discount']}")
    
    if ethics and ethics.get('carbon_footprint'):
        output.append("\n" + "─" * 60)
        output.append("🌍 CARBON & ETHICS SCORE (Feature 10)")
        output.append("─" * 60)
        carbon = ethics['carbon_footprint']
        output.append(f"🌍 **Carbon Footprint:** {carbon['co2_kg']} kg CO2")
        output.append(f"♻️  **Recyclable:** {carbon['recyclable']}")
        
        if ethics.get('ethics'):
            eth = ethics['ethics']
            grade_emoji = "🟢" if eth['grade'] in ["A", "A+", "B+"] else "🟡" if eth['grade'] in ["B", "B-", "C"] else "🔴"
            output.append(f"{grade_emoji} **Ethics Grade:** {eth['grade']}")
            output.append(f"👷 **Labor:** {eth['labor_practices']}")
            output.append(f"🌱 **Sustainability:** {eth['sustainability']}")
    
    output.append("\n" + "─" * 60)
    output.append("🤖 AI VERDICT (Feature 6)")
    output.append("─" * 60)
    
    if "BUY" in ai_verdict.upper() and "AVOID" not in ai_verdict.upper():
        verdict_emoji = "✅"
        verdict = "BUY"
    elif "AVOID" in ai_verdict.upper():
        verdict_emoji = "❌"
        verdict = "AVOID"
    else:
        verdict_emoji = "⏳"
        verdict = "WAIT"
    
    output.append(f"\n{verdict_emoji} **{verdict}**")
    output.append(f"\n{ai_verdict}")
    
    output.append("\n" + "━" * 60)
    output.append("✅ All 10 Features Analyzed | Shopping Truth Agent")
    output.append("━" * 60)
    
    return "\n".join(output)


async def test_complete_agent(asin):
    """Complete test with all 10 features"""
    
    print("\n🔄 Starting complete agent test...")
    print(f"🔗 ASIN: {asin}\n")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Scrape Amazon
        print("⏳ [1/10] Scraping Amazon...")
        amazon_data = await scrape_amazon(client, asin)
        
        if "error" in amazon_data:
            print(f"❌ Error: {amazon_data['error']}")
            return
        
        product_name = amazon_data.get('title', '')
        brand = product_name.split()[0] if product_name else ''
        
        print(f"✅ Product: {product_name[:60]}...")
        
        # Step 2: Multi-platform scraping
        print("⏳ [2/10] Checking Reddit...")
        reddit_data = await scrape_reddit(client, product_name)
        
        print("⏳ [3/10] Checking YouTube...")
        youtube_data = await scrape_youtube(client, product_name)
        
        print("⏳ [4/10] Checking Twitter...")
        twitter_data = await scrape_twitter(client, product_name)
        
        # Step 3: Analysis
        print("⏳ [5/10] Analyzing fake reviews...")
        fake_analysis = analyze_fake_reviews(amazon_data.get('reviews', []))
        
        print("⏳ [6/10] Detecting regret patterns...")
        regret_analysis = analyze_regret_pattern(amazon_data.get('reviews', []))
        
        print("⏳ [7/10] Calculating confidence...")
        confidence = calculate_confidence(amazon_data, reddit_data, youtube_data, twitter_data)
        
        # Step 4: Advanced features
        print("⏳ [8/10] Predicting price drops...")
        price_pred = await scrape_price_history(client, asin)
        
        print("⏳ [9/10] Finding alternatives...")
        alternatives = await find_alternatives(client, product_name, amazon_data.get('price', ''))
        
        print("⏳ [10/10] Discovering coupons...")
        coupons = await find_coupons(client, product_name, asin)
        
        print("⏳ Calculating ethics score...")
        ethics = await calculate_ethics_score(client, product_name, brand)
        
        # Step 5: Generate AI verdict
        print("⏳ Generating AI verdict with OpenAI...\n")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            ai_verdict = "API key not set - skipping AI verdict"
        else:
            context = f"""
Product: {product_name}
Price: {amazon_data.get('price')}
Rating: {amazon_data.get('rating')}/5 ({amazon_data.get('review_count', 0):,} reviews)
Fake Review Risk: {fake_analysis['risk']} ({fake_analysis['score']}%)
Regret: {regret_analysis.get('warning', 'None')}
Confidence: {confidence}%

Analyze and give verdict: BUY, WAIT, or AVOID. 3 sentences max.
"""
            
            try:
                llm_resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a brutally honest shopping advisor."},
                            {"role": "user", "content": context}
                        ],
                        "max_tokens": 250,
                        "temperature": 0.3
                    }
                )
                result = llm_resp.json()
                ai_verdict = result["choices"][0]["message"]["content"]
            except Exception as e:
                ai_verdict = f"AI verdict generation failed: {str(e)}"
        
        # Step 6: Format beautiful output
        print("✨ Generating beautiful output...\n")
        print("=" * 70)
        
        beautiful_output = format_beautiful_output(
            amazon_data, fake_analysis, regret_analysis, confidence,
            reddit_data, youtube_data, twitter_data,
            price_pred, alternatives, coupons, ethics, ai_verdict
        )
        
        print(beautiful_output)
        print("\n" + "=" * 70)
        print("✅ TEST COMPLETE!")


if __name__ == "__main__":
    # Garnier face wash ASIN
    asyncio.run(test_complete_agent("B00V4L6JC2"))
