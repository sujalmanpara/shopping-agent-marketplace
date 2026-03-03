# summarizer.py — Beautiful formatted output with ALL 10 features

from typing import Dict
import httpx
from app.core.llm import call_llm
from .constants import DEFAULT_TEMPERATURE, MAX_CONTEXT_LENGTH


async def generate_summary(
    client: httpx.AsyncClient,
    api_key: str,
    amazon_data: Dict,
    reddit_data: Dict,
    fake_review_analysis: Dict,
    regret_analysis: Dict,
    confidence_score: int
) -> str:
    """Generate final shopping advice summary using LLM."""
    
    reviews_text = "\n".join([f"- {r['body'][:200]}" for r in amazon_data.get("reviews", [])[:5]])
    reddit_titles = "\n".join([f"- {c['title']}" for c in reddit_data.get("comments", [])[:5]])
    
    context = f"""
Product: {amazon_data.get('title', 'Unknown')}
Price: {amazon_data.get('price', 'N/A')}
Amazon Rating: {amazon_data.get('rating', 0)}★ ({amazon_data.get('review_count', 0)} reviews)

Reddit Mentions: {reddit_data.get('found', 0)}
{reddit_titles[:500] if reddit_titles else "None found"}

Fake Review Risk: {fake_review_analysis['risk']} ({fake_review_analysis['score']}% suspicious)
Regret Warning: {regret_analysis.get('warning', 'None')}

Sample Reviews:
{reviews_text[:MAX_CONTEXT_LENGTH]}
"""
    
    system_prompt = """You are a brutally honest shopping advisor. 
Analyze the product data and give a clear verdict: BUY, WAIT, or AVOID.
Be concise (3-4 sentences). Focus on red flags and money-saving tips."""
    
    summary = await call_llm(
        client,
        api_key,
        system=system_prompt,
        user=f"Analyze this product:\n{context}\n\nVerdict:",
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=300
    )
    
    return summary


def format_beautiful_output(
    amazon_data: Dict,
    fake_analysis: Dict,
    regret_analysis: Dict,
    confidence: int,
    reddit_data: Dict,
    youtube_data: Dict,
    twitter_data: Dict,
    price_prediction: Dict,
    alternatives: Dict,
    coupons: Dict,
    ethics: Dict,
    ai_verdict: str
) -> str:
    """
    Format all 10 features into a beautiful, readable output
    """
    
    output = []
    
    # Header
    output.append("━" * 60)
    output.append("🛒 SHOPPING TRUTH AGENT - COMPLETE ANALYSIS")
    output.append("━" * 60)
    
    # Product Info
    output.append(f"\n📦 **Product:** {amazon_data.get('title', 'Unknown')}")
    output.append(f"💰 **Price:** {amazon_data.get('price', 'N/A')}")
    output.append(f"⭐ **Rating:** {amazon_data.get('rating', 0)}/5 ({amazon_data.get('review_count', 0):,} reviews)")
    
    # Feature 1-2: Multi-Platform Analysis
    output.append("\n" + "─" * 60)
    output.append("📊 MULTI-PLATFORM ANALYSIS (Features 1-2)")
    output.append("─" * 60)
    output.append(f"✅ Amazon: {amazon_data.get('review_count', 0):,} reviews")
    output.append(f"✅ Reddit: {reddit_data.get('found', 0)} mentions")
    output.append(f"✅ YouTube: {youtube_data.get('found', 0)} video reviews")
    output.append(f"✅ Twitter: {twitter_data.get('found', 0)} tweets")
    
    # Feature 3: Fake Review Detection
    output.append("\n" + "─" * 60)
    output.append("🕵️ FAKE REVIEW DETECTION (Feature 3)")
    output.append("─" * 60)
    risk_emoji = "🔴" if fake_analysis['risk'] == "high" else "🟡" if fake_analysis['risk'] == "medium" else "🟢"
    output.append(f"{risk_emoji} **Risk Level:** {fake_analysis['risk'].upper()}")
    output.append(f"📊 **Fake Score:** {fake_analysis['score']}% suspicious")
    output.append(f"⚠️  **Suspicious Reviews:** {fake_analysis.get('suspicious_count', 0)}/{fake_analysis.get('total_analyzed', 0)}")
    
    # Feature 4: Regret Detector
    output.append("\n" + "─" * 60)
    output.append("⏰ REGRET DETECTOR (Feature 4)")
    output.append("─" * 60)
    if regret_analysis.get('warning'):
        output.append(f"⚠️  **Warning:** {regret_analysis['warning']}")
        output.append(f"📉 **Severity:** {regret_analysis['severity'].upper()}")
    else:
        output.append("✅ **No regret detected** - Ratings stable over time")
    
    # Feature 5: Confidence Score
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
    
    # Feature 7: Price Prediction
    if price_prediction and price_prediction.get('prediction'):
        output.append("\n" + "─" * 60)
        output.append("💰 PRICE DROP PREDICTION (Feature 7)")
        output.append("─" * 60)
        pred = price_prediction['prediction']
        output.append(f"🎯 **Event:** {pred['event']}")
        output.append(f"📉 **Predicted Drop:** {pred['predicted_drop']}")
        output.append(f"💡 **Advice:** {pred['advice']}")
    
    # Feature 8: Alternative Products
    if alternatives and alternatives.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🔄 BETTER ALTERNATIVES (Feature 8)")
        output.append("─" * 60)
        output.append(f"✅ **Found:** {alternatives['found']} cheaper/better options")
        for i, alt in enumerate(alternatives.get('alternatives', [])[:3], 1):
            output.append(f"\n{i}. {alt['title'][:60]}...")
            output.append(f"   💰 {alt['price']} | ⭐ {alt['rating']}/5 | 💵 Save {alt['savings']}")
    
    # Feature 9: Coupons
    if coupons and coupons.get('found', 0) > 0:
        output.append("\n" + "─" * 60)
        output.append("🎟️  COUPON CODES (Feature 9)")
        output.append("─" * 60)
        for coupon in coupons.get('coupons', []):
            output.append(f"💰 **{coupon['code']}:** {coupon['discount']}")
    
    # Feature 10: Ethics & Carbon
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
    
    # Feature 6: AI Verdict
    output.append("\n" + "─" * 60)
    output.append("🤖 AI VERDICT (Feature 6)")
    output.append("─" * 60)
    
    # Extract verdict keyword
    verdict_keyword = "WAIT"
    if "BUY" in ai_verdict.upper() and "AVOID" not in ai_verdict.upper():
        verdict_keyword = "BUY"
        verdict_emoji = "✅"
    elif "AVOID" in ai_verdict.upper():
        verdict_keyword = "AVOID"
        verdict_emoji = "❌"
    else:
        verdict_emoji = "⏳"
    
    output.append(f"\n{verdict_emoji} **{verdict_keyword}**")
    output.append(f"\n{ai_verdict}")
    
    # Footer
    output.append("\n" + "━" * 60)
    output.append("✅ All 10 Features Analyzed | Powered by Shopping Truth Agent")
    output.append("━" * 60)
    
    return "\n".join(output)
