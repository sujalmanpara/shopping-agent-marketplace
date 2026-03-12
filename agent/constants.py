# constants.py — Configuration and weights for Shopping Truth Agent
# Phase 1: Clean config with API-focused architecture

# Source weights for confidence scoring (out of 1.0, sums to 1.0)
SOURCE_WEIGHTS = {
    "amazon": 0.20,
    "reddit": 0.15,
    "youtube": 0.10,
    "keepa": 0.15,
    "google_shopping": 0.10,
    "fakespot": 0.08,
    "reviewmeta": 0.07,
    "wirecutter": 0.05,
    "rtings": 0.05,
    "trustpilot": 0.05,
}

# Cache TTLs (seconds)
CACHE_TTL = {
    "amazon": 1800,       # 30 min (prices change)
    "reddit": 7200,       # 2 hours
    "youtube": 7200,      # 2 hours
    "keepa": 3600,        # 1 hour
    "google_shopping": 1800,  # 30 min
    "fakespot": 86400,    # 24 hours
    "reviewmeta": 86400,  # 24 hours
    "wirecutter": 86400,  # 24 hours
    "rtings": 86400,      # 24 hours
    "trustpilot": 86400,  # 24 hours
}

# Timeouts
SCRAPE_TIMEOUT = 15  # seconds per source
MAX_RETRIES = 2

# Analysis thresholds
FAKE_REVIEW_THRESHOLD = 40   # % suspicious reviews = high risk
MIN_REVIEWS_FOR_PERCENTAGE = 15  # Need 15+ reviews for percentage mode
MIN_REVIEWS_FOR_ANALYSIS = 5    # Need 5+ reviews to even run analysis
REGRET_SEVERITY_HIGH = 0.3   # 30% rating drop = high regret
PRICE_DROP_THRESHOLD = 15    # 15% predicted drop = wait

# LLM config
LLM_TEMPERATURE = 0.0        # Deterministic for factual output
LLM_MAX_TOKENS = 800
DEFAULT_MODEL = "gpt-4o-mini"
MAX_CONTEXT_LENGTH = 6000    # chars to send to LLM

# URLs (APIs only — no scraping endpoints)
KEEPA_API_URL = "https://api.keepa.com/product"
REDDIT_SEARCH_URL = "https://old.reddit.com/search.json"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
SERPAPI_URL = "https://serpapi.com/search.json"
COUPON_API_BASE = "https://api.couponapi.org/v1"
