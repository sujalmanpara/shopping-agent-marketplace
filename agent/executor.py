# executor.py — Shopping Truth Agent (ALL 10 FEATURES)
# Complete implementation with all features

import asyncio
import httpx
from typing import AsyncGenerator
from app.core.sse import sse_event, sse_error
from app.core.llm import call_llm
from app.core.config import settings

# Import all scrapers and analyzers
from .scrapers import (
    extract_asin, 
    scrape_amazon, 
    scrape_reddit, 
    scrape_youtube, 
    scrape_twitter,
    scrape_price_history,      # Feature 7
    find_alternatives,          # Feature 8
    find_coupons,               # Feature 9
    calculate_ethics_score      # Feature 10
)
from .analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence
from .summarizer import generate_summary


async def execute(
    prompt: str,
    keys: dict,
    language: str = None,
    options: dict = None
) -> AsyncGenerator[dict, None]:
    """
    Shopping Truth Agent executor - ALL 10 FEATURES
    
    Features:
    1. Multi-platform analysis (Amazon, Reddit, YouTube, Twitter)
    2. Reddit Truth Bomb
    3. Fake review detection
    4. Regret detector
    5. Confidence scoring
    6. LLM verdict
    7. Price drop prediction ✨ NEW
    8. Alternative products ✨ NEW
    9. Coupon finder ✨ NEW
    10. Carbon & ethics score ✨ NEW
    """
    
    # Extract API key
    api_key = keys.get("OPENAI_API_KEY")
    if not api_key:
        yield sse_error("Missing OPENAI_API_KEY. Please configure your API key.")
        return
    
    # Extract Amazon ASIN
    asin = extract_asin(prompt)
    if not asin:
        yield sse_error("Please provide a valid Amazon product URL (e.g., amazon.com/dp/B08N5WRWNW)")
        return
    
    yield sse_event("status", "🔍 Extracting product information...")
    
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        # PHASE 1: Scrape core data (Features 1-2)
        yield sse_event("status", "⏳ Gathering data from Amazon, Reddit, YouTube, Twitter...")
        
        try:
            amazon_data, reddit_data, youtube_data, twitter_data = await asyncio.gather(
                scrape_amazon(client, asin),
                scrape_reddit(client, f"amazon {asin}"),
                scrape_youtube(client, ""),
                scrape_twitter(client, ""),
                return_exceptions=True
            )
        except Exception as e:
            yield sse_error(f"Scraping failed: {str(e)}")
            return
        
        if isinstance(amazon_data, Exception) or "error" in amazon_data:
            yield sse_error(f"Amazon scraping failed: {amazon_data.get('error', str(amazon_data))}")
            return
        
        # Update scrapers with product name
        product_name = amazon_data.get("title", "")
        brand = product_name.split()[0] if product_name else ""
        
        if product_name:
            if isinstance(reddit_data, dict) and not reddit_data.get("found"):
                reddit_data = await scrape_reddit(client, product_name)
            if isinstance(youtube_data, dict):
                youtube_data = await scrape_youtube(client, product_name)
            if isinstance(twitter_data, dict):
                twitter_data = await scrape_twitter(client, product_name)
        
        yield sse_event("progress", {
            "amazon": "✅" if amazon_data else "❌",
            "reddit": f"✅ ({reddit_data.get('found', 0)} mentions)" if isinstance(reddit_data, dict) else "❌",
            "youtube": f"✅ ({youtube_data.get('found', 0)} videos)" if isinstance(youtube_data, dict) else "❌",
            "twitter": f"✅ ({twitter_data.get('found', 0)} tweets)" if isinstance(twitter_data, dict) else "❌",
        })
        
        # PHASE 2: Advanced analysis (Features 3-5)
        yield sse_event("status", "🤖 Analyzing fake reviews, regret patterns, and gathering price data...")
        
        fake_review_analysis = analyze_fake_reviews(amazon_data.get("reviews", []))
        regret_analysis = analyze_regret_pattern(amazon_data.get("reviews", []))
        confidence_score = calculate_confidence(
            amazon_data,
            reddit_data if isinstance(reddit_data, dict) else {},
            youtube_data if isinstance(youtube_data, dict) else {},
            twitter_data if isinstance(twitter_data, dict) else {}
        )
        
        # PHASE 3: NEW FEATURES (7-10) 🚀
        yield sse_event("status", "🚀 Checking price history, alternatives, coupons, and ethics...")
        
        # Feature 7: Price prediction
        price_history, alternatives, coupons, ethics = await asyncio.gather(
            scrape_price_history(client, asin),
            find_alternatives(client, product_name, amazon_data.get("price", "")),
            find_coupons(client, product_name, asin),
            calculate_ethics_score(client, product_name, brand),
            return_exceptions=True
        )
        
        # PHASE 4: LLM Summary (Feature 6)
        yield sse_event("status", "📝 Generating comprehensive shopping advice...")
        
        summary = await generate_summary(
            client,
            api_key,
            amazon_data,
            reddit_data if isinstance(reddit_data, dict) else {},
            fake_review_analysis,
            regret_analysis,
            confidence_score
        )
        
        # PHASE 5: Final comprehensive result
        result = {
            "product": {
                "title": amazon_data.get("title"),
                "url": amazon_data.get("url"),
                "price": amazon_data.get("price"),
                "rating": amazon_data.get("rating"),
                "review_count": amazon_data.get("review_count"),
            },
            "analysis": {
                "confidence": confidence_score,
                "fake_reviews": fake_review_analysis,
                "regret_warning": regret_analysis,
                "sources": {
                    "reddit": reddit_data.get("found", 0) if isinstance(reddit_data, dict) else 0,
                    "youtube": youtube_data.get("found", 0) if isinstance(youtube_data, dict) else 0,
                    "twitter": twitter_data.get("found", 0) if isinstance(twitter_data, dict) else 0,
                }
            },
            "price_prediction": price_history if not isinstance(price_history, Exception) else None,
            "alternatives": alternatives if not isinstance(alternatives, Exception) else {"found": 0},
            "coupons": coupons if not isinstance(coupons, Exception) else {"found": 0},
            "ethics": ethics if not isinstance(ethics, Exception) else None,
            "summary": summary,
        }
        
        yield sse_event("result", result)
