# 🏗️ Shopping Truth Agent — Architecture V2

## 13 Features. One Pipeline. 8 Seconds. 5-8 Credits.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INPUT                            │
│                                                         │
│  Mode A: Amazon URL    → "https://amazon.in/dp/B0BX..."│
│  Mode B: Compare       → "compare URL1 vs URL2"        │
│  Mode C: Visual Check  → [image attachment]             │
│  Mode D: Search        → "best headphones under 15000"  │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 ROUTER (router.py)                       │
│                                                         │
│  Detects input type → routes to correct pipeline        │
│  Extracts: ASIN, product name, brand, category          │
│  Detects: persona hints ("for my mom", "for gaming")    │
│  Cost: 0 credits (local logic)                          │
│                                                         │
└────────┬──────────┬──────────┬──────────┬───────────────┘
         │          │          │          │
    Mode A     Mode B     Mode C     Mode D
   (Analyze)  (Compare) (Visual)   (Search)
         │          │          │          │
         ▼          ▼          ▼          ▼
┌──────────────────────────────────────────────────────────┐
│                                                          │
│              DATA LAYER (api_layer.py)                    │
│                                                          │
│     All FREE APIs. No browsers. No scraping.             │
│     All calls run CONCURRENTLY (asyncio.gather)          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │           TIER 1: Product APIs (~2s)             │     │
│  │                                                  │     │
│  │  📦 Amazon PA-API                                │     │
│  │     → Product details, price, images             │     │
│  │     → Reviews (up to 10 full text)               │     │
│  │     → Q&A section                                │     │
│  │     → Offers/coupons                             │     │
│  │     → Related/similar products                   │     │
│  │     Cost: ~0.5 credits                           │     │
│  │                                                  │     │
│  │  🔍 Google Shopping API                          │     │
│  │     → Prices from ALL stores (one call!)         │     │
│  │     → Walmart, Target, BestBuy, Flipkart, eBay  │     │
│  │     → Alternative products with prices           │     │
│  │     Cost: ~0.5 credits                           │     │
│  │                                                  │     │
│  │  📈 Keepa API                                    │     │
│  │     → 6-month price history (JSON, not scraping) │     │
│  │     → Price drop alerts data                     │     │
│  │     → Sales rank history                         │     │
│  │     Cost: ~0.5 credits                           │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │          TIER 2: Community APIs (~3s)            │     │
│  │                                                  │     │
│  │  💬 Reddit (PRAW)                                │     │
│  │     → Subreddit-specific search                  │     │
│  │     → Top comments with upvotes                  │     │
│  │     → User credibility scoring                   │     │
│  │     Cost: ~0.5 credits                           │     │
│  │                                                  │     │
│  │  📺 YouTube Data API                             │     │
│  │     → Review video titles, views, likes          │     │
│  │     → Top comments from review videos            │     │
│  │     → Channel credibility (sub count)            │     │
│  │     Cost: ~0.5 credits                           │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │        TIER 3: Trust & Expert APIs (~2s)         │     │
│  │                                                  │     │
│  │  🔍 Fakespot API                                 │     │
│  │     → Review authenticity grade (A-F)            │     │
│  │     → Adjusted rating                            │     │
│  │     Cost: ~0.2 credits                           │     │
│  │                                                  │     │
│  │  📊 ReviewMeta API                               │     │
│  │     → Adjusted rating (removes fakes)            │     │
│  │     → Unnatural review patterns                  │     │
│  │     Cost: ~0.2 credits                           │     │
│  │                                                  │     │
│  │  🏆 Wirecutter (HTTP)                            │     │
│  │     → Expert pick status                         │     │
│  │     → Pros/cons summary                          │     │
│  │     Cost: ~0.1 credits                           │     │
│  │                                                  │     │
│  │  📏 RTINGS (HTTP)                                │     │
│  │     → Test scores                                │     │
│  │     → Category rankings                          │     │
│  │     Cost: ~0.1 credits                           │     │
│  │                                                  │     │
│  │  ⭐ Trustpilot API                               │     │
│  │     → Brand trust score                          │     │
│  │     → Recent complaint trends                    │     │
│  │     Cost: ~0.1 credits                           │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  Total Data Layer: ~3-5 credits | ~5-7 seconds           │
│  All tiers run IN PARALLEL                               │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Raw data from 10 sources
                         ▼
┌──────────────────────────────────────────────────────────┐
│                                                          │
│            ANALYSIS ENGINE (Local, 0 credits)            │
│                                                          │
│  All ML models run locally. No API calls. Instant.       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                                                   │    │
│  │  F2. 🔍 FAKE REVIEW DETECTOR                     │    │
│  │      Engine: XGBoost (90.2% accuracy)             │    │
│  │      Input: Amazon reviews (text)                 │    │
│  │      Output: Fake %, flagged reviews, risk level  │    │
│  │      Cross-verified with: Fakespot + ReviewMeta   │    │
│  │      Credits: 0 (local ML)                        │    │
│  │                                                   │    │
│  │  F3. 📉 PRICE PROPHET                            │    │
│  │      Engine: ARIMA time-series model              │    │
│  │      Input: Keepa price history (6 months)        │    │
│  │      Output: 30-day prediction, best buy date,    │    │
│  │              drop probability, savings estimate    │    │
│  │      Credits: 0 (local ML)                        │    │
│  │                                                   │    │
│  │  F4. 😰 REGRET DETECTOR                          │    │
│  │      Engine: Temporal sentiment analysis          │    │
│  │      Input: Reviews sorted by date                │    │
│  │      Output: Rating trajectory, quality decline,  │    │
│  │              common post-purchase complaints      │    │
│  │      Credits: 0 (local analysis)                  │    │
│  │                                                   │    │
│  │  F5. 📊 CONFIDENCE SCORER                        │    │
│  │      Engine: Weighted multi-source aggregation    │    │
│  │      Input: All 10 source results                 │    │
│  │      Output: Overall confidence %, source         │    │
│  │              agreement/contradictions             │    │
│  │      Credits: 0 (local calculation)               │    │
│  │                                                   │    │
│  │  F10. 🌍 ETHICS SCORER                           │    │
│  │       Engine: Static database + brand lookup      │    │
│  │       Input: Brand name, product category         │    │
│  │       Output: Carbon grade, labor grade,          │    │
│  │               sustainability rating               │    │
│  │       Credits: 0 (local database)                 │    │
│  │                                                   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Total Analysis Engine: 0 credits | <1 second            │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Analyzed data + ML predictions
                         ▼
┌──────────────────────────────────────────────────────────┐
│                                                          │
│           INTELLIGENCE LAYER (1 LLM call)                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                                                   │    │
│  │  F1. 🌐 MULTI-PLATFORM SYNTHESIS                 │    │
│  │      Combines all 10 sources into unified view    │    │
│  │                                                   │    │
│  │  F6. 🤖 LLM VERDICT ENGINE                       │    │
│  │      Input: ALL analyzed data (structured JSON)   │    │
│  │      Model: GPT-4o-mini (fast, cheap)             │    │
│  │      Output:                                      │    │
│  │        → BUY / WAIT / AVOID decision              │    │
│  │        → Reasoning (3-5 bullet points)            │    │
│  │        → Personalized advice (if persona given)   │    │
│  │        → Risk assessment                          │    │
│  │        → Action items ("wait 18 days", etc.)      │    │
│  │                                                   │    │
│  │  F13. 🧠 PERSONA MODE (modifier, not separate)   │    │
│  │       If persona detected in input:               │    │
│  │         "for my mom" → prioritize ease of use     │    │
│  │         "for gaming" → prioritize latency         │    │
│  │         "budget" → prioritize value               │    │
│  │       Modifies LLM prompt, costs 0 extra          │    │
│  │                                                   │    │
│  │  Credits: ~1 credit (single LLM call)             │    │
│  │                                                   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                                                          │
│            SAVINGS ENGINE (0.5 credits)                   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                                                   │    │
│  │  F7. 💰 COUPON SNIPER                            │    │
│  │      Sources: Amazon PA-API offers, CouponAPI     │    │
│  │      Output: Verified codes, clip coupons,        │    │
│  │              Subscribe & Save deals               │    │
│  │                                                   │    │
│  │  F8. 🔄 ALTERNATIVE FINDER                       │    │
│  │      Source: Google Shopping results               │    │
│  │      Output: Top 3 alternatives with              │    │
│  │              price comparison & why they're better │    │
│  │                                                   │    │
│  │  F9. 💳 CARD + CASHBACK OPTIMIZER                │    │
│  │      Source: Local database (15 cards)             │    │
│  │      Output: Best card, cashback platform,        │    │
│  │              BEST COMBO (stacking strategy)        │    │
│  │                                                   │    │
│  │  Credits: ~0.5 (API portion only)                 │    │
│  │                                                   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                                                          │
│             OUTPUT FORMATTER (formatter.py)               │
│                                                          │
│  Takes ALL results → produces beautiful output           │
│  Format adapts to: Marketplace UI / Telegram / API       │
│  Credits: 0 (local formatting)                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Special Modes (On-Demand, Extra Credits)

### Mode B: Head-to-Head Compare (Feature 11)

```
┌───────────────────────────────────────────┐
│  F11. 🆚 HEAD-TO-HEAD BATTLE             │
│                                           │
│  User: "compare URL1 vs URL2 vs URL3"    │
│                                           │
│  Runs FULL pipeline for each product      │
│  Then adds comparison layer:              │
│                                           │
│  Product A ──┐                            │
│  Product B ──┼──→ COMPARATOR ──→ Output   │
│  Product C ──┘    (LLM call)              │
│                                           │
│  Credits: 5-8 per product × N products    │
│         + 1 credit comparison LLM         │
│                                           │
│  Example: 2 products = ~12-17 credits     │
│           3 products = ~18-25 credits     │
│                                           │
│  Shows: Side-by-side table                │
│         Winner per category               │
│         Overall recommendation            │
│         "Best for YOU" based on persona   │
│                                           │
└───────────────────────────────────────────┘
```

### Mode C: Visual Lie Detector (Feature 12)

```
┌───────────────────────────────────────────┐
│  F12. 📸 VISUAL LIE DETECTOR             │
│                                           │
│  User: sends product image from ad/social │
│                                           │
│  Image ──→ Google Lens/Vision API         │
│        ──→ Identify product               │
│        ──→ Find real listing              │
│        ──→ Run FULL pipeline on it        │
│                                           │
│  Credits: ~1 (image recognition)          │
│         + 5-8 (full analysis)             │
│         = ~7-10 total                     │
│                                           │
│  Output:                                  │
│    "This is: Sony WH-1000XM5"            │
│    "Advertised at: ₹29,999 (FAKE!)"      │
│    "Real price: ₹24,990 on Amazon"       │
│    "Best price: ₹19,990 (wait 18 days)"  │
│    + Full 10-feature analysis             │
│                                           │
└───────────────────────────────────────────┘
```

---

## Feature-to-Source Mapping

```
Feature                  │ Data Sources Used           │ Credits │ Local?
─────────────────────────┼─────────────────────────────┼─────────┼────────
F1.  Multi-Platform      │ ALL 10 sources              │ ~4      │ No
F2.  Fake Review Det.    │ Amazon reviews + ML model   │ 0       │ ✅ Yes
F3.  Price Prophet       │ Keepa API + ARIMA model     │ ~0.5    │ Partial
F4.  Regret Detector     │ Amazon reviews (dated)      │ 0       │ ✅ Yes
F5.  Confidence Score    │ All source results          │ 0       │ ✅ Yes
F6.  LLM Verdict         │ GPT-4o-mini                 │ ~1      │ No
F7.  Coupon Sniper       │ Amazon PA-API + CouponAPI   │ ~0.5    │ Partial
F8.  Alternative Finder  │ Google Shopping API          │ ~0.5    │ No
F9.  Card Optimizer      │ Local database              │ 0       │ ✅ Yes
F10. Ethics Score        │ Local database              │ 0       │ ✅ Yes
F11. Head-to-Head        │ Full pipeline × N           │ ~12-25  │ No
F12. Visual Detector     │ Vision API + Full pipeline  │ ~7-10   │ No
F13. Persona Mode        │ LLM prompt modifier         │ 0       │ ✅ Yes
─────────────────────────┼─────────────────────────────┼─────────┼────────
TOTAL (single product)   │                             │ ~5-8    │ 6 local
```

---

## Execution Flow (Single Product Analysis)

```
Time    Action                              Credits   Parallel?
────────────────────────────────────────────────────────────────
0.0s    Router: Parse input, extract ASIN     0       -
0.1s    ┌─ Amazon PA-API call                 0.5     ┐
0.1s    ├─ Google Shopping API call           0.5     │
0.1s    ├─ Keepa API call                     0.5     │
0.1s    ├─ Reddit (PRAW) call                 0.5     ├─ ALL
0.1s    ├─ YouTube Data API call              0.5     │  PARALLEL
0.1s    ├─ Fakespot API call                  0.2     │
0.1s    ├─ ReviewMeta API call                0.2     │
0.1s    ├─ Wirecutter HTTP call               0.1     │
0.1s    ├─ RTINGS HTTP call                   0.1     │
0.1s    └─ Trustpilot API call                0.1     ┘
                                              ───
5.0s    All API responses received            ~3.2 credits

5.0s    ┌─ Fake Review Detection (XGBoost)    0       ┐
5.0s    ├─ Price Prediction (ARIMA)           0       │
5.0s    ├─ Regret Detection                   0       ├─ ALL
5.0s    ├─ Confidence Scoring                 0       │  PARALLEL
5.0s    └─ Ethics Scoring                     0       ┘
                                              ───
5.5s    All ML analysis complete              0 credits

5.5s    ┌─ LLM Verdict (GPT-4o-mini)         ~1      ┐
5.5s    ├─ Coupon lookup (CouponAPI)          ~0.5    ├─ PARALLEL
5.5s    └─ Card matching (local)              0       ┘
                                              ───
7.5s    Intelligence + Savings complete       ~1.5 credits

7.5s    Output formatting                     0
                                              ───
8.0s    ✅ DONE!                              

TOTAL: ~5-7 credits | ~8 seconds
```

---

## File Structure

```
agent/
│
├── router.py                 # INPUT: Detects mode (URL/compare/image/search)
│                              # Extracts: ASIN, product name, brand, persona
│
├── api_layer.py              # DATA: Central API client for all 10 sources
│   ├── amazon_api.py         #   Amazon PA-API wrapper
│   ├── google_shopping.py    #   Google Shopping API wrapper
│   ├── keepa_api.py          #   Keepa API wrapper  
│   ├── reddit_api.py         #   Reddit PRAW wrapper
│   ├── youtube_api.py        #   YouTube Data API wrapper
│   ├── fakespot_api.py       #   Fakespot API wrapper
│   ├── reviewmeta_api.py     #   ReviewMeta API wrapper
│   ├── trustpilot_api.py     #   Trustpilot API wrapper
│   └── http_scrapers.py      #   Wirecutter + RTINGS (lightweight HTTP)
│
├── analyzers/                # ANALYSIS: All local ML models
│   ├── fake_detector.py      #   F2: XGBoost fake review detection
│   ├── price_predictor.py    #   F3: ARIMA price prediction
│   ├── regret_detector.py    #   F4: Temporal sentiment analysis
│   ├── confidence_scorer.py  #   F5: Multi-source confidence
│   └── ethics_scorer.py      #   F10: Carbon + labor grades
│
├── intelligence/             # INTELLIGENCE: LLM-powered features
│   ├── verdict_engine.py     #   F6: BUY/WAIT/AVOID + reasoning
│   ├── persona_engine.py     #   F13: Persona detection + prompt modifier
│   └── comparator.py         #   F11: Head-to-head comparison logic
│
├── savings/                  # SAVINGS: Money-saving features
│   ├── coupon_sniper.py      #   F7: Coupon finding + verification
│   ├── alternative_finder.py #   F8: Better product alternatives
│   └── card_optimizer.py     #   F9: Credit card + cashback stacking
│
├── special/                  # SPECIAL MODES
│   ├── visual_detector.py    #   F12: Image → product identification
│   └── search_mode.py        #   Mode D: Natural language search
│
├── models/                   # ML model files
│   ├── fake_review_model.joblib
│   └── feature_pipeline.joblib
│
├── data/                     # Static databases
│   ├── credit_cards.json     #   15 cards (US + India)
│   ├── cashback_platforms.json
│   ├── ethics_database.json  #   Brand ethics scores
│   └── sale_calendar.json    #   Major sale dates
│
├── formatter.py              # OUTPUT: Beautiful formatted results
├── executor.py               # ORCHESTRATOR: Runs full pipeline
├── manifest.json             # Agent metadata for marketplace
├── constants.py              # Config, thresholds, weights
└── SKILL.md                  # OpenClaw integration guide
```

---

## API Keys Required (All FREE)

| API | Free Tier | Rate Limit | Key Needed |
|-----|-----------|------------|------------|
| Amazon PA-API | Free with Associates | 1 req/sec | ✅ User provides |
| Google Shopping | Free tier | 100/day | ✅ User provides |
| Keepa API | Free tier | 100/day | ✅ User provides |
| Reddit (PRAW) | Free | 60 req/min | ✅ User provides |
| YouTube Data | 10K units/day | 100/sec | ✅ User provides |
| Fakespot | Free | Unknown | ✅ Auto |
| ReviewMeta | Free | Unknown | ✅ Auto |
| Wirecutter | No API (HTTP) | Respectful | ❌ None |
| RTINGS | No API (HTTP) | Respectful | ❌ None |
| Trustpilot | Free tier | 100/day | ✅ Auto |
| OpenAI (LLM) | Pay-per-use | Standard | ✅ User provides |
| Google Vision | Free tier 1K/mo | Standard | ✅ User provides |

**User only needs:** OpenAI key (required) + Amazon Associates (recommended)
**Everything else:** Free or auto-configured

---

## Credit Budget Per Mode

| Mode | Features Used | Credits | Time |
|------|--------------|---------|------|
| A: Single Product | All 13 | 5-8 | ~8s |
| B: Compare 2 | All × 2 + comparator | 12-17 | ~15s |
| B: Compare 3 | All × 3 + comparator | 18-25 | ~20s |
| C: Visual Check | Vision + All 13 | 7-10 | ~12s |
| D: Search | Search + top 3 analysis | 18-25 | ~25s |

---

## Quality Targets

| Feature | Current Score | Target | Method |
|---------|--------------|--------|--------|
| F1. Multi-Platform | 6.0/10 | 9.5/10 | API rewrite |
| F2. Fake Reviews | 9.2/10 | 9.5/10 | Add Fakespot + ReviewMeta cross-check |
| F3. Price Prophet | 7.5/10 | 9.3/10 | Keepa API (real data!) |
| F4. Regret Detector | 5.0/10 | 8.5/10 | Better temporal analysis |
| F5. Confidence | 5.0/10 | 9.0/10 | Dynamic multi-source weighting |
| F6. LLM Verdict | 5.0/10 | 9.5/10 | Structured prompt + persona |
| F7. Coupon Sniper | 9.0/10 | 9.5/10 | API-based verification |
| F8. Alternatives | 5.0/10 | 9.0/10 | Google Shopping |
| F9. Card Optimizer | 9.0/10 | 9.2/10 | Dynamic cashback rates |
| F10. Ethics | 5.0/10 | 8.0/10 | Expanded brand DB |
| F11. Head-to-Head | NEW | 9.0/10 | Comparator engine |
| F12. Visual Detect | NEW | 8.5/10 | Google Vision API |
| F13. Persona Mode | NEW | 9.0/10 | LLM prompt engineering |
| **AVERAGE** | **6.4** | **9.0** | **+2.6 improvement** |

---

*Architecture V2 — March 12, 2026*
*Shopping Truth Agent — Sam + Assistant*
