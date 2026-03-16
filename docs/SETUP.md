# 🚀 Setup Guide — Shopping Truth Agent

Complete setup from zero to running in under 5 minutes.

---

## Step 1 — Clone & Install

```bash
git clone https://github.com/sujalmanpara/shopping-agent-marketplace.git
cd shopping-agent-marketplace
pip install -r requirements.txt
```

---

## Step 2 — Configure API Keys

Copy the example env file:

```bash
cp .env.example .env
```

Open `.env` and fill in your keys. **Only one LLM key is required** to get started:

```env
# ── REQUIRED (pick ONE) ──────────────────────────
OPENAI_API_KEY=sk-...          # https://platform.openai.com/api-keys
# ANTHROPIC_API_KEY=sk-ant-... # https://console.anthropic.com/
# GEMINI_API_KEY=AIza...       # https://aistudio.google.com/app/apikey
# GROK_API_KEY=xai-...         # https://console.x.ai/
# OPENROUTER_API_KEY=sk-or-... # https://openrouter.ai/keys (access ALL models)

# ── OPTIONAL — Unlocks more features ─────────────
YOUTUBE_API_KEY=               # Free — https://console.cloud.google.com/
SERPAPI_KEY=                   # 100 free/mo — https://serpapi.com/
RAINFOREST_API_KEY=            # Paid — https://www.rainforestapi.com/
SCRAPINGDOG_API_KEY=           # 1000 free/mo — https://www.scrapingdog.com/
KEEPA_API_KEY=                 # Paid — https://keepa.com/#!api
REDDIT_CLIENT_ID=              # Free — https://www.reddit.com/prefs/apps
REDDIT_CLIENT_SECRET=          # Free (same app as above)
```

---

## Step 3 — Run It

```python
import asyncio
import os
from dotenv import load_dotenv
from agent.executor import execute

load_dotenv()

keys = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
    "SERPAPI_KEY": os.getenv("SERPAPI_KEY"),
    # ... add any others you have
}

async def analyze(url):
    async for event in execute(url, keys):
        if event["event"] == "status":
            print(event["data"])
        elif event["event"] == "result":
            print(event["data"])
        elif event["event"] == "error":
            print(f"Error: {event['data']}")

asyncio.run(analyze("https://www.amazon.in/dp/B09R4SF5SP"))
```

---

## What Each Key Unlocks

| Without Key | With Key | Source |
|-------------|----------|--------|
| — | AI verdict & summary | LLM key (required) |
| Free scrape (2 videos, no views) | Full video search + view counts | `YOUTUBE_API_KEY` |
| Camoufox scrape (residential only) | Google Shopping prices | `SERPAPI_KEY` |
| 8 reviews from product page | 100+ reviews, paginated | `RAINFOREST_API_KEY` |
| 8 reviews from product page | 100+ reviews (cheaper tier) | `SCRAPINGDOG_API_KEY` |
| No price history | 6-month price trend graph | `KEEPA_API_KEY` |
| No Reddit posts | Subreddit discussions | `REDDIT_CLIENT_ID/SECRET` |

---

## Supported Inputs

Any Amazon India or US product URL:

```
https://www.amazon.in/dp/B09R4SF5SP
https://www.amazon.in/dp/B09R4SF5SP/ref=...   (with ref tags, works too)
https://www.amazon.com/dp/B0CX44DFVH
https://amzn.in/d/abc123                        (short links — partially supported)
```

---

## Getting API Keys (Step by Step)

### OpenAI (Recommended LLM)
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy and paste into `.env` as `OPENAI_API_KEY`
4. Cost: ~$0.01 per analysis (GPT-4o-mini)

### YouTube Data API v3 (Free)
1. Go to https://console.cloud.google.com/
2. Create a project → Enable "YouTube Data API v3"
3. Credentials → Create API Key
4. Free quota: 10,000 units/day (each search = ~100 units → 100 searches/day free)

### SerpAPI (Google Shopping)
1. Go to https://serpapi.com/
2. Sign up → Copy your API key
3. Free: 100 searches/month
4. Cost: $50/month for 5,000 searches

### Reddit API (Free)
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" → Select "script"
3. Name: "ShoppingAgent", Redirect URI: `http://localhost:8080`
4. Copy `client_id` (under app name) and `secret`
5. Completely free, no rate limit for read-only

### Rainforest API (Best for Reviews)
1. Go to https://www.rainforestapi.com/
2. Sign up for trial
3. Best quality Amazon data — recommended for production use
4. Cost: from ~$80/month

### ScrapingDog (Review Alternative)
1. Go to https://www.scrapingdog.com/
2. Sign up → Copy API key from dashboard
3. Free tier: 1,000 credits/month (1 request = 1 credit for reviews)
4. Paid: $30/month for 100,000 credits

---

## Troubleshooting

### "Product Not Found"
The ASIN doesn't exist or has been removed from Amazon. Double-check the URL.

### "Amazon unavailable — please try again"
Amazon is temporarily rate-limiting or showing a CAPTCHA. Wait 5 minutes and retry.

### "AI verdict generation failed"
Your LLM API key is invalid or has insufficient credits. Check your key at the provider dashboard.

### Results look incomplete (low confidence)
Add more API keys — each one unlocks more data sources and raises confidence. Without SerpAPI and Rainforest, the agent relies on free fallbacks which are less reliable from server/datacenter IPs.

### "ML model not usable"
XGBoost isn't installed. The agent automatically falls back to keyword-based fake review detection. To install: `pip install xgboost scikit-learn`. The output will say "Method: keyword (~80% accuracy)" instead.

---

## System Requirements

- Python 3.10 or higher
- Internet connection
- ~50MB disk space (for dependencies)
- No GPU required
