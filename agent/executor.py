# executor.py — Shopping Truth Agent executor with API-first architecture
# Phase 1: Clean API layer, graceful degradation, structured output

import asyncio
from typing import AsyncGenerator, Dict
from app.core.sse import sse_event, sse_error
from app.core.config import settings

from .api_layer import (
    extract_asin, extract_flipkart_id, detect_platform,
    fetch_amazon_product, fetch_all_sources
)
from .analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence
from .summarizer import generate_summary, format_beautiful_output
from .coupon_sniper import find_coupons
from .constants import LLM_TEMPERATURE, LLM_MAX_TOKENS


async def execute(
    prompt: str,
    keys: dict,
    language: str = None,
    options: dict = None
) -> AsyncGenerator[dict, None]:
    """
    Shopping Truth Agent — Analyze products across 10 data sources.
    
    Flow:
    1. Parse input → extract ASIN, detect platform
    2. Fetch Amazon product first (need title/price for other searches)
    3. Fetch ALL other sources in parallel
    4. Run ML analysis (fake reviews, regret, confidence)
    5. Run price prediction (if Keepa data available)
    6. Run coupon/savings check
    7. Generate LLM verdict
    8. Format two-tier output (TL;DR + full analysis)
    """
    api_key = keys.get("OPENAI_API_KEY")
    if not api_key:
        yield sse_error("Missing OPENAI_API_KEY")
        return

    # ── Step 1: Parse input ──
    platform = detect_platform(prompt)
    asin = extract_asin(prompt)
    flipkart_id = extract_flipkart_id(prompt)

    if not asin:
        if flipkart_id:
            yield sse_error("Flipkart support coming soon. Please provide an Amazon product URL for now.")
            return
        yield sse_error("Please provide a valid Amazon product URL or ASIN")
        return

    # Determine country from platform
    country = "IN" if platform == "amazon_in" or "amazon.in" in prompt.lower() else "IN"  # Default to India

    yield sse_event("status", "🔍 Analyzing product across 10+ data sources...")

    # ── Step 2: Fetch Amazon product first (need title for other searches) ──
    yield sse_event("status", "📦 Fetching product details from Amazon...")
    amazon_result = await fetch_amazon_product(asin, country, keys)

    # Extract product info for other searches
    if amazon_result["success"]:
        amazon_data = amazon_result["data"]
        product_name = amazon_data.get("title", "")
        brand = product_name.split()[0] if product_name else ""
        price_numeric = amazon_data.get("price")
    else:
        # Graceful degradation: even if Amazon fails, try other sources
        product_name = prompt.replace("https://", "").replace("http://", "").replace("amazon.in", "").replace("amazon.com", "")
        brand = ""
        price_numeric = None
        amazon_data = {
            "title": "Product (Amazon unavailable)",
            "price": None,
            "price_display": "N/A",
            "rating": None,
            "review_count": 0,
            "reviews": [],
            "asin": asin,
            "url": f"https://www.amazon.in/dp/{asin}",
            "source_method": "failed",
            "country": country,
        }

    # ── Step 3: Fetch ALL other sources in parallel ──
    yield sse_event("status", "🌐 Querying Reddit, YouTube, Keepa, Fakespot, ReviewMeta, Wirecutter, RTINGS, Trustpilot...")
    all_results = await fetch_all_sources(asin, product_name, brand, country, keys)
    source_results = all_results["sources"]
    summary = all_results["summary"]

    # Inject the Amazon result we already have
    source_results["amazon"] = amazon_result

    yield sse_event("status", f"✅ {summary['succeeded']}/{summary['total']} sources responded")

    # ── Step 4: ML Analysis ──
    yield sse_event("status", "🕵️ Running fake review detection & pattern analysis...")

    # Use reviews from Amazon data for fake review analysis
    reviews = amazon_data.get("reviews", [])
    fake_analysis = analyze_fake_reviews(reviews)
    regret_analysis = analyze_regret_pattern(reviews)
    confidence = calculate_confidence(all_results)

    # ── Step 5: Price Prediction (if Keepa data available) ──
    price_prediction = {}
    keepa_result = source_results.get("keepa", {})
    if keepa_result.get("success"):
        yield sse_event("status", "📈 Running ARIMA price prediction...")
        try:
            from .price_predictor_arima import ARIMAPricePredictor
            predictor = ARIMAPricePredictor(order=(5, 1, 0))
            keepa_data = keepa_result["data"]
            # Format for ARIMA predictor
            price_data_for_arima = {
                "success": True,
                "prices": keepa_data.get("prices", []),
                "data_points": keepa_data.get("data_points", 0),
            }
            price_prediction = predictor.predict_next_30_days(price_data_for_arima)
        except Exception as e:
            price_prediction = {"error": str(e), "confidence": 0}

    # ── Step 6: Coupon & Savings ──
    yield sse_event("status", "💰 Checking coupons, cashback & credit card benefits...")
    try:
        coupons = await find_coupons(product_name, asin, price_numeric, country)
    except Exception:
        coupons = {"found": 0, "coupons": [], "cashback": [], "credit_cards": []}

    # ── Step 7: Generate LLM Verdict ──
    yield sse_event("status", "🤖 Generating AI verdict...")

    ai_verdict = await generate_summary(
        api_key=api_key,
        amazon_data=amazon_data,
        source_results=source_results,
        fake_analysis=fake_analysis,
        regret_analysis=regret_analysis,
        confidence=confidence,
    )

    # ── Step 8: Format Output ──
    beautiful_output = format_beautiful_output(
        amazon_data=amazon_data,
        source_results=source_results,
        fake_analysis=fake_analysis,
        regret_analysis=regret_analysis,
        confidence=confidence,
        price_prediction=price_prediction,
        coupons=coupons,
        ai_verdict=ai_verdict,
        summary=summary,
    )

    yield sse_event("result", beautiful_output)
