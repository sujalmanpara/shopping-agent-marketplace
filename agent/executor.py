# executor.py — Shopping Truth Agent
# Thin orchestrator following Nextbase standards

import asyncio
import httpx
from typing import AsyncGenerator
from app.core.sse import sse_event, sse_error
from app.core.llm import call_llm
from app.core.config import settings

# Import helper modules (relative imports)
from .scrapers import extract_asin, scrape_amazon, scrape_reddit, scrape_youtube, scrape_twitter
from .analyzers import analyze_fake_reviews, analyze_regret_pattern, calculate_confidence
from .summarizer import generate_summary


async def execute(
    prompt: str,
    keys: dict,
    language: str = None,
    options: dict = None
) -> AsyncGenerator[dict, None]:
    """
    Shopping Truth Agent executor.
    
    Analyzes Amazon products across multiple platforms,
    detects fake reviews, and provides honest buying advice.
    
    Args:
        prompt: Amazon product URL or search query
        keys: {"OPENAI_API_KEY": "sk-xxx"}
        language: User's preferred language (default: English)
        options: Optional config (model, etc.)
    
    Yields:
        SSE events with analysis results
    """
    
    # Extract API key
    api_key = keys.get("OPENAI_API_KEY")
    if not api_key:
        yield sse_error("Missing OPENAI_API_KEY. Please configure your API key.")
        return
    
    # Extract Amazon ASIN from prompt
    asin = extract_asin(prompt)
    if not asin:
        yield sse_error("Please provide a valid Amazon product URL (e.g., amazon.com/dp/B08N5WRWNW)")
        return
    
    yield sse_event("status", "🔍 Extracting product information...")
    
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        # Phase 1: Scrape data from all sources (parallel)
        yield sse_event("status", "⏳ Gathering data from Amazon, Reddit, YouTube, Twitter...")
        
        try:
            amazon_data, reddit_data, youtube_data, twitter_data = await asyncio.gather(
                scrape_amazon(client, asin),
                scrape_reddit(client, f"amazon {asin}"),
                scrape_youtube(client, ""),  # Will update with product name
                scrape_twitter(client, ""),   # Will update with product name
                return_exceptions=True
            )
        except Exception as e:
            yield sse_error(f"Scraping failed: {str(e)}")
            return
        
        # Handle scraping errors
        if isinstance(amazon_data, Exception):
            yield sse_error(f"Failed to scrape Amazon: {str(amazon_data)}")
            return
        
        if "error" in amazon_data:
            yield sse_error(f"Amazon scraping failed: {amazon_data.get('error', 'Unknown error')}")
            return
        
        # Update other scrapers with actual product name
        product_name = amazon_data.get("title", "")
        if product_name:
            if isinstance(reddit_data, dict) and not reddit_data.get("found"):
                reddit_data = await scrape_reddit(client, product_name)
            if isinstance(youtube_data, dict):
                youtube_data = await scrape_youtube(client, product_name)
            if isinstance(twitter_data, dict):
                twitter_data = await scrape_twitter(client, product_name)
        
        # Show progress
        yield sse_event("progress", {
            "amazon": "✅" if amazon_data else "❌",
            "reddit": f"✅ ({reddit_data.get('found', 0)} mentions)" if isinstance(reddit_data, dict) else "❌",
            "youtube": f"✅ ({youtube_data.get('found', 0)} videos)" if isinstance(youtube_data, dict) else "❌",
            "twitter": f"✅ ({twitter_data.get('found', 0)} tweets)" if isinstance(twitter_data, dict) else "❌",
        })
        
        # Phase 2: Analyze data
        yield sse_event("status", "🤖 Analyzing fake reviews and sentiment patterns...")
        
        fake_review_analysis = analyze_fake_reviews(amazon_data.get("reviews", []))
        regret_analysis = analyze_regret_pattern(amazon_data.get("reviews", []))
        confidence_score = calculate_confidence(
            amazon_data,
            reddit_data if isinstance(reddit_data, dict) else {},
            youtube_data if isinstance(youtube_data, dict) else {},
            twitter_data if isinstance(twitter_data, dict) else {}
        )
        
        # Phase 3: Generate LLM summary
        yield sse_event("status", "📝 Generating shopping advice...")
        
        summary = await generate_summary(
            client,
            api_key,
            amazon_data,
            reddit_data if isinstance(reddit_data, dict) else {},
            fake_review_analysis,
            regret_analysis,
            confidence_score
        )
        
        # Phase 4: Return final result
        yield sse_event("result", {
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
            "summary": summary,
        })
