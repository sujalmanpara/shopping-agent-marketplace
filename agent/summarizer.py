# summarizer.py — LLM summary generation

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
