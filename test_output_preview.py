#!/usr/bin/env python3
"""
Output Preview — Generate realistic output using mock data.
Shows EXACTLY what users will see when all APIs are connected.
No API keys needed — uses realistic simulated data.
"""

import sys
sys.path.insert(0, '.')

from agent.analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence, get_fake_review_summary
from agent.coupon_sniper import find_coupons, get_card_recommendations
from agent.summarizer import format_beautiful_output
import asyncio


def build_mock_data():
    """Build realistic mock data that mirrors real API responses."""

    # ── Amazon Product Data ──
    amazon_data = {
        "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "price": 24990,
        "price_display": "₹24,990",
        "rating": 4.3,
        "review_count": 12847,
        "asin": "B0BX4L9143",
        "url": "https://www.amazon.in/dp/B0BX4L9143",
        "country": "IN",
        "source_method": "pa_api",
        "reviews": [
            {"body": "Amazing product! Best ever! Must buy!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "Five stars!!!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "I've been using these headphones for 3 months now and the noise cancellation is genuinely impressive. Battery lasts about 28 hours in my experience. The touch controls take some getting used to but overall very satisfied.", "rating": 4.0, "date": "2025-02-20"},
            {"body": "Good sound quality but the ear cushions started peeling after 6 months. Not great for the price point. Sony should use better materials.", "rating": 3.0, "date": "2025-06-15"},
            {"body": "Perfect perfect perfect! Love it so much! Must buy!", "rating": 5.0, "date": "2025-01-16"},
            {"body": "Excellent noise cancelling. Comfortable for long flights. Multipoint connection works well between laptop and phone. Worth the premium over XM4.", "rating": 5.0, "date": "2025-03-10"},
            {"body": "Returned after a week. Sound quality is good but they're too tight on my head. YMMV based on head size.", "rating": 2.0, "date": "2025-04-01"},
            {"body": "Best product! Amazing! Buy now!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "Solid upgrade from my Bose QC35. The ANC is noticeably better. Call quality is decent but not great in windy conditions. The case is sleeker than the XM4 version.", "rating": 4.0, "date": "2025-05-20"},
            {"body": "Five stars!!!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "Bought for my wife. She loves the comfort and sound. We compared with Bose 700 and Sony won on ANC. Bose won on call quality though.", "rating": 4.0, "date": "2025-07-10"},
            {"body": "Good but overpriced. The AirPods Max sounds slightly better for music but costs 2x. For most people Sony is the sweet spot.", "rating": 4.0, "date": "2025-08-05"},
            {"body": "Outstanding!", "rating": 5.0, "date": "2025-01-16"},
            {"body": "Not bad but the XM4 was better value when it was on sale. XM5 lost the folding mechanism which is annoying for travel.", "rating": 3.0, "date": "2025-09-01"},
            {"body": "Love this product! Amazing quality! Best headphones!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "After extensive testing: ANC 9/10, Sound 8/10, Comfort 8/10, Battery 9/10, Call quality 6/10, Build quality 7/10. Overall great but not perfect.", "rating": 4.0, "date": "2025-10-15"},
            {"body": "AMAZING PRODUCT BUY NOW BEST EVER!!!", "rating": 5.0, "date": "2025-01-15"},
            {"body": "The LDAC codec support is a big plus for Android users. Sound quality over LDAC is noticeably better than AAC.", "rating": 5.0, "date": "2025-11-20"},
            {"body": "Superb! Highly recommend!", "rating": 5.0, "date": "2025-01-16"},
            {"body": "Disappointed with the microphone quality for work calls. Everything else is excellent. Had to keep using my old headset for Zoom.", "rating": 3.0, "date": "2025-12-01"},
        ],
    }

    # ── Source Results (simulated API responses) ──
    source_results = {
        "amazon": {
            "success": True,
            "data": amazon_data,
            "source": "amazon_paapi",
            "latency_ms": 342,
            "error": None,
        },
        "reddit": {
            "success": True,
            "data": {
                "found": 47,
                "posts": [
                    {"title": "Sony XM5 vs Bose QC45 — my honest take after 6 months", "subreddit": "headphones", "score": 847, "num_comments": 234},
                    {"title": "PSA: Sony WH-1000XM5 ear cushions cracking issue", "subreddit": "headphones", "score": 523, "num_comments": 156},
                    {"title": "XM5 on sale for ₹19,990 during Amazon GIF — worth it?", "subreddit": "IndianGaming", "score": 312, "num_comments": 89},
                    {"title": "Best ANC headphones 2025 — detailed comparison", "subreddit": "audiophile", "score": 289, "num_comments": 167},
                    {"title": "XM5 multipoint is a game changer for WFH", "subreddit": "WorkFromHome", "score": 201, "num_comments": 45},
                ],
                "subreddits": ["headphones", "IndianGaming", "audiophile", "WorkFromHome", "SonyHeadphones"],
                "total_engagement": 4823,
            },
            "source": "reddit_praw",
            "latency_ms": 890,
            "error": None,
        },
        "youtube": {
            "success": True,
            "data": {
                "found": 23,
                "videos": [
                    {"title": "Sony WH-1000XM5 Review: The King of ANC!", "channel": "MKBHD", "views": 4200000, "likes": 98000},
                    {"title": "XM5 vs QC45 vs AirPods Max — ULTIMATE Comparison", "channel": "Linus Tech Tips", "views": 2800000, "likes": 67000},
                    {"title": "Sony XM5 Long Term Review — 1 Year Later", "channel": "SuperSaf", "views": 1500000, "likes": 34000},
                ],
                "total_views": 12300000,
            },
            "source": "youtube_api",
            "latency_ms": 456,
            "error": None,
        },
        "keepa": {
            "success": True,
            "data": {
                "current_price": 24990,
                "average_price": 22450,
                "lowest_price": 17990,
                "highest_price": 29990,
                "lowest_date": "2025-10-08",
                "data_points": 180,
                "price_range": 12000,
                "prices": [{"price": 22000 + (i % 10) * 500, "date": f"2025-{(i//30)+1:02d}-{(i%28)+1:02d}"} for i in range(90)],
            },
            "source": "keepa",
            "latency_ms": 678,
            "error": None,
        },
        "google_shopping": {
            "success": True,
            "data": {
                "found": 8,
                "items": [
                    {"title": "Sony WH-1000XM5", "price": "₹22,990", "price_numeric": 22990, "source": "Flipkart", "rating": 4.4},
                    {"title": "Sony WH-1000XM5", "price": "₹23,490", "price_numeric": 23490, "source": "Croma", "rating": 4.3},
                    {"title": "Sony WH-1000XM5", "price": "₹24,990", "price_numeric": 24990, "source": "Amazon.in", "rating": 4.3},
                    {"title": "Sony WH-1000XM5", "price": "₹25,999", "price_numeric": 25999, "source": "Reliance Digital", "rating": 4.2},
                ],
                "lowest_price": "₹22,990",
                "lowest_source": "Flipkart",
                "price_range": {"min": 22990, "max": 25999},
            },
            "source": "google_shopping",
            "latency_ms": 534,
            "error": None,
        },
        "reviewmeta": {
            "success": True,
            "data": {
                "adjusted_rating": 3.9,
                "original_rating": 4.3,
                "failed_reviews_pct": 26,
                "analysis_url": "https://reviewmeta.com/amazon/B0BX4L9143",
            },
            "source": "reviewmeta",
            "latency_ms": 1230,
            "error": None,
        },
        "wirecutter": {
            "success": True,
            "data": {
                "found": True,
                "is_top_pick": True,
                "search_url": "https://www.nytimes.com/wirecutter/search/?s=Sony+WH-1000XM5",
            },
            "source": "wirecutter",
            "latency_ms": 345,
            "error": None,
        },
        "rtings": {
            "success": True,
            "data": {
                "found": True,
                "score": 8.4,
                "search_url": "https://www.rtings.com/headphones/reviews/sony/wh-1000xm5",
            },
            "source": "rtings",
            "latency_ms": 289,
            "error": None,
        },
        "trustpilot": {
            "success": True,
            "data": {
                "found": True,
                "trust_score": 3.8,
                "review_count": 1247,
                "url": "https://www.trustpilot.com/review/sony.com",
                "note": "Brand-level trust score, not product-specific",
            },
            "source": "trustpilot",
            "latency_ms": 267,
            "error": None,
        },
    }

    # ── Price Prediction (simulated ARIMA output) ──
    price_prediction = {
        "predicted_lowest": 19990,
        "predicted_average": 22500,
        "drop_probability": 0.72,
        "expected_savings": 5000,
        "savings_percentage": 20.0,
        "best_day_to_buy": 18,
        "best_action": "WAIT_X_DAYS",
        "confidence": 0.78,
        "current_vs_average": "above",
        "upcoming_sales": [
            {"name": "Holi Sale", "days_away": 3, "typical_discount": "10-30%"},
        ],
    }

    # ── Alternatives (simulated) ──
    alternatives_result = {
        "success": True,
        "data": {
            "found": 3,
            "alternatives": [
                {
                    "title": "Jabra Elite 85t Wireless Earbuds",
                    "price": "₹14,990",
                    "price_numeric": 14990,
                    "rating": 4.2,
                    "source": "Amazon.in",
                    "savings_percentage": 40,
                    "why_better": "40% cheaper, comparable ANC, better for small ears",
                },
                {
                    "title": "Bose QuietComfort 45",
                    "price": "₹22,990",
                    "price_numeric": 22990,
                    "rating": 4.4,
                    "source": "Flipkart",
                    "savings_percentage": 8,
                    "why_better": "8% cheaper, more comfortable, better mic for calls",
                },
                {
                    "title": "Samsung Galaxy Buds2 Pro",
                    "price": "₹12,990",
                    "price_numeric": 12990,
                    "rating": 4.1,
                    "source": "Amazon.in",
                    "savings_percentage": 48,
                    "why_better": "48% cheaper, great for Samsung ecosystem, lighter",
                },
            ],
        },
        "source": "google_shopping",
        "latency_ms": 534,
        "error": None,
    }

    # ── AI Verdict (simulated LLM output) ──
    ai_verdict = """WAIT — Don't buy at ₹24,990. This is 11% above the 6-month average of ₹22,450, and our model predicts a drop to ~₹19,990 within 18 days (72% probability). The Holi Sale starts in 3 days with typical 10-30% discounts. Wirecutter's Top Pick and RTINGS 8.4/10 confirm this is a great product — just not at today's price. Our fake review analysis flagged 50% of reviews as suspicious (short generic praise), but ReviewMeta independently found 26% failed reviews, confirming the adjusted rating is 3.9/5 not 4.3/5. Best move: Wait for Holi Sale, buy on Flipkart (₹22,990), use ICICI Amazon Pay card for 5% back, and route through CashKaro for an extra 2-6% cashback."""

    return amazon_data, source_results, price_prediction, alternatives_result, ai_verdict


async def main():
    amazon_data, source_results, price_prediction, alternatives_result, ai_verdict = build_mock_data()

    # Run real analyzers on mock data
    reviews = amazon_data["reviews"]
    fake_analysis = analyze_fake_reviews(reviews)
    regret_analysis = analyze_regret_pattern(reviews)
    confidence = calculate_confidence({"sources": source_results})

    # Run real coupon sniper
    coupons = await find_coupons("Sony WH-1000XM5", "B0BX4L9143", 24990, "IN")

    # Build summary dict
    summary = {
        "total": len(source_results),
        "succeeded": sum(1 for r in source_results.values() if r["success"]),
        "failed": sum(1 for r in source_results.values() if not r["success"]),
        "failed_sources": [n for n, r in source_results.items() if not r["success"]],
    }

    # Generate formatted output
    output = format_beautiful_output(
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

    print(output)
    
    # Save to file
    with open("OUTPUT_PREVIEW.md", "w") as f:
        f.write(output)
    print("\n\n📝 Output saved to OUTPUT_PREVIEW.md")


asyncio.run(main())
