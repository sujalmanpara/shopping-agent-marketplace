# summarizer.py — LLM verdict generation and beautiful formatted output
# Phase 1: Structured JSON prompts, temperature 0.0, two-tier output

import json
from typing import Dict
import httpx
from app.core.llm import call_llm
from .constants import LLM_TEMPERATURE, LLM_MAX_TOKENS, MAX_CONTEXT_LENGTH


async def generate_summary(
    api_key: str,
    amazon_data: Dict,
    source_results: Dict,
    fake_analysis: Dict,
    regret_analysis: Dict,
    confidence: Dict,
) -> str:
    """
    Generate final shopping advice using LLM with structured JSON input.
    
    Uses temperature 0.0 for deterministic, factual output.
    """
    # Build structured context for LLM
    context = {
        "product": {
            "title": amazon_data.get("title", "Unknown"),
            "price": amazon_data.get("price_display", amazon_data.get("price", "N/A")),
            "rating": amazon_data.get("rating"),
            "review_count": amazon_data.get("review_count", 0),
        },
        "fake_reviews": {
            "risk": fake_analysis.get("risk", "unknown"),
            "score": fake_analysis.get("score", 0),
            "suspicious_count": fake_analysis.get("suspicious_count", 0),
            "total_analyzed": fake_analysis.get("total_analyzed", 0),
        },
        "regret": {
            "severity": regret_analysis.get("severity", "unknown"),
            "warning": regret_analysis.get("warning"),
        },
        "confidence": {
            "overall": confidence.get("overall", 0),
            "level": confidence.get("level", "LOW"),
            "sources_used": confidence.get("sources_used", 0),
        },
        "sources": {},
    }

    # Add source summaries
    for name, result in source_results.items():
        if result.get("success"):
            data = result.get("data", {})
            if name == "reddit":
                context["sources"]["reddit"] = {
                    "found": data.get("found", 0),
                    "top_subreddits": data.get("subreddits", [])[:3],
                    "engagement": data.get("total_engagement", 0),
                }
            elif name == "youtube":
                context["sources"]["youtube"] = {
                    "found": data.get("found", 0),
                    "total_views": data.get("total_views", 0),
                }
            elif name == "keepa":
                context["sources"]["keepa"] = {
                    "average_price": data.get("average_price"),
                    "lowest_price": data.get("lowest_price"),
                    "highest_price": data.get("highest_price"),
                    "current_vs_average": "above" if (data.get("average_price") and amazon_data.get("price") and amazon_data["price"] > data["average_price"]) else "below",
                }
            elif name == "fakespot":
                context["sources"]["fakespot"] = {
                    "grade": data.get("grade"),
                    "adjusted_rating": data.get("adjusted_rating"),
                }
            elif name == "reviewmeta":
                context["sources"]["reviewmeta"] = {
                    "adjusted_rating": data.get("adjusted_rating"),
                    "original_rating": data.get("original_rating"),
                    "failed_reviews_pct": data.get("failed_reviews_pct"),
                }
            elif name == "wirecutter":
                context["sources"]["wirecutter"] = {
                    "found": data.get("found", False),
                    "is_top_pick": data.get("is_top_pick", False),
                }
            elif name == "rtings":
                context["sources"]["rtings"] = {
                    "found": data.get("found", False),
                    "score": data.get("score"),
                }
            elif name == "trustpilot":
                context["sources"]["trustpilot"] = {
                    "trust_score": data.get("trust_score"),
                    "review_count": data.get("review_count"),
                }

    context_str = json.dumps(context, indent=2, default=str)

    # Truncate if too long
    if len(context_str) > MAX_CONTEXT_LENGTH:
        context_str = context_str[:MAX_CONTEXT_LENGTH] + "\n... (truncated)"

    system_prompt = """You are a brutally honest shopping advisor analyzing product data from multiple sources.
Give a clear verdict: BUY, WAIT, or AVOID.
Be concise (4-6 sentences max). Focus on:
1. Red flags (fake reviews, quality issues)
2. Price assessment (good deal or overpriced?)
3. Community sentiment (what real users say)
4. One actionable tip to save money

Do NOT hedge or be vague. State your verdict clearly in the first sentence."""

    summary = await call_llm(
        api_key,
        system=system_prompt,
        user=f"Analyze this product data and give your verdict:\n\n{context_str}",
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )

    return summary


def format_beautiful_output(
    amazon_data: Dict,
    source_results: Dict,
    fake_analysis: Dict,
    regret_analysis: Dict,
    confidence: Dict,
    price_prediction: Dict,
    coupons: Dict,
    ai_verdict: str,
    summary: Dict,
) -> str:
    """
    Format all data into a beautiful, readable two-tier output.
    
    Tier 1: TL;DR (quick verdict at top)
    Tier 2: Full detailed analysis below
    """
    output = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TIER 1: TL;DR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    output.append("━" * 50)
    output.append("🛒 SHOPPING TRUTH AGENT")
    output.append("━" * 50)

    # Quick product info
    title = amazon_data.get("title", "Unknown Product")
    price_display = amazon_data.get("price_display", amazon_data.get("price", "N/A"))
    rating = amazon_data.get("rating")
    review_count = amazon_data.get("review_count", 0)

    output.append(f"\n📦 {title}")
    output.append(f"💰 {price_display} | ⭐ {rating or 'N/A'}/5 ({review_count:,} reviews)")

    # Quick verdict
    verdict_keyword = "WAIT"
    if ai_verdict:
        upper = ai_verdict.upper()
        if "BUY" in upper and "AVOID" not in upper and "DON'T BUY" not in upper:
            verdict_keyword = "BUY"
            verdict_emoji = "✅"
        elif "AVOID" in upper or "DON'T" in upper or "DONT" in upper:
            verdict_keyword = "AVOID"
            verdict_emoji = "❌"
        else:
            verdict_emoji = "⏳"
    else:
        verdict_emoji = "⏳"

    output.append(f"\n{verdict_emoji} **VERDICT: {verdict_keyword}**")

    # Quick stats line
    conf_level = confidence.get("level", "LOW")
    conf_emoji = "🟢" if conf_level == "HIGH" else "🟡" if conf_level == "MEDIUM" else "🔴"
    risk = fake_analysis.get("risk", "unknown")
    risk_emoji = "🔴" if risk == "high" else "🟡" if risk in ("medium", "limited") else "🟢" if risk == "low" else "⚪"
    sources_used = summary.get("succeeded", 0)
    sources_total = summary.get("total", 10)

    output.append(f"{conf_emoji} Confidence: {conf_level} | {risk_emoji} Fake Risk: {risk.upper()} | 📊 Sources: {sources_used}/{sources_total}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TIER 2: FULL ANALYSIS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── Source Results ──
    output.append("\n" + "─" * 50)
    output.append("📊 DATA SOURCES")
    output.append("─" * 50)

    for name, result in source_results.items():
        if result.get("success"):
            data = result.get("data", {})
            latency = result.get("latency_ms", 0)
            source_label = result.get("source", name)

            if name == "amazon":
                output.append(f"✅ Amazon: {review_count:,} reviews, {rating or 'N/A'}★ [{latency:.0f}ms]")
            elif name == "reddit":
                found = data.get("found", 0)
                engagement = data.get("total_engagement", 0)
                output.append(f"✅ Reddit: {found} posts, {engagement} engagement [{latency:.0f}ms]")
            elif name == "youtube":
                found = data.get("found", 0)
                views = data.get("total_views", 0)
                output.append(f"✅ YouTube: {found} videos, {views:,} total views [{latency:.0f}ms]")
            elif name == "keepa":
                avg = data.get("average_price")
                low = data.get("lowest_price")
                output.append(f"✅ Keepa: Avg ₹{avg:,.0f}, Low ₹{low:,.0f} [{latency:.0f}ms]" if avg and low else f"✅ Keepa: Data available [{latency:.0f}ms]")
            elif name == "google_shopping":
                found = data.get("found", 0)
                output.append(f"✅ Google Shopping: {found} price comparisons [{latency:.0f}ms]")
            elif name == "fakespot":
                grade = data.get("grade", "N/A")
                output.append(f"✅ Fakespot: Grade {grade} [{latency:.0f}ms]")
            elif name == "reviewmeta":
                adj = data.get("adjusted_rating")
                failed = data.get("failed_reviews_pct")
                output.append(f"✅ ReviewMeta: Adjusted {adj}/5" + (f", {failed}% failed" if failed else "") + f" [{latency:.0f}ms]")
            elif name == "wirecutter":
                is_pick = data.get("is_top_pick", False)
                output.append(f"✅ Wirecutter: {'🏆 Top Pick!' if is_pick else 'Found' if data.get('found') else 'Not listed'} [{latency:.0f}ms]")
            elif name == "rtings":
                score = data.get("score")
                output.append(f"✅ RTINGS: {score}/10" if score else f"✅ RTINGS: {'Listed' if data.get('found') else 'Not tested'}" + f" [{latency:.0f}ms]")
            elif name == "trustpilot":
                ts = data.get("trust_score")
                output.append(f"✅ Trustpilot: {ts}/5 TrustScore [{latency:.0f}ms]" if ts else f"✅ Trustpilot: Data available [{latency:.0f}ms]")
        else:
            error = result.get("error", "Unknown error")
            # Shorten API key messages
            if "No " in error and "key" in error.lower():
                output.append(f"⬚ {name.title()}: API key not configured")
            else:
                output.append(f"❌ {name.title()}: {error[:60]}")

    # ── Fake Review Detection ──
    output.append("\n" + "─" * 50)
    output.append("🕵️ FAKE REVIEW ANALYSIS")
    output.append("─" * 50)

    if risk == "insufficient_data":
        output.append(f"⚪ {fake_analysis.get('reason', 'Not enough reviews for analysis')}")
    elif risk == "limited":
        has_suspicious = fake_analysis.get("has_suspicious", False)
        output.append(f"{'🟡' if has_suspicious else '🟢'} Limited data ({fake_analysis.get('total_analyzed', 0)} reviews)")
        if has_suspicious:
            output.append(f"   ⚠️ {fake_analysis.get('suspicious_count', 0)} suspicious reviews detected")
    else:
        output.append(f"{risk_emoji} Risk: {risk.upper()} — {fake_analysis.get('score', 0)}% suspicious")
        output.append(f"   {fake_analysis.get('suspicious_count', 0)}/{fake_analysis.get('total_analyzed', 0)} reviews flagged")
        output.append(f"   Method: {fake_analysis.get('method', 'N/A')} ({fake_analysis.get('model_accuracy', 'N/A')} accuracy)")

    # Show flagged review snippets
    for flagged in fake_analysis.get("flagged_reviews", [])[:2]:
        output.append(f"   📝 \"{flagged['text']}\" (conf: {flagged['confidence']})")

    # ── Regret Detector ──
    if regret_analysis.get("warning"):
        output.append("\n" + "─" * 50)
        output.append("⏰ REGRET DETECTOR")
        output.append("─" * 50)
        output.append(f"⚠️ {regret_analysis['warning']}")
        if regret_analysis.get("early_avg") and regret_analysis.get("recent_avg"):
            output.append(f"   Early avg: {regret_analysis['early_avg']}★ → Recent avg: {regret_analysis['recent_avg']}★")

    # ── Confidence Score ──
    output.append("\n" + "─" * 50)
    output.append("🎯 CONFIDENCE SCORE")
    output.append("─" * 50)
    output.append(f"{conf_emoji} Overall: {confidence.get('overall', 0):.0%} ({conf_level})")
    output.append(f"   📊 Sufficiency: {confidence.get('sufficiency', 0):.0%} | Agreement: {confidence.get('agreement', 0):.0%} | Quality: {confidence.get('quality', 0):.0%}")
    output.append(f"   Sources: {confidence.get('sources_used', 0)}/{confidence.get('sources_total', 0)} responded")

    # ── Price Prediction ──
    if price_prediction and not price_prediction.get("error"):
        output.append("\n" + "─" * 50)
        output.append("📈 PRICE PREDICTION (ARIMA)")
        output.append("─" * 50)
        pred_lowest = price_prediction.get("predicted_lowest")
        pred_avg = price_prediction.get("predicted_average")
        drop_prob = price_prediction.get("drop_probability", 0)
        savings = price_prediction.get("expected_savings", 0)
        best_day = price_prediction.get("best_day_to_buy")

        if pred_lowest:
            output.append(f"📉 Predicted lowest: ₹{pred_lowest:,.0f} (avg ₹{pred_avg:,.0f})")
        output.append(f"🎯 Drop probability: {drop_prob:.0%}")
        if savings > 0:
            output.append(f"💰 Expected savings: ₹{savings:,.0f} ({price_prediction.get('savings_percentage', 0):.1f}%)")
        if best_day:
            output.append(f"📅 Best day to buy: ~{best_day} days from now")
        output.append(f"🔬 Model confidence: {price_prediction.get('confidence', 0):.0%}")

    # ── Google Shopping Price Comparison ──
    google_result = source_results.get("google_shopping", {})
    if google_result.get("success"):
        gs_data = google_result["data"]
        items = gs_data.get("items", [])
        if items:
            output.append("\n" + "─" * 50)
            output.append("🔍 PRICE COMPARISON (Google Shopping)")
            output.append("─" * 50)
            for item in items[:3]:
                output.append(f"   • {item.get('source', 'Unknown')}: {item.get('price', 'N/A')} — {item.get('title', '')[:50]}")
            if gs_data.get("lowest_price"):
                output.append(f"   💡 Lowest: {gs_data['lowest_price']} at {gs_data.get('lowest_source', 'Unknown')}")

    # ── Coupon Sniper ──
    output.append("\n" + "─" * 50)
    output.append("🎯 COUPON SNIPER")
    output.append("─" * 50)

    if coupons and coupons.get("found", 0) > 0:
        for coupon in coupons.get("coupons", []):
            conf = coupon.get("confidence", 0)
            badge = "✅" if conf >= 0.8 else "⚠️"
            code = coupon.get("code", "")
            if code == "CLIP_COUPON":
                output.append(f"  {badge} 🏷️ Clip Coupon: {coupon['discount']}")
            elif code == "SUBSCRIBE_SAVE":
                output.append(f"  {badge} 📦 Subscribe & Save: {coupon['discount']}")
            elif code != "NO_CODE":
                output.append(f"  {badge} 💰 {code}: {coupon['discount']}")
            else:
                output.append(f"  {badge} 🏷️ Deal: {coupon['discount']}")
    else:
        output.append("  ❌ No verified coupon codes available")
        output.append("  ℹ️  We show nothing rather than unverified codes")

    # Cashback
    if coupons and coupons.get("cashback"):
        output.append("")
        output.append("  💸 CASHBACK:")
        for cb in coupons["cashback"]:
            note = f" — {cb['note']}" if cb.get("note") else ""
            output.append(f"    • {cb['platform']}: {cb['rate']} cashback{note}")

    # Credit Cards
    if coupons and coupons.get("credit_cards"):
        output.append("")
        output.append("  💳 BEST CARDS:")
        for card in coupons["credit_cards"]:
            special = f" {card['special']}" if card.get("special") else ""
            savings = f" (save ~₹{card['savings_estimate']:.0f})" if card.get("savings_estimate") else ""
            output.append(f"    • {card['card']}: {card['benefit']}{savings}{special}")
            output.append(f"      💡 {card['shopping_tip']}")

    # Best Combo
    if coupons and coupons.get("best_combo"):
        combo = coupons["best_combo"]
        output.append("")
        output.append("  🏆 BEST COMBO:")
        output.append(f"    {combo['strategy']}")
        output.append(f"    💵 Save ₹{combo['total_savings']:.0f} ({combo['savings_percentage']}% off!)")
        output.append(f"    🏷️ Final: ₹{combo['final_price']:.0f} (was ₹{combo['original_price']:.0f})")

    # Advice
    if coupons and coupons.get("advice"):
        output.append(f"\n  📌 {coupons['advice']}")

    # ── AI Verdict (full text) ──
    output.append("\n" + "─" * 50)
    output.append("🤖 AI VERDICT")
    output.append("─" * 50)
    output.append(f"\n{verdict_emoji} **{verdict_keyword}**")
    if ai_verdict:
        output.append(f"\n{ai_verdict}")

    # ── Footer ──
    output.append("\n" + "━" * 50)
    failed_sources = summary.get("failed_sources", [])
    if failed_sources:
        missing_note = f" | Missing: {', '.join(failed_sources[:3])}" + ("..." if len(failed_sources) > 3 else "")
    else:
        missing_note = ""
    output.append(f"✅ {sources_used}/{sources_total} sources analyzed{missing_note}")
    output.append("Powered by Shopping Truth Agent v2.0")
    output.append("━" * 50)

    return "\n".join(output)
