# 🧠 How It Works — Shopping Truth Agent

A deep dive into how the agent analyzes products and generates verdicts.

---

## The Big Picture

When you paste an Amazon URL, the agent:

1. **Extracts the ASIN** from the URL
2. **Fetches product data** from Amazon (with 4-tier fallback)
3. **Queries 7+ other sources in parallel** (YouTube, Google Shopping, Wirecutter, etc.)
4. **Runs analysis** (fake reviews, price check, quality scoring)
5. **Finds savings** (coupons, cashback, credit card rewards)
6. **Asks an LLM** to synthesize everything into a verdict
7. **Formats and returns** a structured report

Total time: **5–15 seconds** depending on available API keys.

---

## Data Sources

### Amazon (Primary Source)

The agent tries 4 methods in order, using the first that succeeds:

```
Tier 1: Rainforest API        → Best quality, enterprise-grade
         (if RAINFOREST_API_KEY set)
         
Tier 2: ScrapingDog API       → Good quality, cheaper
         (if SCRAPINGDOG_API_KEY set)
         
Tier 3: Camoufox Browser      → Stealth browser automation
         (uses modified Firefox, passes bot detection)
         
Tier 4: Direct HTTP           → Simple request with headers
         (fastest, but may get blocked from datacenter IPs)
```

**What it extracts:** Title, price, rating, review count, reviews, star distribution, product features, images.

### Amazon Rating Widget (Always Free)

A separate undocumented Amazon endpoint returns:
- Average rating from **all** ratings (not just reviews)
- Star distribution breakdown (% of 1★, 2★, 3★, 4★, 5★)
- Total ratings count

This works **without any login or API key** and provides the most reliable rating data.

### YouTube

```
Tier 1: YouTube Data API v3   → Structured results, view counts, channels
         (if YOUTUBE_API_KEY set)
         
Tier 2: YouTube search scrape → Free, gets video IDs and titles
         (no API key needed, but no view counts)
```

### Google Shopping

```
Tier 1: SerpAPI               → Structured product listings, prices, stores
         (if SERPAPI_KEY set)
         
Tier 2: Camoufox Google scrape → Works from residential IPs
         (blocked by CAPTCHA from datacenter IPs)
```

### Review Bulk Fetching

```
Tier 1: Rainforest Reviews API → 100+ reviews, paginated, helpful votes
Tier 2: ScrapingDog Reviews    → 100+ reviews alternative
Tier 3: Product page scrape    → 8 reviews (always available)
```

### Always-Free Sources (No API Key)
- **Wirecutter** — New York Times expert picks
- **RTINGS** — Lab-tested scores for electronics
- **Trustpilot** — Brand-level trust scores (note: brand-level, not product-level)
- **Reddit** — User discussions via HTTP search (limited; REDDIT_CLIENT_ID unlocks full API)

---

## Analysis Modules

### 1. Fake Review Detection

Uses a 3-signal approach:

**Signal A: Star Distribution Analysis**
Analyzes the pattern of 1★–5★ ratings from the Amazon rating widget (often 2,000+ ratings). Calculates a "J-score":
- Normal product: bell curve or moderate positive skew (e.g., 5★=60%, 4★=20%, 3★=8%, 2★=5%, 1★=7%)
- Fake farm signature: J-shape (e.g., 5★=90%, 4★=3%, 3★=1%, 2★=1%, 1★=5%)

**Signal B: Keyword Analysis (always active)**
Scans review text for patterns common in paid reviews:
- Excessive praise without specifics
- Suspiciously short reviews
- Template-style language
- Immediate 5-star patterns

**Signal C: XGBoost ML Model (if installed)**
A trained classifier on 83 labeled review samples. Uses 216 text + metadata features.
⚠️ Small training set — treat as supplementary signal, not ground truth.

**Combined output:**
- Risk level: LOW / LIMITED / MEDIUM / HIGH / CRITICAL
- Suspicious review count and percentage
- Adjusted rating (with suspicious reviews removed)

### 2. Price Benchmarking

Compares the current price against:
- 10 similar products in the same category (via Google Shopping)
- Historical average (via Keepa if key provided)

Outputs: "X% below/above average", "Good deal / Fair / Overpriced"

### 3. Price Prediction (ARIMA)

Uses a statistical ARIMA model to predict price trend:
- Recent price change velocity
- Sale calendar proximity (Republic Day, Prime Day, Diwali, etc.)
- Historical volatility

Outputs: BUY_NOW / WAIT / WAIT_IF_POSSIBLE + estimated savings

### 4. Review Quality Scoring

Scores each review on detail level:
- **Detailed (40+ words, specific)**: +full points
- **Medium (15-40 words)**: +partial points
- **One-liner (<15 words)**: minimal points

Combined into a 0–100 quality score.

### 5. Confidence Scoring

Three-dimensional score:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Sufficiency | 40% | How many sources returned data |
| Agreement | 30% | Do ratings agree across sources? |
| Quality | 30% | Richness/depth of data |

Thresholds:
- **HIGH** (≥65%): Multiple quality sources agree
- **MEDIUM** (40–64%): Some sources, some gaps
- **LOW** (<40%): Insufficient data to be confident

---

## Savings Engine

The coupon and savings module checks:

1. **Live coupon codes** — From CouponAPI and web scraping
2. **Cashback platforms** — CashKaro, Magicpin, Amazon Pay
3. **Credit card rewards** — Hardcoded database of India's best cards:
   - ICICI Amazon Pay (5% for Prime)
   - HDFC Millennia (5% via SmartBuy)
   - Axis Flipkart (5% on Flipkart)
   - HDFC Infinia, Regalia (reward points)
4. **UPI cashback** — Amazon Pay UPI deals
5. **Bank offers** — Sale-period bank offers

Calculates the **Best Deal**: Optimal combination of cashback + card reward.

---

## AI Verdict

After all analysis, the agent sends a structured JSON context to your LLM:

```json
{
  "product": {"title": "...", "price": "₹24,990", "rating": 4.1, "review_count": 2265},
  "fake_reviews": {"risk": "limited", "suspicious_count": 2, "total_analyzed": 8},
  "confidence": {"overall": 0.64, "level": "MEDIUM", "sources_used": 6},
  "sources": {
    "wirecutter": {"is_top_pick": true},
    "rtings": {"score": 7.5},
    "trustpilot": {"trust_score": 4.9}
  },
  "alternatives": [...],
  "price_prediction": {"best_action": "BUY_NOW", ...}
}
```

The LLM is instructed to:
- Give a clear **BUY / WAIT / AVOID** verdict in the first sentence
- Be concise (5–7 sentences)
- Only use data provided (no hallucination)
- Mention specific alternatives, wait periods, or card recommendations

---

## Output Format

The agent returns a beautifully formatted text report with:

```
╔═══════════════════════════════════╗
║  🛒 SHOPPING TRUTH AGENT v2.0     ║
╚═══════════════════════════════════╝

Product name, brand, price, rating, review count

VERDICT box (BUY / WAIT / AVOID)

Trust bar + confidence % + fake risk label + sources count

Price Check — position vs category average
Best Deal — calculated optimal savings

DEEP ANALYSIS section:
  - Top YouTube video reviews
  - Fake review analysis + star distribution
  - Review timeline + quality score
  - Price prediction chart
  - Alternatives comparison
  - Cross-store price comparison

SAVINGS section:
  - Cashback options
  - Credit card recommendations

AI VERDICT — natural language summary

Footer — source status + confidence
```

---

## Streaming Events

The `execute()` function is an async generator that yields events:

```python
async for event in execute(url, keys):
    event_type = event["event"]   # "status" | "result" | "error"
    data = event["data"]          # string content
```

| Event | When | Data |
|-------|------|------|
| `status` | During processing | Progress message (e.g., "📦 Fetching Amazon...") |
| `result` | End of analysis | Full formatted report string |
| `error` | On failure | Error message string |

This is **SSE-compatible** — you can pipe it directly into a Server-Sent Events stream for a web UI.

---

## Caching

All API responses are cached in a local SQLite database (`agent/cache.db`):

| Source | Cache TTL |
|--------|-----------|
| Amazon product | 1 hour |
| Amazon reviews | 2 hours |
| YouTube | 6 hours |
| Google Shopping | 30 minutes |
| Wirecutter/RTINGS | 24 hours |
| Trustpilot | 12 hours |
| Reddit | 30 minutes |

To clear the cache: `rm agent/cache.db`

---

## Error Handling Philosophy

Every data source is **optional**. The agent never crashes because one source failed.

```
If Rainforest fails → try ScrapingDog
If ScrapingDog fails → try Camoufox
If Camoufox fails → try direct HTTP
If all fail → report 0/1 sources, lower confidence, continue with other sources
```

The only hard stop: if Amazon returns 404 (product not found), the agent stops immediately with a clear error message. Continuing with a missing product would produce garbage results.
