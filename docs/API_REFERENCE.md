# 📖 API Reference — Shopping Truth Agent

---

## Main Entry Point

### `execute(prompt, keys, country=None)`

The primary function. Accepts an Amazon URL and returns an async generator of events.

```python
from agent.executor import execute

async for event in execute(
    prompt="https://www.amazon.in/dp/B09R4SF5SP",
    keys={"OPENAI_API_KEY": "sk-..."}
):
    print(event)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | `str` | Yes | Amazon product URL or ASIN |
| `keys` | `dict` | Yes | API keys dict (see below) |
| `country` | `str` | No | `"IN"` or `"US"` — auto-detected from URL |

**Yields:** `dict` with keys:
- `event`: `"status"` | `"result"` | `"error"`
- `data`: `str` — message or formatted report

---

## Keys Dictionary

All keys are optional except one LLM key:

```python
keys = {
    # LLM (pick one — required)
    "OPENAI_API_KEY": "sk-...",
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "GEMINI_API_KEY": "AIza...",
    "GROK_API_KEY": "xai-...",
    "OPENROUTER_API_KEY": "sk-or-...",

    # Data sources (all optional)
    "YOUTUBE_API_KEY": "AIza...",
    "SERPAPI_KEY": "...",
    "RAINFOREST_API_KEY": "...",
    "SCRAPINGDOG_API_KEY": "...",
    "KEEPA_API_KEY": "...",
    "REDDIT_CLIENT_ID": "...",
    "REDDIT_CLIENT_SECRET": "...",

    # Browser server (auto-detected from /data/browser-server-token)
    "CAMOUFOX_TOKEN": "...",
    "CAMOUFOX_PORT": "9222",
}
```

---

## Direct API Layer Functions

You can call individual data-fetch functions directly:

```python
from agent.api_layer import (
    fetch_amazon_product,
    fetch_youtube_reviews,
    fetch_google_shopping,
    fetch_all_sources,
    fetch_alternatives,
)
```

### `fetch_amazon_product(asin, country, keys)`

```python
result = await fetch_amazon_product("B09R4SF5SP", "IN", keys)
# Returns:
{
    "success": True,
    "source": "amazon_camoufox",
    "data": {
        "title": "Daikin 0.8 Ton 3 Star Split AC",
        "price": 24990.0,
        "price_display": "₹24,990",
        "rating": 4.1,
        "review_count": 2265,
        "reviews": [...],  # list of review dicts
        "features": [...],  # bullet point features
        "asin": "B09R4SF5SP",
        "url": "https://www.amazon.in/dp/B09R4SF5SP",
        "brand": "Daikin",
        "country": "IN",
    },
    "latency_ms": 3241
}
```

### `fetch_youtube_reviews(product_name, keys)`

```python
result = await fetch_youtube_reviews("Daikin 0.8 Ton Split AC", keys)
# Returns:
{
    "success": True,
    "source": "youtube",
    "data": {
        "videos": [
            {
                "title": "Daikin AC Unboxing",
                "url": "https://youtube.com/watch?v=...",
                "video_id": "...",
                "channel": "Tech Reviews",
                "views": 109000,
            }
        ],
        "found": 2,
        "total_views": 203000,
    }
}
```

### `fetch_google_shopping(product_name, country, keys)`

```python
result = await fetch_google_shopping("Daikin 0.8 Ton AC", "IN", keys)
# Returns:
{
    "success": True,
    "source": "google_shopping",
    "data": {
        "products": [
            {
                "title": "Daikin 0.8 Ton 3 Star Split AC",
                "price": 24990.0,
                "price_display": "₹24,990",
                "store": "amazon.in",
                "rating": 4.1,
                "url": "...",
            }
        ],
        "lowest_price": 24990.0,
        "lowest_store": "amazon.in",
    }
}
```

### `fetch_all_sources(asin, product_name, brand, country, keys)`

Fetches all sources in parallel.

```python
results = await fetch_all_sources(
    asin="B09R4SF5SP",
    product_name="Daikin 0.8 Ton Split AC",
    brand="Daikin",
    country="IN",
    keys=keys
)
# Returns:
{
    "sources": {
        "reddit": {"success": False, "error": "..."},
        "youtube": {"success": True, "data": {...}},
        "keepa": {"success": False, "error": "No Keepa key"},
        "wirecutter": {"success": True, "data": {"found": True, "is_top_pick": True}},
        "rtings": {"success": True, "data": {"found": True, "score": 7.5}},
        "trustpilot": {"success": True, "data": {"trust_score": 4.9}},
        "google_shopping": {"success": True, "data": {...}},
    },
    "summary": {
        "total": 8,
        "succeeded": 5,
        "failed": 3,
        "success_rate": 0.625,
        "total_latency_ms": 4230,
    }
}
```

---

## Analysis Functions

```python
from agent.analyzers import (
    detect_fake_reviews,
    analyze_star_distribution,
    calculate_confidence,
    analyze_review_timeline,
    score_review_quality,
)
```

### `detect_fake_reviews(reviews)`

```python
result = detect_fake_reviews(reviews_list)
# Returns:
{
    "risk": "limited",           # none/low/limited/medium/high/critical
    "score": 25,                 # percentage of suspicious reviews
    "suspicious_count": 2,
    "total_analyzed": 8,
    "method": "keyword",         # or "ml" if xgboost installed
    "model_accuracy": "~80%",
    "flagged_reviews": [...],
}
```

### `analyze_star_distribution(star_dist)`

```python
# star_dist = {"5": 61, "4": 18, "3": 6, "2": 3, "1": 12}  (percentages)
result = analyze_star_distribution(star_dist)
# Returns:
{
    "j_score": 0.15,             # 0-1, higher = more J-shaped = more suspicious
    "is_j_shaped": False,
    "interpretation": "positive_natural",  # positive_natural / positive_suspicious / negative / polarized
    "label": "✅ Positive but natural skew",
}
```

### `calculate_confidence(source_results)`

```python
result = calculate_confidence(source_results)
# Returns:
{
    "overall": 0.64,             # 0.0-1.0
    "level": "MEDIUM",           # HIGH / MEDIUM / LOW
    "sufficiency": 0.53,
    "agreement": 0.84,
    "quality": 0.50,
    "sources_used": 6,
    "sources_total": 8,
    "breakdown": {
        "amazon": 0.2,
        "youtube": 0.1,
        ...
    }
}
```

---

## Output Formatter

```python
from agent.summarizer import format_beautiful_output

output_string = format_beautiful_output(
    amazon_data=amazon_result["data"],
    source_results=all_sources,
    fake_analysis=fake_detect_result,
    confidence=confidence_result,
    price_prediction=price_pred,
    alternatives=alternatives_data,
    coupon_result=coupon_result,
    fake_review_summary=fake_summary,
    star_analysis=star_dist_analysis,
    review_quality=quality_result,
)
print(output_string)
```

---

## Integrating with a Web Server

The `execute()` generator is SSE-compatible. Example with FastAPI:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from agent.executor import execute
import json

app = FastAPI()

@app.get("/analyze")
async def analyze(url: str):
    keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        # ... other keys
    }

    async def event_stream():
        async for event in execute(url, keys):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | One LLM required | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | One LLM required | — | Anthropic API key |
| `GEMINI_API_KEY` | One LLM required | — | Google Gemini API key |
| `GROK_API_KEY` | One LLM required | — | xAI Grok API key |
| `OPENROUTER_API_KEY` | One LLM required | — | OpenRouter API key |
| `YOUTUBE_API_KEY` | Optional | — | YouTube Data API v3 key |
| `SERPAPI_KEY` | Optional | — | SerpAPI key for Google Shopping |
| `RAINFOREST_API_KEY` | Optional | — | Rainforest/TrajectData API key |
| `SCRAPINGDOG_API_KEY` | Optional | — | ScrapingDog API key |
| `KEEPA_API_KEY` | Optional | — | Keepa API key for price history |
| `REDDIT_CLIENT_ID` | Optional | — | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Optional | — | Reddit app client secret |
| `CAMOUFOX_TOKEN` | Optional | Auto-detected | Browser server auth token |
| `CAMOUFOX_PORT` | Optional | `9222` | Browser server port |
