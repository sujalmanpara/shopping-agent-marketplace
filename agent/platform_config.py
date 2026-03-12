# platform_config.py — Configuration for all 15 platforms

PLATFORMS = {
    # ============================================
    # E-COMMERCE (Camoufox - heavy bot detection)
    # ============================================
    "amazon": {
        "scraper": "camoufox",
        "base_url": "https://www.amazon.com",
        "search_url": "https://www.amazon.com/s?k={query}",
        "timeout": 20,
        "selectors": {
            "title": "#productTitle",
            "price": ".a-price .a-offscreen",
            "rating": "[data-hook='rating-out-of-text']",
            "review_count": "#acrCustomerReviewText",
            "reviews": "[data-hook='review']",
        }
    },
    "amazon_in": {
        "scraper": "camoufox",
        "base_url": "https://www.amazon.in",
        "search_url": "https://www.amazon.in/s?k={query}",
        "timeout": 20,
        "selectors": {
            "title": "#productTitle",
            "price": ".a-price .a-offscreen",
            "rating": "[data-hook='rating-out-of-text']",
            "review_count": "#acrCustomerReviewText",
            "reviews": "[data-hook='review']",
        }
    },
    "walmart": {
        "scraper": "camoufox",
        "base_url": "https://www.walmart.com",
        "search_url": "https://www.walmart.com/search?q={query}",
        "timeout": 20,
        "selectors": {
            "product_card": "[data-item-id]",
            "title": "[data-automation-id='product-title']",
            "price": "[data-automation-id='product-price'] span",
            "rating": "[data-testid='product-ratings'] span",
        }
    },
    "target": {
        "scraper": "camoufox",
        "base_url": "https://www.target.com",
        "search_url": "https://www.target.com/s?searchTerm={query}",
        "timeout": 20,
        "selectors": {
            "product_card": "[data-test='product-card']",
            "title": "a[data-test='product-title']",
            "price": "[data-test='current-price'] span",
            "rating": "[data-test='ratings'] span",
        }
    },
    "bestbuy": {
        "scraper": "camoufox",
        "base_url": "https://www.bestbuy.com",
        "search_url": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
        "timeout": 20,
        "selectors": {
            "product_card": ".sku-item",
            "title": ".sku-title a",
            "price": ".priceView-hero-price span",
            "rating": ".c-ratings-reviews .c-stars",
        }
    },
    "flipkart": {
        "scraper": "camoufox",
        "base_url": "https://www.flipkart.com",
        "search_url": "https://www.flipkart.com/search?q={query}",
        "timeout": 20,
        "selectors": {
            "product_card": "._1AtVbE, ._1xHGtK",
            "title": "._4rR01T, .s1Q9rs, .IRpwTa",
            "price": "._30jeq3, ._1_WHN1",
            "rating": "._3LWZlK, .gUuXy-",
        }
    },
    
    # ============================================
    # SOCIAL MEDIA (Mixed)
    # ============================================
    "reddit": {
        "scraper": "scrapling",
        "base_url": "https://old.reddit.com",
        "search_url": "https://old.reddit.com/search?q={query}&sort=relevance",
        "timeout": 10,
        "selectors": {
            "post": ".thing",
            "title": ".title a",
        }
    },
    "youtube": {
        "scraper": "camoufox",
        "base_url": "https://www.youtube.com",
        "search_url": "https://www.youtube.com/results?search_query={query}+review",
        "timeout": 20,
        "selectors": {
            "video": "ytd-video-renderer",
            "title": "#video-title",
        }
    },
    "tiktok": {
        "scraper": "camoufox",  # MUST use camoufox
        "base_url": "https://www.tiktok.com",
        "search_url": "https://www.tiktok.com/search?q={query}%20review",
        "timeout": 30,
        "selectors": {
            "video": "[class*='DivItemCard']",
        }
    },
    "twitter": {
        "scraper": "camoufox",
        "base_url": "https://x.com",
        "search_url": "https://nitter.net/search?q={query}",
        "timeout": 20,
        "selectors": {
            "tweet": ".tweet-content",
        }
    },
    
    # ============================================
    # EXPERT REVIEWS (Scrapling - simple sites)
    # ============================================
    "consumer_reports": {
        "scraper": "camoufox",  # Paywall
        "base_url": "https://www.consumerreports.org",
        "search_url": "https://www.consumerreports.org/search/?query={query}",
        "timeout": 20,
        "selectors": {
            "result": ".search-result-item",
            "title": "h3, .search-result-title",
        }
    },
    "wirecutter": {
        "scraper": "scrapling",
        "base_url": "https://www.nytimes.com/wirecutter",
        "search_url": "https://www.nytimes.com/wirecutter/search/?s={query}",
        "timeout": 10,
        "selectors": {
            "result": ".SearchResults-item",
            "title": "h3, .SearchResults-title",
        }
    },
    "rtings": {
        "scraper": "scrapling",
        "base_url": "https://www.rtings.com",
        "search_url": "https://www.rtings.com/search?query={query}",
        "timeout": 10,
        "selectors": {
            "result": ".search-result",
            "title": "a, h3",
            "score": ".score, .overall-score",
        }
    },
    
    # ============================================
    # TRUST & QUALITY (Scrapling - simple sites)
    # ============================================
    "trustpilot": {
        "scraper": "scrapling",
        "base_url": "https://www.trustpilot.com",
        "search_url": "https://www.trustpilot.com/search?query={query}",
        "timeout": 10,
        "selectors": {
            "score": "[data-rating-typography]",
            "review_count": "[data-reviews-count-typography]",
        }
    },
    "fakespot": {
        "scraper": "scrapling",
        "base_url": "https://www.fakespot.com",
        "product_url": "https://www.fakespot.com/product/{asin}",
        "timeout": 10,
        "selectors": {
            "grade": ".grade-box, .review-grade",
        }
    },
    "bbb": {
        "scraper": "scrapling",
        "base_url": "https://www.bbb.org",
        "search_url": "https://www.bbb.org/search?find_text={query}",
        "timeout": 10,
        "selectors": {
            "rating": ".bds-rating",
            "accredited": ".accredited-badge",
        }
    },
}


# Scraper routing summary
CAMOUFOX_COUNT = sum(1 for p in PLATFORMS.values() if p["scraper"] == "camoufox")
SCRAPLING_COUNT = sum(1 for p in PLATFORMS.values() if p["scraper"] == "scrapling")

# Export
__all__ = ["PLATFORMS", "CAMOUFOX_COUNT", "SCRAPLING_COUNT"]
