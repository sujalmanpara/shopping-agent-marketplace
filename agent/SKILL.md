# Shopping Truth Agent

AI-powered shopping advisor that analyzes products across 9+ platforms to detect fake reviews, predict regret, and save you money.

> **Marketplace agent by Nextbase.** Logic runs on Nextbase servers. Your API key is used in-memory only and never stored.

---

## Features

- ✅ **Multi-platform analysis** — Amazon, Reddit, YouTube, Twitter
- ✅ **Fake review detection** — Pattern-based ML identifies suspicious reviews
- ✅ **Regret detector** — Analyzes review timelines to spot quality decline
- ✅ **Confidence scoring** — Weighted by source reliability (Reddit 30%, YouTube 25%, etc.)
- ✅ **LLM-powered verdict** — Clear BUY / WAIT / AVOID recommendation
- ✅ **Zero extra API keys** — No Reddit API, no YouTube API, just your LLM key

---

## Setup

Set `OPENAI_API_KEY` in your environment or provide it when calling the agent.

---

## How to Execute

### From OpenClaw CLI:

```bash
# Just paste an Amazon URL
Analyze this product: https://amazon.com/dp/B08N5WRWNW

# Or ask naturally
Should I buy the Sony WH-1000XM5 headphones?
```

### From curl:

```bash
curl -s -X POST https://marketplacebackend-production-58c8.up.railway.app/v1/agents/shopping-agent/execute \
  -H "Content-Type: application/json" \
  -H "X-User-LLM-Key: $OPENAI_API_KEY" \
  -d '{"prompt": "https://amazon.com/dp/B08N5WRWNW"}'
```

---

## Response Format (SSE Stream)

| Event | Data | Meaning |
|-------|------|---------|
| `event: status` | `"🔍 Extracting product data..."` | Progress update |
| `event: progress` | `{"amazon": "✅", "reddit": "✅ (247 mentions)"}` | Source status |
| `event: result` | Full analysis object | Final output |
| `event: error` | Error message | Something went wrong |

### Example Result:

```json
{
  "product": {
    "title": "Sony WH-1000XM4 Wireless Headphones",
    "url": "https://amazon.com/dp/B08N5WRWNW",
    "price": "$278.00",
    "rating": 4.7,
    "review_count": 73429
  },
  "analysis": {
    "confidence": 87,
    "fake_reviews": {
      "score": 12,
      "risk": "low",
      "suspicious_count": 2,
      "total_analyzed": 10
    },
    "regret_warning": {
      "severity": "medium",
      "warning": "⚠️ Ratings dropped 0.6 stars over time",
      "early_avg": 4.8,
      "recent_avg": 4.2
    },
    "sources": {
      "reddit": 247,
      "youtube": 19,
      "twitter": 1203
    }
  },
  "summary": "⚠️ WAIT — Solid headphones but ear pads wear out after 6-12 months (common complaint on Reddit). Price likely to drop 15% during Prime Day in 3 weeks. Buy if discounted below $240, otherwise wait."
}
```

---

## What Makes This Unique

1. **Reddit Truth Bomb** — Compares Amazon (often fake) vs Reddit (brutally honest)
2. **Regret Detector** — Spots products where ratings decline over time
3. **Multi-source confidence** — 9 platforms weighted by reliability
4. **Zero API setup** — No Reddit API, no YouTube API, just works
5. **Actionable verdicts** — Clear BUY/WAIT/AVOID with reasoning

---

## Free vs Premium

**Free Tier:**  
- 10 analyses per day  
- Amazon + Reddit only  
- Basic fake review detection  

**Premium ($9.99/month):**  
- Unlimited analyses  
- All 10 features unlocked  
- Priority support  
- API access  

---

## Privacy

- Your `OPENAI_API_KEY` is used in-memory only and **never stored**
- Product URLs are not logged
- Analysis results are not cached with user identifiers

---

## Support

For issues or feature requests, contact marketplace support or open an issue on GitHub.

---

## Coming Soon (Phase 2-4)

- 💰 **Price prediction** — Historical data + ML forecasting
- 🎟️ **Coupon finder** — Auto-discover discount codes
- 🔄 **Alternative products** — Better options at similar/lower price
- ⚔️ **Battle Mode** — Two AI agents debate pros/cons
- 🌍 **Carbon/Ethics scoring** — Environmental impact + labor practices

---

## Installation

```bash
# In OpenClaw
/agent install shopping-agent

# Test it
Analyze https://amazon.com/dp/B08N5WRWNW
```
