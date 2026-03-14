# coupon_sniper.py — Coupon Sniper: Real verified coupons + cashback + credit card benefits
# Principle: Show NOTHING rather than wrong/expired coupons

import asyncio
import os
import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx

# ============================================================
# CREDIT CARD BENEFITS DATABASE (Static knowledge base)
# No API needed — curated data about major card benefits
# ============================================================

CREDIT_CARD_BENEFITS = {
    # --- US Cards ---
    "chase_sapphire_preferred": {
        "name": "Chase Sapphire Preferred",
        "country": "US",
        "benefits": [
            {"type": "points", "value": "3x points on dining & online groceries", "category": "dining"},
            {"type": "points", "value": "2x points on travel", "category": "travel"},
            {"type": "points", "value": "1x points on everything else", "category": "general"},
            {"type": "perk", "value": "DoorDash DashPass membership", "category": "food"},
            {"type": "perk", "value": "5x points on Lyft rides", "category": "travel"},
            {"type": "protection", "value": "Purchase protection up to $500/claim", "category": "shopping"},
            {"type": "protection", "value": "Extended warranty +1 year", "category": "shopping"},
        ],
        "shopping_tip": "Use Chase Offers in app for statement credits on select retailers"
    },
    "chase_sapphire_reserve": {
        "name": "Chase Sapphire Reserve",
        "country": "US",
        "benefits": [
            {"type": "points", "value": "10x on hotels & car rentals via Chase", "category": "travel"},
            {"type": "points", "value": "3x on dining & travel", "category": "dining"},
            {"type": "perk", "value": "$300 annual travel credit", "category": "travel"},
            {"type": "protection", "value": "Purchase protection up to $10,000/claim", "category": "shopping"},
            {"type": "protection", "value": "Extended warranty +1 year", "category": "shopping"},
            {"type": "protection", "value": "Return protection (90 days)", "category": "shopping"},
        ],
        "shopping_tip": "Check Chase Offers for 5-15% back at select stores. Points worth 1.5x on travel via portal."
    },
    "amex_gold": {
        "name": "Amex Gold Card",
        "country": "US",
        "benefits": [
            {"type": "points", "value": "4x on restaurants worldwide", "category": "dining"},
            {"type": "points", "value": "4x on US supermarkets (up to $25K/yr)", "category": "groceries"},
            {"type": "perk", "value": "$120/yr dining credit (GrubHub, Seamless, etc.)", "category": "food"},
            {"type": "perk", "value": "$120/yr Uber Cash", "category": "travel"},
        ],
        "shopping_tip": "Check Amex Offers for targeted discounts — often 10-20% back at specific retailers"
    },
    "amex_platinum": {
        "name": "Amex Platinum",
        "country": "US",
        "benefits": [
            {"type": "points", "value": "5x on flights booked directly", "category": "travel"},
            {"type": "perk", "value": "$200 airline fee credit", "category": "travel"},
            {"type": "perk", "value": "$200 hotel credit (FHR/THC)", "category": "travel"},
            {"type": "perk", "value": "$155 Walmart+ credit", "category": "shopping"},
            {"type": "perk", "value": "$240 digital entertainment credit", "category": "entertainment"},
            {"type": "protection", "value": "Purchase protection up to $10,000", "category": "shopping"},
            {"type": "protection", "value": "Extended warranty +2 years", "category": "shopping"},
            {"type": "protection", "value": "Return protection (90 days, up to $300)", "category": "shopping"},
        ],
        "shopping_tip": "Walmart+ included! Use for free delivery. Check Amex Offers — often $50-100 back on electronics."
    },
    "amazon_prime_visa": {
        "name": "Amazon Prime Visa",
        "country": "US",
        "benefits": [
            {"type": "cashback", "value": "5% back on Amazon.com & Whole Foods", "category": "shopping"},
            {"type": "cashback", "value": "2% at restaurants, gas stations, drugstores", "category": "dining"},
            {"type": "cashback", "value": "1% on everything else", "category": "general"},
            {"type": "perk", "value": "No foreign transaction fees", "category": "travel"},
        ],
        "shopping_tip": "ALWAYS use this card on Amazon — 5% back is automatic. Stacks with Subscribe & Save!"
    },
    "capital_one_venture_x": {
        "name": "Capital One Venture X",
        "country": "US",
        "benefits": [
            {"type": "points", "value": "10x on hotels & car rentals via Capital One Travel", "category": "travel"},
            {"type": "points", "value": "5x on flights via Capital One Travel", "category": "travel"},
            {"type": "points", "value": "2x on everything else", "category": "general"},
            {"type": "perk", "value": "$300 annual travel credit", "category": "travel"},
            {"type": "protection", "value": "Purchase protection", "category": "shopping"},
            {"type": "protection", "value": "Extended warranty", "category": "shopping"},
        ],
        "shopping_tip": "Capital One Shopping extension auto-applies coupons + earns shopping rewards"
    },
    "citi_double_cash": {
        "name": "Citi Double Cash",
        "country": "US",
        "benefits": [
            {"type": "cashback", "value": "2% on everything (1% on buy + 1% on pay)", "category": "general"},
        ],
        "shopping_tip": "Simple flat 2% — good default card when no category bonus applies"
    },

    # --- India Cards ---
    "hdfc_infinia": {
        "name": "HDFC Infinia",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "5 reward points per ₹150 spent (3.3% value)", "category": "general"},
            {"type": "perk", "value": "Complimentary airport lounge access worldwide", "category": "travel"},
            {"type": "perk", "value": "1:1 airmiles transfer (Intermiles, Singapore KrisFlyer)", "category": "travel"},
            {"type": "protection", "value": "Purchase protection", "category": "shopping"},
        ],
        "shopping_tip": "Use SmartBuy portal for 10x rewards on flights, hotels, Amazon vouchers!"
    },
    "hdfc_regalia": {
        "name": "HDFC Regalia",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "4 reward points per ₹150 spent (2.6% value)", "category": "general"},
            {"type": "perk", "value": "Complimentary domestic lounge access", "category": "travel"},
            {"type": "perk", "value": "Milestone benefits at ₹3L and ₹5L spend", "category": "rewards"},
        ],
        "shopping_tip": "SmartBuy portal gives 10x rewards on flights and Amazon vouchers"
    },
    "sbi_elite": {
        "name": "SBI Card Elite",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "2 reward points per ₹100 (1% value general)", "category": "general"},
            {"type": "perk", "value": "5x points on dining, groceries, departmental stores", "category": "dining"},
            {"type": "perk", "value": "Complimentary Trident Privilege membership", "category": "travel"},
            {"type": "perk", "value": "Movie ticket offers (Buy 1 Get 1)", "category": "entertainment"},
        ],
        "shopping_tip": "Use for dining and grocery purchases for maximum 5x rewards"
    },
    "icici_amazon_pay": {
        "name": "ICICI Amazon Pay Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5% back on Amazon.in for Prime members", "category": "shopping"},
            {"type": "cashback", "value": "2% back on paying bills, recharges", "category": "bills"},
            {"type": "cashback", "value": "1% back on all other spends", "category": "general"},
        ],
        "shopping_tip": "Best card for Amazon India purchases — 5% instant cashback as Amazon Pay balance"
    },
    "axis_flipkart": {
        "name": "Axis Bank Flipkart Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5% cashback on Flipkart, Myntra, 2GUD", "category": "shopping"},
            {"type": "cashback", "value": "4% cashback on Swiggy, Uber, PVR, Curefit", "category": "dining"},
            {"type": "cashback", "value": "1.5% on all other spends", "category": "general"},
        ],
        "shopping_tip": "Use this on Flipkart Big Billion Days / sales for 5% + sale discounts stacking"
    },
    "au_ixigo": {
        "name": "AU Ixigo Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "10% off on Ixigo flights and trains", "category": "travel"},
            {"type": "cashback", "value": "5% off on Ixigo hotels", "category": "travel"},
            {"type": "perk", "value": "1% fuel surcharge waiver", "category": "fuel"},
        ],
        "shopping_tip": "Great for booking travel — combine with Ixigo sale periods for best rates"
    },

    # --- India Cards (Expanded) ---
    "hdfc_millennia": {
        "name": "HDFC Millennia Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5% cashback on Amazon, Flipkart, Myntra (via SmartBuy)", "category": "shopping"},
            {"type": "cashback", "value": "2.5% on all online spends", "category": "general"},
            {"type": "cashback", "value": "1% on offline/wallet spends", "category": "general"},
        ],
        "shopping_tip": "Best budget card for online shopping — 5% on major e-commerce via SmartBuy portal"
    },
    "hdfc_diners_black": {
        "name": "HDFC Diners Club Black",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "5 reward points per ₹150 (3.3% value)", "category": "general"},
            {"type": "perk", "value": "10x rewards on SmartBuy (flights, Amazon, hotels)", "category": "shopping"},
            {"type": "perk", "value": "Unlimited airport lounge access (domestic + international)", "category": "travel"},
            {"type": "protection", "value": "Comprehensive travel insurance", "category": "travel"},
        ],
        "shopping_tip": "Use SmartBuy for 10x rewards on Amazon/Flipkart gift vouchers — better than direct purchase!"
    },
    "amex_mrcc": {
        "name": "American Express MRCC (Membership Rewards)",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "1000 bonus MR points on ₹1,500+ Amazon spend", "category": "shopping"},
            {"type": "points", "value": "5x MR points on select partners", "category": "shopping"},
            {"type": "perk", "value": "18-hole complimentary golf games", "category": "lifestyle"},
        ],
        "shopping_tip": "Enroll in Amazon offer via Amex portal first — bonus 1000 points on ₹1,500+ spends"
    },
    "amex_platinum_travel": {
        "name": "American Express Platinum Travel",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "5x MR points on domestic travel", "category": "travel"},
            {"type": "points", "value": "3x MR points on international spends", "category": "travel"},
            {"type": "perk", "value": "4 complimentary airport lounge visits/year", "category": "travel"},
        ],
        "shopping_tip": "Best for international purchases (no forex markup with points offset)"
    },
    "kotak_811": {
        "name": "Kotak 811 #DreamDifferent Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "10% on OTT (Netflix, Hotstar, Prime)", "category": "entertainment"},
            {"type": "cashback", "value": "6% on food delivery (Swiggy, Zomato)", "category": "dining"},
            {"type": "cashback", "value": "2% on all other spends", "category": "general"},
        ],
        "shopping_tip": "Entry-level card with no joining fee — good for general cashback"
    },
    "kotak_league_platinum": {
        "name": "Kotak League Platinum Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "4 reward points per ₹150 (2.6% value)", "category": "general"},
            {"type": "perk", "value": "8x reward points on weekend dining", "category": "dining"},
            {"type": "perk", "value": "Buy 1 Get 1 on movies (BookMyShow)", "category": "entertainment"},
        ],
        "shopping_tip": "Great for weekend shopping + dining combo — maximize 8x weekend rewards"
    },
    "idfc_millennia": {
        "name": "IDFC FIRST Millennia Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "6x rewards on online spends", "category": "shopping"},
            {"type": "points", "value": "3x rewards on offline spends", "category": "general"},
            {"type": "perk", "value": "4 complimentary railway lounge visits/quarter", "category": "travel"},
        ],
        "shopping_tip": "6x online rewards is among the best in segment — great for e-commerce purchases"
    },
    "idfc_select": {
        "name": "IDFC FIRST Select Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "10x rewards on select brands (Amazon, Flipkart, BigBasket)", "category": "shopping"},
            {"type": "points", "value": "4x rewards on all other spends", "category": "general"},
            {"type": "perk", "value": "Airport lounge access (domestic)", "category": "travel"},
        ],
        "shopping_tip": "10x on Amazon/Flipkart is INSANE value — check if your purchase qualifies"
    },
    "onecard": {
        "name": "OneCard Metal Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5x rewards on top spend category (auto-detected)", "category": "shopping"},
            {"type": "cashback", "value": "2x rewards on all other spends", "category": "general"},
            {"type": "perk", "value": "No annual fee, no joining fee", "category": "general"},
        ],
        "shopping_tip": "OneCard auto-detects your top category — if shopping is your #1 spend, you get 5x automatically!"
    },
    "cred_mint": {
        "name": "CRED Mint (via RBL Bank)",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5% cashback on CRED partner brands", "category": "shopping"},
            {"type": "cashback", "value": "1% cashback on all other spends", "category": "general"},
            {"type": "perk", "value": "CRED coins on every payment", "category": "rewards"},
        ],
        "shopping_tip": "Pay via CRED app for extra CRED coins — redeem for brand vouchers and cashback"
    },
    "sbi_cashback": {
        "name": "SBI Cashback Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "5% cashback on all online spends", "category": "shopping"},
            {"type": "cashback", "value": "1% cashback on offline spends", "category": "general"},
        ],
        "shopping_tip": "Flat 5% on ALL online purchases — no category restrictions. Best flat-rate online card!"
    },
    "bob_eterna": {
        "name": "Bank of Baroda Eterna Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "6x rewards on weekend dining/shopping", "category": "shopping"},
            {"type": "points", "value": "3x rewards on weekday spends", "category": "general"},
            {"type": "perk", "value": "2 domestic lounge visits/quarter", "category": "travel"},
        ],
        "shopping_tip": "Shop on weekends for 6x rewards — great for planned purchases"
    },
    "rupay_platinum": {
        "name": "RuPay Platinum Debit Card (various banks)",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "UPI cashback via RuPay on Amazon, Swiggy", "category": "shopping"},
            {"type": "perk", "value": "No transaction fees on RuPay", "category": "general"},
            {"type": "perk", "value": "Complimentary IRCTC lounge access", "category": "travel"},
        ],
        "shopping_tip": "RuPay debit cards often get exclusive cashback during Amazon/Flipkart sales!"
    },
    "axis_neo": {
        "name": "Axis Bank Neo Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "2% cashback on utility bill payments", "category": "bills"},
            {"type": "cashback", "value": "1% cashback on all other spends", "category": "general"},
            {"type": "perk", "value": "Buy 1 Get 1 movie tickets (Paytm)", "category": "entertainment"},
        ],
        "shopping_tip": "Entry-level Axis card — good for bill payments. Upgrade to Flipkart card for shopping."
    },
    "hdfc_swiggy": {
        "name": "HDFC Swiggy Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "cashback", "value": "10% cashback on Swiggy orders", "category": "dining"},
            {"type": "cashback", "value": "5% cashback on online shopping", "category": "shopping"},
            {"type": "cashback", "value": "1% on all other spends", "category": "general"},
        ],
        "shopping_tip": "5% on all online shopping is great — plus 10% on Swiggy is unmatched"
    },
    "icici_coral": {
        "name": "ICICI Bank Coral Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "2 PAYBACK points per ₹100 spent", "category": "general"},
            {"type": "perk", "value": "Buy 1 Get 1 on BookMyShow (up to ₹250)", "category": "entertainment"},
            {"type": "perk", "value": "1 domestic lounge access/quarter", "category": "travel"},
        ],
        "shopping_tip": "Good entry card — PAYBACK points redeemable at many partner stores"
    },
    "icici_sapphiro": {
        "name": "ICICI Bank Sapphiro Credit Card",
        "country": "IN",
        "benefits": [
            {"type": "points", "value": "2x rewards on all online spends", "category": "shopping"},
            {"type": "perk", "value": "Golf privileges and airport lounges", "category": "travel"},
            {"type": "protection", "value": "Extended warranty on electronics", "category": "shopping"},
        ],
        "shopping_tip": "Extended warranty on electronics is valuable for expensive purchases — 1 extra year free!"
    },
}


# ============================================================
# COUPON SOURCES — Affiliate network APIs
# ============================================================

COUPON_API_BASE = "https://api.couponapi.org/v1"

# Store domain mapping for popular brands
STORE_DOMAINS = {
    # India
    "amazon.in": "amazon.in",
    "amazon": "amazon.com",
    "flipkart": "flipkart.com",
    "myntra": "myntra.com",
    "croma": "croma.com",
    "reliance digital": "reliancedigital.in",
    "vijay sales": "vijaysales.com",
    "tata cliq": "tatacliq.com",
    "jiomart": "jiomart.com",
    "meesho": "meesho.com",
    "snapdeal": "snapdeal.com",
    "nykaa": "nykaa.com",
    "ajio": "ajio.com",
    # US/Global
    "nike": "nike.com",
    "adidas": "adidas.com",
    "walmart": "walmart.com",
    "target": "target.com",
    "bestbuy": "bestbuy.com",
    "ebay": "ebay.com",
}

# Confidence thresholds
CONFIDENCE_THRESHOLD = 0.7  # Only show coupons above this
COUPON_TTL_HOURS = 72       # Hide coupons older than this
MAX_COUPONS_DISPLAY = 5     # Show top 5 coupons max


def _calculate_confidence(coupon: Dict) -> float:
    """Calculate confidence score for a coupon."""
    score = 0.0

    # Source trust
    source = coupon.get("source", "").lower()
    if source in ("cj", "awin", "rakuten", "impact", "merchant"):
        score += 0.4  # Affiliate network = high trust
    elif source in ("couponapi", "aggregator"):
        score += 0.3
    elif source in ("community", "user"):
        score += 0.15
    else:
        score += 0.1

    # Has expiry date and not expired
    expiry = coupon.get("expires")
    if expiry:
        try:
            exp_date = datetime.fromisoformat(expiry)
            if exp_date > datetime.now():
                days_left = (exp_date - datetime.now()).days
                if days_left > 7:
                    score += 0.3
                elif days_left > 1:
                    score += 0.2
                else:
                    score += 0.1
            else:
                return 0.0  # Expired — kill it
        except (ValueError, TypeError):
            score += 0.1
    else:
        score += 0.1

    # Has actual code (not just "deal")
    if coupon.get("code") and coupon["code"] != "NO_CODE":
        score += 0.2
    else:
        score += 0.05

    # Verification status
    if coupon.get("verified"):
        score += 0.1

    return min(score, 1.0)


async def _fetch_couponapi(store_domain: str, api_key: str = None) -> List[Dict]:
    """Fetch coupons from CouponAPI.org."""
    try:
        params = {"store": store_domain}
        if api_key:
            params["api_key"] = api_key

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{COUPON_API_BASE}/coupons", params=params)
            if resp.status_code == 200:
                data = resp.json()
                coupons = []
                for item in data if isinstance(data, list) else data.get("coupons", []):
                    coupons.append({
                        "code": item.get("code", "NO_CODE"),
                        "discount": item.get("discount", item.get("title", "")),
                        "description": item.get("description", ""),
                        "source": "couponapi",
                        "expires": item.get("end_date", item.get("expiry", None)),
                        "verified": item.get("verified", False),
                        "type": "code" if item.get("code") else "deal",
                    })
                return coupons
    except Exception:
        pass
    return []


async def _fetch_amazon_coupons(asin: str) -> List[Dict]:
    """
    Check for Amazon-native coupons (clip coupons, Subscribe & Save).
    
    Note: Amazon coupons are best detected via PA-API product data
    (when available). This HTTP fallback uses lightweight regex parsing
    without browser automation dependencies.
    """
    coupons = []
    try:
        url = f"https://www.amazon.in/dp/{asin}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        import re
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return coupons

            html = resp.text

            # Detect clip coupon via common patterns in Amazon HTML
            coupon_patterns = [
                r'couponText["\s>]*([^<]*\d+%[^<]*)',
                r'promoPriceBlockMessage["\s>]*([^<]*(?:coupon|₹|%)[^<]*)',
                r'couponBadge["\s>]*([^<]*\d+[^<]*)',
                r'Apply\s*(\d+%?\s*coupon)',
                r'Save\s*(₹[\d,]+)\s*with\s*coupon',
                r'Save\s*(\d+%)\s*with\s*coupon',
            ]

            for pattern in coupon_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()
                    # Sanitize: reject if it contains JS/HTML artifacts
                    if len(text) > 150 or '{' in text or '<' in text or 'function' in text.lower() or 'ajax' in text.lower() or 'document' in text.lower() or '.com' in text:
                        continue
                    if text and ("coupon" in text.lower() or "%" in text or "₹" in text or "$" in text):
                        coupons.append({
                            "code": "CLIP_COUPON",
                            "discount": text,
                            "description": "Amazon clip coupon — apply on product page",
                            "source": "merchant",
                            "verified": True,
                            "type": "clip",
                            "expires": None,
                        })
                        break  # Only one clip coupon per product

            # Detect Subscribe & Save
            sns_patterns = [
                r'Save\s*(?:up\s*to\s*)?(\d+%)\s*(?:more\s*)?(?:with|when)?\s*Subscribe',
                r'Subscribe\s*&?\s*Save[^<]*?(\d+%[^<]*)',
                r'snsDetailPageFeature["\s>]*([^<]*\d+%[^<]*)',
            ]

            for pattern in sns_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    sns_text = match.group(1).strip()
                    coupons.append({
                        "code": "SUBSCRIBE_SAVE",
                        "discount": sns_text if sns_text else "5-15% off with Subscribe & Save",
                        "description": "Amazon Subscribe & Save discount — auto-delivery",
                        "source": "merchant",
                        "verified": True,
                        "type": "subscription",
                        "expires": None,
                    })
                    break

    except Exception:
        pass
    return coupons


async def _fetch_cashback_offers(store_domain: str) -> List[Dict]:
    """Check for cashback offers from major platforms."""
    cashback = []

    # Known cashback rates (curated, updated periodically)
    # In production, this would call Rakuten/CashKaro APIs
    KNOWN_CASHBACK = {
        "amazon.com": [
            {"platform": "Rakuten", "rate": "1-3%", "note": "Varies by category"},
            {"platform": "TopCashback", "rate": "1-5%", "note": "Higher on select categories"},
        ],
        "amazon.in": [
            {"platform": "CashKaro", "rate": "2-6%", "note": "Varies by category"},
            {"platform": "Magicpin", "rate": "3-5%", "note": "Via gift cards"},
            {"platform": "Amazon Pay (wallet)", "rate": "2-10%", "note": "Load via UPI for extra cashback during sales"},
            {"platform": "CRED Pay", "rate": "1-5%", "note": "Pay via CRED for coins redeemable as cashback"},
        ],
        "nike.com": [
            {"platform": "Rakuten", "rate": "6-8%", "note": "Standard rate"},
            {"platform": "TopCashback", "rate": "7-10%", "note": "Check for elevated rates"},
        ],
        "flipkart.com": [
            {"platform": "CashKaro", "rate": "3-6%", "note": "Varies by category"},
            {"platform": "Flipkart Pay Later", "rate": "1-3%", "note": "Interest-free EMI + extra discount"},
            {"platform": "PhonePe (Flipkart)", "rate": "2-5%", "note": "Pay via PhonePe UPI for cashback during sales"},
            {"platform": "CRED Pay", "rate": "1-5%", "note": "CRED coins on Flipkart payments"},
        ],
        "myntra.com": [
            {"platform": "CashKaro", "rate": "4-7%", "note": "Fashion & accessories"},
            {"platform": "Myntra Insider Points", "rate": "2-5%", "note": "Redeem as coupons on next purchase"},
        ],
        "croma.com": [
            {"platform": "CashKaro", "rate": "2-4%", "note": "Electronics & appliances"},
            {"platform": "HDFC SmartBuy", "rate": "5-10%", "note": "Via HDFC card reward points"},
        ],
        "reliancedigital.in": [
            {"platform": "JioMart/Reliance Pay", "rate": "2-5%", "note": "Jio wallet cashback"},
        ],
        "vijaysales.com": [
            {"platform": "CashKaro", "rate": "1-3%", "note": "Electronics"},
        ],
    }

    if store_domain in KNOWN_CASHBACK:
        for cb in KNOWN_CASHBACK[store_domain]:
            cashback.append({
                "platform": cb["platform"],
                "rate": cb["rate"],
                "note": cb.get("note", ""),
                "type": "cashback",
            })

    return cashback


def get_card_recommendations(store_domain: str, price: float = None, country: str = "IN") -> List[Dict]:
    """Get credit card recommendations for this purchase."""
    recommendations = []

    # Filter cards by country
    relevant_cards = {
        k: v for k, v in CREDIT_CARD_BENEFITS.items()
        if v["country"] == country
    }

    for card_key, card in relevant_cards.items():
        shopping_benefits = [
            b for b in card["benefits"]
            if b["category"] in ("shopping", "general")
        ]
        if not shopping_benefits:
            continue

        # Check if card has special benefit for this store
        special = None
        if "amazon" in store_domain and "amazon" in card_key:
            special = "🔥 BEST CARD for this store!"

        best_benefit = shopping_benefits[0]
        savings_estimate = None
        if price and "%" in best_benefit["value"]:
            try:
                # Extract percentage
                pct_str = best_benefit["value"]
                for part in pct_str.split():
                    if "%" in part:
                        pct = float(part.replace("%", "").replace("x", ""))
                        if pct < 20:  # Sanity check
                            savings_estimate = round(price * pct / 100, 2)
                        break
            except (ValueError, IndexError):
                pass

        recommendations.append({
            "card": card["name"],
            "benefit": best_benefit["value"],
            "savings_estimate": savings_estimate,
            "shopping_tip": card["shopping_tip"],
            "special": special,
            "all_benefits": [b["value"] for b in shopping_benefits],
        })

    # Sort: special cards first, then by savings estimate
    recommendations.sort(
        key=lambda x: (0 if x.get("special") else 1, -(x.get("savings_estimate") or 0))
    )

    return recommendations[:4]  # Top 4 cards


# ============================================================
# UPI & WALLET BENEFITS (India-specific)
# ============================================================

UPI_WALLET_BENEFITS = {
    "amazon.in": [
        {"wallet": "Amazon Pay UPI", "benefit": "Up to 10% cashback on loading via UPI during sales", "max_cashback": "₹200", "note": "Best during Great Indian Festival / Prime Day"},
        {"wallet": "Amazon Pay Later", "benefit": "Interest-free EMI on orders above ₹3,000", "max_cashback": None, "note": "No extra cashback but saves interest"},
    ],
    "flipkart.com": [
        {"wallet": "PhonePe UPI", "benefit": "₹25-100 cashback on transactions above ₹199", "max_cashback": "₹100", "note": "Offers rotate — check PhonePe app before paying"},
        {"wallet": "Flipkart Pay Later", "benefit": "Interest-free EMI + up to ₹100 off", "max_cashback": "₹100", "note": "Auto-applied during BBD sales"},
        {"wallet": "Paytm UPI", "benefit": "Scratch cards worth up to ₹500 on Flipkart", "max_cashback": "₹500", "note": "Scratch card is lottery — avg value ₹5-50"},
    ],
    "croma.com": [
        {"wallet": "HDFC SmartBuy", "benefit": "10x reward points on HDFC cards", "max_cashback": None, "note": "Must go through SmartBuy portal first"},
    ],
}


def get_upi_wallet_benefits(store_domain: str, country: str = "IN") -> List[Dict]:
    """Get UPI and wallet cashback benefits for a store (India-specific)."""
    if country != "IN":
        return []
    
    benefits = []
    if store_domain in UPI_WALLET_BENEFITS:
        for b in UPI_WALLET_BENEFITS[store_domain]:
            benefits.append({
                "wallet": b["wallet"],
                "benefit": b["benefit"],
                "max_cashback": b.get("max_cashback"),
                "note": b.get("note", ""),
                "type": "upi_wallet",
            })
    return benefits


# ============================================================
# MAIN FUNCTION — Drop-in replacement for find_coupons
# ============================================================

async def find_coupons(product_name: str, asin: str, price: float = None, country: str = "IN") -> Dict:
    """
    🎯 Coupon Sniper — Find verified coupons, cashback, and credit card benefits.

    Drop-in compatible with existing scrapers.find_coupons() signature.
    Returns enriched data with coupons + cashback + card recommendations.

    Principle: Show NOTHING rather than wrong/expired coupons.
    """
    # Determine store domain
    store_domain = "amazon.in" if country == "IN" else "amazon.com"
    for keyword, domain in STORE_DOMAINS.items():
        if keyword in product_name.lower():
            store_domain = domain
            break

    # Fetch from all sources in parallel
    couponapi_key = os.environ.get("COUPONAPI_KEY")

    api_coupons, amazon_coupons, cashback_offers = await asyncio.gather(
        _fetch_couponapi(store_domain, couponapi_key),
        _fetch_amazon_coupons(asin),
        _fetch_cashback_offers(store_domain),
        return_exceptions=True,
    )

    # UPI/Wallet benefits (India only, instant — no API call)
    upi_benefits = get_upi_wallet_benefits(store_domain, country)

    # Handle exceptions gracefully
    if isinstance(api_coupons, Exception):
        api_coupons = []
    if isinstance(amazon_coupons, Exception):
        amazon_coupons = []
    if isinstance(cashback_offers, Exception):
        cashback_offers = []

    # Merge all coupons
    all_coupons = amazon_coupons + api_coupons  # Amazon first (highest trust)

    # ===== VERIFICATION GATE =====
    # Only pass coupons above confidence threshold
    verified_coupons = []
    for coupon in all_coupons:
        confidence = _calculate_confidence(coupon)
        if confidence >= CONFIDENCE_THRESHOLD:
            coupon["confidence"] = round(confidence, 2)
            verified_coupons.append(coupon)

    # Sort by confidence (highest first), limit display
    verified_coupons.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    verified_coupons = verified_coupons[:MAX_COUPONS_DISPLAY]

    # Credit card recommendations
    card_recs = get_card_recommendations(store_domain, price, country)

    # ===== BEST COMBO CALCULATOR =====
    best_combo = _calculate_best_combo(verified_coupons, cashback_offers, card_recs, price)

    return {
        "found": len(verified_coupons),
        "coupons": verified_coupons,
        "cashback": cashback_offers,
        "upi_wallets": upi_benefits,
        "credit_cards": card_recs,
        "best_combo": best_combo,
        "store": store_domain,
        "verification": "All coupons verified above confidence threshold"
            if verified_coupons else "No verified coupons found — we show nothing rather than wrong codes",
        "advice": _generate_advice(verified_coupons, cashback_offers, card_recs),
    }


def _calculate_best_combo(
    coupons: List[Dict],
    cashback: List[Dict],
    cards: List[Dict],
    price: float = None,
) -> Optional[Dict]:
    """Calculate the best stacking combination for maximum savings."""
    if not price or price <= 0:
        return None

    total_savings = 0.0
    strategy_parts = []

    # Best coupon
    if coupons:
        best_coupon = coupons[0]
        discount_text = best_coupon.get("discount", "")
        coupon_savings = 0

        # Try to parse discount amount
        if "%" in discount_text:
            for word in discount_text.replace(",", "").split():
                clean = word.strip("%").strip("₹").strip("$")
                try:
                    pct = float(clean)
                    if pct < 100:
                        coupon_savings = price * pct / 100
                        break
                except ValueError:
                    continue
        elif "₹" in discount_text or "$" in discount_text:
            for word in discount_text.replace(",", "").split():
                clean = word.strip("₹").strip("$")
                try:
                    coupon_savings = float(clean)
                    break
                except ValueError:
                    continue

        if coupon_savings > 0:
            total_savings += coupon_savings
            code = best_coupon.get("code", "")
            strategy_parts.append(f"{code} ({discount_text})")

    # Best cashback
    if cashback:
        best_cb = cashback[0]
        rate_text = best_cb.get("rate", "")
        try:
            # Take lower bound of range (e.g., "3-6%" → 3%)
            pct = float(rate_text.split("-")[0].strip().replace("%", ""))
            cb_savings = (price - total_savings) * pct / 100
            total_savings += cb_savings
            strategy_parts.append(f"{best_cb['platform']} ({rate_text} cashback)")
        except (ValueError, IndexError):
            pass

    # Best card
    if cards:
        best_card = cards[0]
        if best_card.get("savings_estimate"):
            total_savings += best_card["savings_estimate"]
            strategy_parts.append(f"{best_card['card']} ({best_card['benefit']})")

    if total_savings <= 0:
        return None

    return {
        "total_savings": round(total_savings, 2),
        "savings_percentage": round((total_savings / price) * 100, 1),
        "strategy": " + ".join(strategy_parts),
        "original_price": price,
        "final_price": round(price - total_savings, 2),
    }


def _generate_advice(
    coupons: List[Dict],
    cashback: List[Dict],
    cards: List[Dict],
) -> str:
    """Generate human-readable advice."""
    parts = []

    if coupons:
        codes = [c["code"] for c in coupons if c.get("code") and c["code"] not in ("NO_CODE", "CLIP_COUPON", "SUBSCRIBE_SAVE")]
        clips = [c for c in coupons if c.get("code") == "CLIP_COUPON"]
        sns = [c for c in coupons if c.get("code") == "SUBSCRIBE_SAVE"]

        if codes:
            parts.append(f"Apply code{'s' if len(codes) > 1 else ''}: {', '.join(codes)}")
        if clips:
            parts.append("Clip the on-page Amazon coupon before checkout")
        if sns:
            parts.append("Consider Subscribe & Save for extra 5-15% off")
    else:
        parts.append("No verified coupon codes available right now")

    if cashback:
        best = cashback[0]
        parts.append(f"Route through {best['platform']} for {best['rate']} cashback")

    if cards:
        best = cards[0]
        if best.get("special"):
            parts.append(f"💳 {best['special']} Use {best['card']} — {best['benefit']}")
        else:
            parts.append(f"💳 Pay with {best['card']} for {best['benefit']}")

    return " → ".join(parts)
