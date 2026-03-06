"""
Feature 2: Community Truth Bomb
Main feature orchestrator
"""

from typing import Dict
from agent.community_scrapers import get_community_truth
from agent.community_analyzer import analyze_community_data


async def community_truth_bomb(product_name: str, asin: str = None, domain: str = 'amazon.com') -> Dict:
    """
    Feature 2: Community Truth Bomb
    
    Scrapes and analyzes community discussions from:
    1. Reddit (PRAW)
    2. Amazon Q&A (Scrapling)
    3. YouTube Comments (yt-dlp)
    
    Returns community insights with common complaints and sentiment
    """
    
    # Step 1: Scrape community data (smart fallback chain)
    community_data = await get_community_truth(product_name, asin, domain)
    
    # Step 2: Analyze community data
    analysis = analyze_community_data(community_data)
    
    return analysis
