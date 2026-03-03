# constants.py — Configuration and weights

# Source confidence weights (must sum to 100)
SOURCE_WEIGHTS = {
    "reddit": 30,
    "youtube": 25,
    "twitter": 20,
    "amazon_qa": 15,
    "google_reviews": 10,
}

# Timeouts
SCRAPE_TIMEOUT = 15  # seconds per source
MAX_RETRIES = 2

# Rate limiting (to avoid bot detection)
REQUEST_DELAY = 2  # seconds between requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]

# URLs
KEEPA_GRAPH_URL = "https://graph.keepa.com/pricehistory.png"
NITTER_INSTANCE = "https://nitter.net"
REDDIT_OLD = "https://old.reddit.com"

# Analysis thresholds
FAKE_REVIEW_THRESHOLD = 40  # % suspicious reviews = high risk
REGRET_SEVERITY_HIGH = 0.3  # 30% rating drop = high regret
PRICE_DROP_THRESHOLD = 15  # 15% predicted drop = wait

# LLM parameters
DEFAULT_TEMPERATURE = 0.3
MAX_CONTEXT_LENGTH = 6000  # chars to send to LLM
