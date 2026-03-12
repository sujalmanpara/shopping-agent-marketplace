# executor.py — Beautiful output for all 10 features

import asyncio
from typing import AsyncGenerator
from app.core.sse import sse_event, sse_error
from app.core.config import settings

from .scrapers import (
    extract_asin, scrape_amazon, scrape_reddit, scrape_youtube, scrape_twitter,
    scrape_price_history, find_alternatives, find_coupons, calculate_ethics_score
)
from .stealth_scraper import scrape_all_platforms
from .analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence
from .summarizer import generate_summary, format_beautiful_output
from .community_feature import community_truth_bomb


async def execute(
    prompt: str,
    keys: dict,
    language: str = None,
    options: dict = None
) -> AsyncGenerator[dict, None]:
    """Shopping Truth Agent - ALL 10 FEATURES with beautiful output"""
    
    api_key = keys.get("OPENAI_API_KEY")
    if not api_key:
        yield sse_error("Missing OPENAI_API_KEY")
        return
    
    asin = extract_asin(prompt)
    if not asin:
        yield sse_error("Please provide a valid Amazon product URL")
        return
    
    yield sse_event("status", "🔍 Analyzing product across 10+ data sources...")
    
    # Phase 1: Scraping
    yield sse_event("status", "⏳ Scraping Amazon, Reddit, YouTube, Twitter...")
    
    amazon_data, reddit_data, youtube_data, twitter_data = await asyncio.gather(
        scrape_amazon(asin),
        scrape_reddit(f"amazon {asin}"),
        scrape_youtube(""),
        scrape_twitter(""),
        return_exceptions=True
    )
    
    if isinstance(amazon_data, Exception) or "error" in amazon_data:
        yield sse_error(f"Scraping failed: {amazon_data.get('error', str(amazon_data))}")
        return
    
    product_name = amazon_data.get("title", "")
    brand = product_name.split()[0] if product_name else ""
    
    # Update with product name
    if product_name:
        reddit_data = await scrape_reddit(product_name) if not isinstance(reddit_data, dict) or not reddit_data.get("found") else reddit_data
        youtube_data = await scrape_youtube(product_name) if isinstance(youtube_data, dict) else youtube_data
        twitter_data = await scrape_twitter(product_name) if isinstance(twitter_data, dict) else twitter_data
    
    # Phase 1.5: Multi-Platform Scraping (Feature 1 UPGRADE — Hybrid Camoufox + Scrapling)
    yield sse_event("status", "🌐 Scraping 15 platforms (Walmart, Target, BestBuy, Flipkart, TikTok, Trustpilot...)")
    
    multi_platform_data = await scrape_all_platforms(
        product_name=product_name,
        asin=asin,
        brand=brand
    )
    
    # Phase 2: Community Truth Bomb (Feature 2) 🆕
    yield sse_event("status", "💬 Analyzing community discussions (Reddit, Amazon Q&A, YouTube)...")
    
    community_data = await community_truth_bomb(product_name, asin)
    
    # Phase 3: Analysis
    yield sse_event("status", "🕵️ Detecting fake reviews & analyzing patterns...")
    
    fake_analysis = analyze_fake_reviews(amazon_data.get("reviews", []))
    regret_analysis = analyze_regret_pattern(amazon_data.get("reviews", []))
    confidence = calculate_confidence(
        amazon_data,
        reddit_data if isinstance(reddit_data, dict) else {},
        youtube_data if isinstance(youtube_data, dict) else {},
        twitter_data if isinstance(twitter_data, dict) else {}
    )
    
    # Phase 4: Advanced features
    yield sse_event("status", "💰 Checking prices, alternatives, coupons, ethics...")
    
    price_pred, alternatives, coupons, ethics = await asyncio.gather(
        scrape_price_history(asin),
        find_alternatives(product_name, amazon_data.get("price", "")),
        find_coupons(product_name, asin, amazon_data.get("price_numeric", None), "IN"),
        calculate_ethics_score(product_name, brand),
        return_exceptions=True
    )
    
    # Phase 5: AI verdict
    yield sse_event("status", "🤖 Generating AI verdict...")
    
    ai_verdict = await generate_summary(
        api_key, amazon_data,
        reddit_data if isinstance(reddit_data, dict) else {},
        fake_analysis, regret_analysis, confidence
    )
    
    # Phase 6: Format beautiful output
    beautiful_output = format_beautiful_output(
        amazon_data, fake_analysis, regret_analysis, confidence,
        reddit_data if isinstance(reddit_data, dict) else {},
        youtube_data if isinstance(youtube_data, dict) else {},
        twitter_data if isinstance(twitter_data, dict) else {},
        price_pred if not isinstance(price_pred, Exception) else {},
        alternatives if not isinstance(alternatives, Exception) else {},
        coupons if not isinstance(coupons, Exception) else {},
        ethics if not isinstance(ethics, Exception) else {},
        ai_verdict,
        community_data if not isinstance(community_data, Exception) else {},  # 🆕 Feature 2
        multi_platform_data if not isinstance(multi_platform_data, Exception) else {}  # 🆕 Feature 1 Upgrade
    )
    
    # Return formatted text result
    yield sse_event("result", beautiful_output)
