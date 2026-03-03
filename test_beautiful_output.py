#!/usr/bin/env python3
"""Test beautiful formatted output"""

import sys
sys.path.insert(0, 'agent')

from agent.summarizer import format_beautiful_output

# Simulate complete data
amazon_data = {
    "title": "Garnier Men Face Wash, Brightening & Anti-Pollution, TurboBright Double Action, 100g",
    "price": "₹207.00",
    "rating": 4.3,
    "review_count": 35579
}

fake_analysis = {
    "score": 8,
    "risk": "low",
    "suspicious_count": 2,
    "total_analyzed": 10
}

regret_analysis = {
    "severity": "low",
    "warning": None
}

confidence = 85

reddit_data = {"found": 12}
youtube_data = {"found": 19}
twitter_data = {"found": 143}

price_prediction = {
    "prediction": {
        "event": "Prime Day",
        "days_away": 18,
        "predicted_drop": "15-20%",
        "advice": "WAIT 18 days for Prime Day discount"
    }
}

alternatives = {
    "found": 3,
    "alternatives": [
        {
            "title": "Himalaya Men Pimple Clear Neem Face Wash 100ml",
            "price": "₹165.00",
            "price_num": 165,
            "rating": 4.4,
            "savings": "20%"
        },
        {
            "title": "Nivea Men Dark Spot Reduction Face Wash 100g",
            "price": "₹189.00",
            "price_num": 189,
            "rating": 4.2,
            "savings": "9%"
        }
    ]
}

coupons = {
    "found": 2,
    "coupons": [
        {"code": "AMAZON35", "discount": "35% off with coupon"},
        {"code": "FIRST10", "discount": "10% off first order"}
    ]
}

ethics = {
    "carbon_footprint": {
        "co2_kg": 2,
        "recyclable": "Yes (packaging)"
    },
    "ethics": {
        "grade": "B",
        "labor_practices": "Good practices, some improvements needed",
        "sustainability": "Moderate"
    }
}

ai_verdict = "BUY. With a strong 4.3/5 rating from 35K+ reviews and only 8% fake review risk, this is a reliable choice. However, consider waiting 18 days for Prime Day to save 15-20%, or check the cheaper Himalaya alternative (₹165, 4.4★) for better value."

# Generate beautiful output
output = format_beautiful_output(
    amazon_data, fake_analysis, regret_analysis, confidence,
    reddit_data, youtube_data, twitter_data,
    price_prediction, alternatives, coupons, ethics, ai_verdict
)

print(output)
