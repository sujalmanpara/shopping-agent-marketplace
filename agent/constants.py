# constants.py — Configuration and weights for Shopping Truth Agent
# Phase 1: Clean config with API-focused architecture
# Phase 2: Added alternatives, price prediction, sale calendar constants

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
    "alternatives": 3600, # 1 hour
}

# Timeouts
SCRAPE_TIMEOUT = 15  # seconds per source
MAX_RETRIES = 2

# Analysis thresholds
FAKE_REVIEW_THRESHOLD = 40   # % suspicious reviews = high risk
MIN_REVIEWS_FOR_PERCENTAGE = 15  # Need 15+ reviews for percentage mode
MIN_REVIEWS_FOR_ANALYSIS = 5    # Need 5+ reviews to even run analysis
REGRET_SEVERITY_HIGH = 0.3   # 30% rating drop = high regret

# Phase 2: Price & alternatives
PRICE_DROP_THRESHOLD = 0.05  # 5% = meaningful drop
MAX_ALTERNATIVES = 3         # Show top 3 alternatives

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

# Sale Calendar for India and US
# Sale calendar with actual date windows (start_day, end_day per month)
# For festivals with variable dates, use the typical Amazon sale window
SALE_CALENDAR = {
    "IN": [
        {"name": "Republic Day Sale", "windows": [(1, 20, 27)], "typical_discount": "20-40%"},
        {"name": "Holi Sale", "windows": [(3, 1, 10)], "typical_discount": "10-30%"},
        {"name": "Summer Sale", "windows": [(5, 1, 10)], "typical_discount": "15-30%"},
        {"name": "Amazon Prime Day", "windows": [(7, 15, 31)], "typical_discount": "20-50%"},
        {"name": "Independence Day Sale", "windows": [(8, 5, 15)], "typical_discount": "15-35%"},
        {"name": "Amazon Great Indian Festival", "windows": [(9, 25, 30), (10, 1, 15)], "typical_discount": "30-60%"},
        {"name": "Flipkart Big Billion Days", "windows": [(9, 25, 30), (10, 1, 10)], "typical_discount": "30-60%"},
        {"name": "Diwali Sale", "windows": [(10, 15, 31)], "typical_discount": "20-50%"},
        {"name": "Year End Sale", "windows": [(12, 20, 31)], "typical_discount": "20-40%"},
    ],
    "US": [
        {"name": "Presidents' Day Sale", "windows": [(2, 14, 21)], "typical_discount": "15-30%"},
        {"name": "Memorial Day Sale", "windows": [(5, 22, 31)], "typical_discount": "15-30%"},
        {"name": "Amazon Prime Day", "windows": [(7, 10, 18)], "typical_discount": "20-50%"},
        {"name": "Back to School", "windows": [(8, 1, 15)], "typical_discount": "10-25%"},
        {"name": "Labor Day Sale", "windows": [(8, 28, 31), (9, 1, 5)], "typical_discount": "15-30%"},
        {"name": "Black Friday", "windows": [(11, 22, 30)], "typical_discount": "30-60%"},
        {"name": "Cyber Monday", "windows": [(11, 28, 30), (12, 1, 3)], "typical_discount": "20-50%"},
    ],
}
