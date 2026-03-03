# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    User (OpenClaw CLI)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ Amazon URL
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Nextbase Marketplace Backend                    │
│  POST /v1/agents/shopping-agent/execute                      │
│  X-User-LLM-Key: sk-xxx                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    executor.py                               │
│              (Thin orchestrator, ~80 lines)                  │
└────────┬────────────────────────┬────────────────────────────┘
         │                        │
         ↓                        ↓
┌────────────────────┐   ┌────────────────────────────────────┐
│   scrapers.py      │   │       analyzers.py                 │
│  (Parallel fetch)  │   │  - analyze_fake_reviews()          │
├────────────────────┤   │  - analyze_regret_pattern()        │
│ • scrape_amazon()  │   │  - calculate_confidence()          │
│ • scrape_reddit()  │   └────────────────────────────────────┘
│ • scrape_youtube() │                  │
│ • scrape_twitter() │                  ↓
└────────┬───────────┘   ┌────────────────────────────────────┐
         │               │       summarizer.py                 │
         │               │  generate_summary()                 │
         │               │  (Calls LLM with user's key)        │
         └───────────────┴────────────────────────────────────┘
                                  │
                                  ↓
                         ┌────────────────────┐
                         │   Final Result     │
                         │  (SSE stream back  │
                         │   to user)         │
                         └────────────────────┘
```

## Data Flow

### Phase 1: Scraping (Parallel)
```python
await asyncio.gather(
    scrape_amazon(client, asin),
    scrape_reddit(client, product_name),
    scrape_youtube(client, product_name),
    scrape_twitter(client, product_name)
)
```

**Latency:** 3-5 seconds (parallel execution)

### Phase 2: Analysis
```python
fake_reviews = analyze_fake_reviews(reviews)
regret = analyze_regret_pattern(reviews)
confidence = calculate_confidence(all_sources)
```

**Latency:** < 100ms (pure Python, no I/O)

### Phase 3: LLM Summary
```python
summary = await call_llm(
    client, api_key,
    system="You are a brutally honest shopping advisor...",
    user=context
)
```

**Latency:** 2-4 seconds (LLM API call)

**Total:** ~12-18 seconds end-to-end

## Module Breakdown

### constants.py
Configuration and weights. No logic.

```python
SOURCE_WEIGHTS = {
    "reddit": 30,      # Most reliable (brutally honest)
    "youtube": 25,     # Video proof
    "twitter": 20,     # Real-time sentiment
    "amazon_qa": 15,   # Specific issues
    "google_reviews": 10
}
```

### scrapers.py
Pure scraping functions. No analysis.

**Key patterns:**
- Random user agents to avoid bot detection
- 2-second delays between requests
- Graceful error handling (returns `{"error": "..."}`)
- No API keys required (HTML parsing only)

### analyzers.py
Pure functions. No I/O.

**Fake review detection:**
- Generic praise + short length = suspicious
- All 5-star + minimal text = suspicious
- Score: `(suspicious_count / total) * 100`

**Regret detector:**
- Compare early vs recent ratings
- Drop > 1.0 stars = high severity
- Drop > 0.5 stars = medium severity

**Confidence scoring:**
- Weighted by source reliability
- 100 = all sources confirm
- 0 = no data

### summarizer.py
LLM wrapper. Constructs context and calls `app.core.llm.call_llm()`.

**Context sent to LLM:**
- Product title, price, rating
- Reddit mentions (top 5)
- Fake review score
- Regret warning
- Sample reviews (truncated to 6000 chars)

### executor.py
Thin orchestrator. Just wires everything together.

**Responsibilities:**
- Extract ASIN from user prompt
- Call scrapers in parallel
- Call analyzers with results
- Call summarizer with aggregated data
- Yield SSE events for progress

**NOT responsible for:**
- Business logic (lives in helpers)
- Direct LLM calls (lives in summarizer)
- Parsing HTML (lives in scrapers)

## Error Handling

### Scraping Failures
```python
try:
    resp = await client.get(url, ...)
except Exception as e:
    return {"error": str(e), "found": 0}
```

All scrapers return dicts. Executor checks for `"error"` key.

### LLM Failures
`app.core.llm.call_llm()` handles retries (2x with exponential backoff).

If all retries fail → executor yields `sse_error("...")`.

### Invalid Input
```python
asin = extract_asin(prompt)
if not asin:
    yield sse_error("Please provide a valid Amazon URL")
    return
```

## Security

### User API Keys
- Passed in `X-User-LLM-Key` header
- Used in-memory only (never stored)
- Sent to OpenAI/Anthropic API via HTTPS

### Rate Limiting
Implemented in marketplace backend (not in agent code):

```python
# In app/routes/execute.py
if not await check_rate_limit(user_id, "shopping-agent", limit=10):
    return sse_error("Free tier limit reached")
```

### Scraping Rate Limits
- 2-second delays between requests
- Random user agents
- No login/cookies required
- Public data only

## Performance Optimization

### Current
- Parallel scraping (asyncio.gather)
- Context truncation (6000 chars max)
- LLM: gpt-4o-mini (fast + cheap)

### Future
- Cache results for 24h (same ASIN = instant)
- Use Redis for cache
- Batch multiple requests
- Add residential proxies if rate-limited

## Deployment

### Nextbase Backend
```bash
cp -r agent/* /path/to/backend/app/agents/shopping_agent/
curl -X POST .../admin/agents/reload
```

### OpenClaw
Agent auto-discovered from marketplace. User just installs.

## Testing

### Unit Tests
```bash
pytest tests/test_analyzers.py
pytest tests/test_scrapers.py
```

### Integration Test
```bash
curl -X POST .../execute \
  -H "X-User-LLM-Key: $OPENAI_API_KEY" \
  -d '{"prompt": "https://amazon.com/dp/B08N5WRWNW"}'
```

## Monitoring

### Key Metrics
- Scraping success rate (per source)
- Average latency (total + per phase)
- LLM cost per request
- User satisfaction (implicit: repeat usage)

### Logging
All errors logged to stdout (captured by Railway/Docker).

```python
import logging
logger = logging.getLogger(__name__)
logger.error(f"Failed to scrape Amazon: {error}")
```

## Future Enhancements

### Phase 2
- Price prediction (historical data + ML)
- Coupon finder (auto-discover codes)
- Alternative products (better options)

### Phase 3
- Battle Mode (AI debate pros/cons)
- Carbon footprint calculator
- Ethics scoring (labor practices)

---

**Questions?** Open a GitHub issue or contact support.
