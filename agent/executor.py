# executor.py — Shopping Truth Agent executor (standalone, no framework deps)
# Phase 1: Clean API layer, graceful degradation, structured output
# Phase 2: Alternatives, enhanced fake reviews, price prediction with context

import asyncio
from typing import AsyncGenerator, Dict


def sse_event(event_type: str, data: str) -> dict:
    """Standalone SSE event helper — no framework dependency."""
    return {"event": event_type, "data": data}


def sse_error(message: str) -> dict:
    """Standalone SSE error helper."""
    return {"event": "error", "data": message}

from .api_layer import (
    extract_asin, detect_platform,
    fetch_amazon_product, fetch_all_sources, fetch_alternatives
)
from .analyzers import (
    analyze_fake_reviews, analyze_regret_pattern, calculate_confidence,
    get_fake_review_summary, analyze_review_timeline, analyze_price_benchmark,
    analyze_review_quality, analyze_buy_timing, generate_price_alerts,
    analyze_star_distribution
)
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
    Shopping Truth Agent — Analyze products across 10+ data sources.
    
    Flow:
    1. Parse input → extract ASIN, detect platform
    2. Fetch Amazon product first (need title/price for other searches)
    3. Fetch ALL other sources + alternatives in parallel
    4. Run ML analysis (fake reviews with cross-verification, regret, confidence)
    5. Run price prediction with context (ARIMA + sale calendar)
    6. Run coupon/savings check
    7. Generate LLM verdict (with alternatives + prediction data)
    8. Format two-tier output (TL;DR + full analysis)
    """
    # Auto-detect LLM provider from available keys
    llm_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY", "OPENROUTER_API_KEY"]
    api_key = None
    for k in llm_keys:
        if keys.get(k):
            api_key = keys[k]
            break
    if not api_key:
        yield sse_error("No LLM API key found. Set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROK_API_KEY, or OPENROUTER_API_KEY")
        return

    # ── Step 1: Parse input ──
    platform = detect_platform(prompt)
    asin = extract_asin(prompt)
    if not asin:
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
        # Graceful degradation: even if Amazon fails, try other sources with ASIN as query
        product_name = f"Amazon product {asin}"
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

    # ── Step 3: Fetch ALL other sources + alternatives in parallel ──
    yield sse_event("status", "🌐 Querying Reddit, YouTube, Keepa, ReviewMeta, Wirecutter, RTINGS, Trustpilot + finding alternatives...")

    # Detect rough category from product name for alternative search
    category = _detect_category(product_name)

    all_results_task = fetch_all_sources(asin, product_name, brand, country, keys)
    alternatives_task = fetch_alternatives(product_name, price_numeric, category, country, keys)

    all_results, alternatives_result = await asyncio.gather(
        all_results_task, alternatives_task, return_exceptions=True
    )

    # Handle exceptions
    if isinstance(all_results, Exception):
        all_results = {"sources": {}, "summary": {"total": 10, "succeeded": 0, "failed": 10, "success_rate": 0, "total_latency_ms": 0, "failed_sources": []}}
    if isinstance(alternatives_result, Exception):
        alternatives_result = {"success": False, "data": {}, "error": str(alternatives_result), "source": "alternatives"}

    source_results = all_results["sources"]
    summary = all_results["summary"]

    # Inject the Amazon result we already have
    source_results["amazon"] = amazon_result

    # Extract alternatives data
    alternatives_data = {}
    if isinstance(alternatives_result, dict) and alternatives_result.get("success"):
        alternatives_data = alternatives_result.get("data", {})
    elif isinstance(alternatives_result, dict) and alternatives_result.get("data"):
        alternatives_data = alternatives_result["data"]

    yield sse_event("status", f"✅ {summary['succeeded']}/{summary['total']} sources responded")

    # ── Step 3b: Fetch bulk reviews (Rainforest → ScrapingDog fallback) ──
    reviews = amazon_data.get("reviews", [])
    rainforest_key = (keys or {}).get("RAINFOREST_API_KEY")
    scrapingdog_key = (keys or {}).get("SCRAPINGDOG_API_KEY")
    bulk_reviews = []

    if len(reviews) < 20:
        # Tier 1: Rainforest Reviews API (best quality, paginated)
        if rainforest_key and not bulk_reviews:
            yield sse_event("status", "📝 Fetching bulk reviews via Rainforest API...")
            try:
                from .api_layer import _fetch_amazon_reviews_rainforest
                bulk_reviews = await _fetch_amazon_reviews_rainforest(
                    asin, rainforest_key, country, max_pages=10
                )
            except Exception as e:
                yield sse_event("status", f"⚠️ Rainforest reviews failed: {str(e)[:80]}")

        # Tier 2: ScrapingDog Reviews API (fallback)
        if scrapingdog_key and len(bulk_reviews) < 10:
            yield sse_event("status", "📝 Fetching bulk reviews via ScrapingDog...")
            try:
                from .api_layer import _fetch_amazon_reviews_scrapingdog
                sd_reviews = await _fetch_amazon_reviews_scrapingdog(
                    asin, scrapingdog_key, country, max_pages=10
                )
                bulk_reviews.extend(sd_reviews)
            except Exception as e:
                yield sse_event("status", f"⚠️ ScrapingDog reviews failed: {str(e)[:80]}")

        # Merge bulk reviews with existing (dedupe by body[:50])
        if bulk_reviews:
            existing_bodies = {r.get("body", "")[:50] for r in reviews}
            for br in bulk_reviews:
                if br.get("body", "")[:50] not in existing_bodies:
                    reviews.append(br)
                    existing_bodies.add(br.get("body", "")[:50])
            amazon_data["reviews"] = reviews
            yield sse_event("status", f"📝 Got {len(reviews)} total reviews for analysis")

    # ── Step 3c: Fetch Amazon rating widget (FREE, no auth) ──
    try:
        from .api_layer import _fetch_amazon_rating_widget
        rating_widget = await _fetch_amazon_rating_widget(asin, country)
        if rating_widget:
            amazon_data["rating_widget"] = rating_widget
            # Enrich amazon_data with accurate rating info from widget
            if rating_widget.get("average_rating"):
                amazon_data["rating"] = rating_widget["average_rating"]
            if rating_widget.get("total_ratings"):
                amazon_data["review_count"] = rating_widget["total_ratings"]
    except Exception:
        rating_widget = None

    # ── Step 4: ML Analysis with cross-verification ──
    yield sse_event("status", "🕵️ Running fake review detection & cross-verification...")
    fake_analysis = analyze_fake_reviews(reviews)
    regret_analysis = analyze_regret_pattern(reviews)
    confidence = calculate_confidence(all_results)

    # Enhanced fake review summary with ReviewMeta cross-verification
    fake_review_summary = get_fake_review_summary(reviews, fake_analysis, all_results)

    # ── Step 4b: New analyses (zero API cost) ──
    yield sse_event("status", "📊 Running timeline analysis, price benchmarking, review quality scoring...")

    # Review Timeline Analyzer (detect review bombing)
    timeline_analysis = analyze_review_timeline(reviews)

    # Category Price Benchmark (compare against Google Shopping results)
    google_shopping_result = source_results.get("google_shopping", {})
    price_benchmark = analyze_price_benchmark(price_numeric, alternatives_result if isinstance(alternatives_result, dict) else {}, google_shopping_result)

    # Review Quality Score
    review_quality = analyze_review_quality(reviews)

    # Star Distribution Analysis (from free Amazon widget)
    star_dist_analysis = {}
    if amazon_data.get("rating_widget", {}).get("star_distribution"):
        star_dist_analysis = analyze_star_distribution(
            amazon_data["rating_widget"]["star_distribution"]
        )

    # ── Step 5: Price Prediction with context ──
    price_prediction = {}
    keepa_result = source_results.get("keepa", {})
    if keepa_result.get("success"):
        yield sse_event("status", "📈 Running ARIMA price prediction with sale calendar...")
        try:
            from .price_predictor_arima import ARIMAPricePredictor
            predictor = ARIMAPricePredictor(order=(5, 1, 0))
            keepa_data = keepa_result["data"]

            # Use predict_with_context for richer output
            price_prediction = predictor.predict_with_context(
                keepa_data=keepa_data,
                current_price=price_numeric,
                country=country
            )
        except Exception as e:
            price_prediction = {"error": str(e), "confidence": 0}
    else:
        # No Keepa data — still provide sale calendar info
        try:
            from .price_predictor_arima import _get_upcoming_sales
            upcoming_sales = _get_upcoming_sales(country)
            if upcoming_sales:
                price_prediction = {
                    "upcoming_sales": upcoming_sales,
                    "method": "sale_calendar_only",
                    "explanation": "No price history available. Showing upcoming sales for planning.",
                    "confidence": 0.1,
                }
        except Exception:
            pass

    # ── Step 5b: Buy Timing + Price Alerts ──
    buy_timing = analyze_buy_timing(price_numeric, price_prediction, country)
    # Only show price alerts when we have real price history (Keepa)
    has_keepa = keys.get("KEEPA_API_KEY", "") != ""
    price_alerts = generate_price_alerts(asin, price_numeric, country) if has_keepa else None

    # ── Step 6: Coupon & Savings ──
    yield sse_event("status", "💰 Checking coupons, cashback & credit card benefits...")
    try:
        coupons = await find_coupons(product_name, asin, price_numeric, country)
    except Exception:
        coupons = {"found": 0, "coupons": [], "cashback": [], "credit_cards": []}

    # ── Step 7: Generate LLM Verdict (with enhanced data) ──
    yield sse_event("status", "🤖 Generating AI verdict...")

    ai_verdict = await generate_summary(
        api_key=api_key,
        amazon_data=amazon_data,
        source_results=source_results,
        fake_analysis=fake_analysis,
        regret_analysis=regret_analysis,
        confidence=confidence,
        alternatives=alternatives_data,
        price_prediction=price_prediction,
        fake_review_summary=fake_review_summary,
        keys=keys,
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
        alternatives=alternatives_data,
        fake_review_summary=fake_review_summary,
        timeline_analysis=timeline_analysis,
        price_benchmark=price_benchmark,
        review_quality=review_quality,
        buy_timing=buy_timing,
        price_alerts=price_alerts,
        star_distribution=star_dist_analysis,
    )

    yield sse_event("result", beautiful_output)


def _detect_category(product_name: str) -> str:
    """Detect product category from name for better alternative search."""
    name_lower = product_name.lower()

    category_keywords = {
        "earbuds": ["earbuds", "earbud", "tws", "wireless earphone"],
        "headphones": ["headphone", "headset", "over-ear", "on-ear"],
        "speaker": ["speaker", "soundbar", "bluetooth speaker", "portable speaker"],
        "phone": ["phone", "smartphone", "mobile", "iphone", "galaxy", "pixel", "oneplus"],
        "laptop": ["laptop", "notebook", "macbook", "chromebook", "thinkpad"],
        "tablet": ["tablet", "ipad", "tab"],
        "tv": ["television", " tv ", "smart tv", "oled", "qled"],
        "monitor": ["monitor", "display"],
        "keyboard": ["keyboard", "mechanical keyboard"],
        "mouse": ["mouse", "mice", "trackpad"],
        "camera": ["camera", "dslr", "mirrorless", "gopro", "action cam"],
        "watch": ["watch", "smartwatch", "fitness tracker", "band"],
        "charger": ["charger", "power bank", "adapter"],
        "storage": ["ssd", "hard drive", "hdd", "pen drive", "memory card"],
    }

    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in name_lower:
                return category

    return ""
