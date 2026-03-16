<div align="center">

# 🛒 Shopping Truth Agent

### The AI That Tells You What Amazon Won't

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**Paste any Amazon link. Get the truth in under 10 seconds.**

Fake reviews detected. Real prices compared. Expert opinions gathered. AI verdict delivered.

<br/>

<img src="https://img.shields.io/badge/⏱️_Average_Response-5--12s-green?style=for-the-badge" />
<img src="https://img.shields.io/badge/📊_Data_Sources-10+-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/💰_Needs-1_LLM_Key-orange?style=for-the-badge" />

<br/><br/>

[Quick Start](#-quick-start) · [How It Works](#-how-it-works) · [Features](#-what-you-get) · [API Keys](#-api-keys--optional-upgrades) · [Sample Output](#-sample-output)

</div>

---

## 💡 The Problem

> **61% of Amazon reviews are fake.** You know it. We know it. But you still buy based on them.

Every product page tells you the same story: ⭐⭐⭐⭐⭐ "Great product!" — posted by accounts that reviewed 47 products in one day.

**Shopping Truth Agent fixes this.** It pulls data from **10+ independent sources**, runs fake review detection, compares prices across stores, finds coupons, and gives you an honest **BUY / WAIT / AVOID** verdict.

---

## ⚡ Quick Start

```bash
git clone https://github.com/sujalmanpara/shopping-agent-marketplace.git
cd shopping-agent-marketplace
pip install -r requirements.txt
```

**Minimum setup — just ONE LLM key required:**
```bash
# .env file — only one LLM key is required to get started
OPENAI_API_KEY=sk-your-key-here
# Or use: ANTHROPIC_API_KEY / GEMINI_API_KEY / GROK_API_KEY / OPENROUTER_API_KEY
```

**Run it:**
```python
import asyncio
from agent.executor import execute

async def main():
    keys = {"OPENAI_API_KEY": "sk-your-key"}
    async for event in execute("https://www.amazon.in/dp/B09R4SF5SP", keys):
        if event["event"] == "status":
            print(event["data"])
        elif event["event"] == "result":
            print(event["data"])

asyncio.run(main())
```

**That's it.** No complex setup. No 10 API keys to configure. Just paste a link and get the truth.

---

## 🔍 How It Works

```
📎 Paste Amazon Link
        │
        ▼
┌─────────────────────────────────────────┐
│  🔄 Parallel Data Collection (3-8s)     │
│                                         │
│  Amazon Product Page ──► Price, specs   │
│  Rating Widget ────────► 2000+ ratings  │
│  YouTube ──────────────► Video reviews  │
│  Google Shopping ──────► Price compare  │
│  Wirecutter ───────────► Expert picks   │
│  RTINGS ───────────────► Lab-tested     │
│  Trustpilot ───────────► Brand trust    │
│  Reddit ───────────────► Real opinions  │
│  Keepa ────────────────► Price history  │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│  🧠 AI Analysis (<2s)                   │
│                                         │
│  Fake Review Detection (star patterns)  │
│  Price Benchmarking (vs category avg)   │
│  Review Quality Scoring                 │
│  Timeline Analysis (organic vs fake)    │
│  Coupon & Cashback Finder               │
│  Alternative Product Search             │
└─────────────────────────────────────────┘
        │
        ▼
   🎯 BUY / WAIT / AVOID
```

**Total time: 5-15 seconds** depending on your connection.

---

## 🎁 What You Get

### 📦 Product Intelligence
- **Price with context** — Is ₹24,990 a good price? Agent tells you it's 10% below category average.
- **Star distribution analysis** — A J-shaped curve (90% 5-star + 10% 1-star) = fake farm. Natural products have a bell curve.
- **Review quality scoring** — Detailed reviews vs one-liners. Verified purchases vs unverified.

### 🕵️ Fake Review Detection
- **Star distribution analysis** from 2,000+ ratings (not just the 8 reviews on the page)
- **J-score metric** — detects the signature pattern of paid review farms
- **Review timeline analysis** — organic products gain reviews steadily, fakes get 500 reviews in one week
- **Keyword flagging** — detects generic praise patterns

### 💰 Price Intelligence
- **Cross-store comparison** — Same product on Amazon, Flipkart, brand stores, and 5+ retailers
- **Category benchmarking** — "This AC costs 10% less than similar models"
- **Best deal calculator** — Combines cashback + credit card rewards for actual lowest price
- **Price history** — Was it cheaper last month? (with Keepa API key)

### 💳 Savings Engine
- **Cashback platforms** — CashKaro, Magicpin, Amazon Pay
- **Credit card rewards** — ICICI Amazon Pay (5%), HDFC Millennia (5%), Axis Flipkart (5%)
- **UPI cashback** — Amazon Pay UPI deals
- **Coupon codes** — Automatically discovered from multiple sources

### 📺 Expert & Community Reviews
- **YouTube** — Top video reviews with view counts
- **Wirecutter** — New York Times expert picks
- **RTINGS** — Lab-tested ratings for electronics
- **Trustpilot** — Brand reputation scores
- **Reddit** — Real user experiences (with API key)

### 🤖 AI Verdict
Clear, actionable advice powered by your choice of LLM:
- **BUY** ✅ — Good product, fair price, real reviews
- **WAIT** ⏳ — Price drop expected or better alternative exists
- **AVOID** 🚫 — Fake reviews, overpriced, or quality issues

---

## 🔑 API Keys — Optional Upgrades

The agent works with **just ONE key** (any LLM provider). Everything else is optional.

| Key | What It Adds | Free Tier | Cost |
|-----|-------------|-----------|------|
| **LLM Key** (Required) | AI verdicts & summaries | — | Varies |
| `OPENAI_API_KEY` | GPT-4 verdicts | Pay-per-use | ~$0.01/query |
| `ANTHROPIC_API_KEY` | Claude verdicts | Pay-per-use | ~$0.01/query |
| `GEMINI_API_KEY` | Gemini verdicts | Free tier! | Free |
| `GROK_API_KEY` | Grok verdicts | Pay-per-use | ~$0.01/query |
| | | | |
| **Optional — Data Sources** | | | |
| `YOUTUBE_API_KEY` | Better video results | Free (10K/day) | Free |
| `SERPAPI_KEY` | Google Shopping prices | 100 free/mo | $50/mo |
| `RAINFOREST_API_KEY` | 100+ Amazon reviews | — | $80/mo |
| `SCRAPINGDOG_API_KEY` | Bulk Amazon reviews | 1,000 free/mo | $30/mo |
| `KEEPA_API_KEY` | Price history graphs | — | €19/mo |
| `REDDIT_CLIENT_ID` | Reddit discussions | Free | Free |
| `REDDIT_CLIENT_SECRET` | Reddit discussions | Free | Free |

### Without any optional keys, you still get:
✅ Amazon product data (via stealth browser)
✅ Star distribution from 2,000+ ratings
✅ YouTube video reviews
✅ Google Shopping prices (from residential IPs)
✅ Wirecutter expert reviews
✅ RTINGS lab-tested scores
✅ Trustpilot brand trust
✅ Fake review detection
✅ Price benchmarking
✅ Coupon & cashback finder
✅ AI verdict

---

## 📸 Sample Output

```
╔══════════════════════════════════════════════════╗
║          🛒  SHOPPING TRUTH AGENT  v2.0         ║
╚══════════════════════════════════════════════════╝

  📦 Daikin 0.8 Ton 3 Star Split AC
  🏷️  DAIKIN

  💰 ₹24,990     ★★★★☆ 4.1/5     📝 2,265 reviews

  ┌────────────────────────────────┐
  │  ✅  VERDICT:     GO FOR IT   │
  └────────────────────────────────┘

  Trust  ██████░░░░  64%    Fake Risk: 🟡 LIMITED    Sources: 6/8

  ╭─── 💲 PRICE CHECK ───────────────────────────╮
  │  🟢 Good price — 10% below average            │
  │  Category avg: ₹27,713 • You: ₹24,990 (-10%) │
  │  Compared across 10 similar products           │
  ╰───────────────────────────────────────────────╯

  ╭─── 🏆 YOUR BEST DEAL ──────────────────────────╮
  │  CashKaro + ICICI Amazon Pay Card               │
  │  Original:  ₹24,990                             │
  │  You pay:   ₹23,241  💚 SAVE ₹1,749 (7.0% off) │
  ╰───────────────────────────────────────────────╯

  ⭐ STAR DISTRIBUTION (from 2,265 ratings)
  5★ ████████████░░░░░░░░ 61%
  4★ ███░░░░░░░░░░░░░░░░░ 18%
  3★ █░░░░░░░░░░░░░░░░░░░  6%
  2★ ░░░░░░░░░░░░░░░░░░░░  3%
  1★ ██░░░░░░░░░░░░░░░░░░ 12%
  ✅ Natural distribution — not a fake farm

  📺 TOP VIDEO REVIEWS
  🎬 Daikin 0.8T AC Unboxing — 109K views
  🎬 Daikin FTL28TV Review  — 94K views

  🛍️ ALTERNATIVES
  1. Lloyd 0.8T 3★ Inverter — ₹23,990 (4% cheaper)
  2. Daikin via Better Home  — ₹25,989
  3. Havells Classic 0.8T    — ₹29,490

  🔍 CROSS-STORE PRICES
  Amazon.in:       ₹24,990 🏆
  TheACWala:       ₹24,990
  Ankur Electric:  ₹25,499
  Tradexact:       ₹25,800
  Better Home:     ₹25,989

  💳 SAVINGS
  • CashKaro: 2-6% cashback
  • ICICI Amazon Pay Card: 5% back for Prime 🔥
  • HDFC Millennia: 5% on Amazon via SmartBuy
  • Amazon Pay UPI: Up to 10% during sales

  🤖 AI VERDICT: BUY
  Wirecutter Top Pick with 4.1★ from 2,265 reviews.
  Price is 10% below average. Consider Lloyd for 4% savings.
  Trustpilot score: 4.9/5. Reliable choice.

  📊 SOURCES: ✅ Amazon │ ✅ YouTube │ ✅ Google Shopping
              ✅ Wirecutter │ ✅ RTINGS │ ✅ Trustpilot
```

---

## 🏗 Architecture

```
shopping-agent-marketplace/
├── agent/
│   ├── executor.py          # Main orchestrator — SSE streaming
│   ├── api_layer.py         # 10+ data sources with tiered fallbacks
│   ├── analyzers.py         # Fake detection, star analysis, quality scoring
│   ├── summarizer.py        # Beautiful terminal output formatter
│   ├── price_predictor_arima.py  # ARIMA-based price prediction
│   └── coupon_sniper.py     # Coupon & cashback discovery
├── .env                     # Your API keys (gitignored)
├── requirements.txt         # Python dependencies
└── README.md
```

### Data Source Priority (Auto-Fallback)

Every source has a **tiered fallback chain** — the agent tries the best method first and degrades gracefully:

```
Amazon Product Data:
  Tier 1: Rainforest API (best quality)
  Tier 2: ScrapingDog API
  Tier 3: Camoufox stealth browser
  Tier 4: Direct HTTP with headers

Amazon Reviews:
  Tier 1: Rainforest Reviews API (100+ reviews)
  Tier 2: ScrapingDog Reviews API
  Tier 3: Product page scrape (8 reviews)

Star Distribution:
  → Amazon Rating Widget (FREE, no auth, 2000+ ratings!)

Google Shopping:
  Tier 1: SerpAPI (structured data)
  Tier 2: Camoufox Google scrape (residential IPs)

YouTube:
  Tier 1: YouTube Data API v3
  Tier 2: YouTube search page scrape

Everything else:
  → Direct HTTP (always free)
```

---

## 🌍 Supported Marketplaces

| Marketplace | Product Data | Reviews | Price Compare |
|-------------|:----------:|:-------:|:------------:|
| 🇮🇳 Amazon.in | ✅ | ✅ | ✅ |
| 🇺🇸 Amazon.com | ✅ | ✅ | ✅ |
| 🇬🇧 Amazon.co.uk | 🔜 | 🔜 | 🔜 |
| 🇩🇪 Amazon.de | 🔜 | 🔜 | 🔜 |
| More coming | — | — | — |

---

## 🔒 Privacy & Security

- **Your keys stay local** — never sent anywhere except the API providers you configure
- **No tracking** — zero analytics, zero telemetry
- **No data stored** — results are cached locally for performance only
- **Open source** — audit every line of code yourself

---

## 🚀 Roadmap

- [x] Multi-source data aggregation (10+ sources)
- [x] Fake review detection (star distribution + keyword analysis)
- [x] Price comparison across stores
- [x] Coupon & cashback discovery
- [x] YouTube video reviews
- [x] Expert reviews (Wirecutter, RTINGS)
- [x] AI verdict with confidence scoring
- [x] Zero API key mode (works out of the box)
- [x] Tiered fallback for every data source
- [ ] Price drop prediction (ARIMA model)
- [ ] Browser extension (Chrome/Firefox)
- [ ] Flipkart support
- [ ] Battle Mode (two AIs debate pros/cons)
- [ ] Telegram bot integration
- [ ] Historical price alerts

---

## 🤝 Contributing

Contributions welcome! Open an issue first to discuss what you'd like to change.

```bash
git clone https://github.com/sujalmanpara/shopping-agent-marketplace.git
cd shopping-agent-marketplace
pip install -r requirements.txt
# Make your changes
# Submit a PR
```

---

## 📄 License

MIT License — use it however you want. Attribution appreciated but not required.

---

<div align="center">

### ⭐ If this saved you from a bad purchase, star the repo!

**[⭐ Star](https://github.com/sujalmanpara/shopping-agent-marketplace)** · **[🐛 Report Bug](https://github.com/sujalmanpara/shopping-agent-marketplace/issues)** · **[💡 Request Feature](https://github.com/sujalmanpara/shopping-agent-marketplace/issues)**

Built by [@sujalmanpara](https://github.com/sujalmanpara)

</div>
