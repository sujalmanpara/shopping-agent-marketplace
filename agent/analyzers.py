# analyzers.py — ML-powered fake review detection, regret analysis, confidence scoring
# Upgraded from keyword-based (~60%) to XGBoost ML model (90.2% accuracy)
# Phase 1 fixes: sample-size guards, multi-dimensional confidence scoring

import os
import numpy as np
from typing import Dict, List
from scipy.sparse import issparse
import joblib

# Load ML model and pipeline once at import time
_BASE = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_BASE, "models")

try:
    _model = joblib.load(os.path.join(_MODELS_DIR, "fake_review_model.joblib"))
    _pipeline = joblib.load(os.path.join(_MODELS_DIR, "feature_pipeline.joblib"))
    _ML_AVAILABLE = True
except Exception:
    _ML_AVAILABLE = False
    print("[!] ML model not found — falling back to keyword detection")


def _ml_detect(review_text: str) -> tuple:
    """Run ML prediction on a single review. Returns (is_fake, confidence)."""
    X = np.array([review_text])
    X_feat = _pipeline.transform(X)
    if issparse(X_feat):
        X_feat = X_feat.toarray()
    proba = _model.predict_proba(X_feat)[0]
    fake_prob = float(proba[1])
    return fake_prob >= 0.5, fake_prob


def _keyword_detect(review: Dict) -> bool:
    """Original keyword fallback (~60% accuracy)."""
    body = review.get("body", "").lower()
    if any(phrase in body for phrase in ["amazing", "best product ever", "highly recommend"]):
        if len(body.split()) < 15:
            return True
    if review.get("rating", 0) == 5.0 and len(body) < 20:
        return True
    return False


def analyze_fake_reviews(reviews: List[Dict]) -> Dict:
    """
    Detect suspicious review patterns using ML model (90.2% accuracy).
    Falls back to keyword detection if model files are missing.
    
    Sample-size guards:
    - <5 reviews: return risk="insufficient_data", no percentage
    - 5-14 reviews: return risk="limited", binary suspicious flag only
    - 15+: normal percentage mode with full analysis
    """
    from .constants import MIN_REVIEWS_FOR_ANALYSIS, MIN_REVIEWS_FOR_PERCENTAGE, FAKE_REVIEW_THRESHOLD

    if not reviews:
        return {"score": 0, "risk": "unknown", "reason": "No reviews to analyze"}

    total = len(reviews)

    # Guard: insufficient data
    if total < MIN_REVIEWS_FOR_ANALYSIS:
        return {
            "score": 0,
            "risk": "insufficient_data",
            "reason": f"Only {total} reviews — need at least {MIN_REVIEWS_FOR_ANALYSIS} for analysis",
            "suspicious_count": 0,
            "total_analyzed": total,
            "method": "skipped",
            "model_accuracy": "N/A",
            "flagged_reviews": [],
        }

    # Run detection on all reviews
    suspicious_count = 0
    flagged_reviews = []

    for review in reviews:
        body = review.get("body", review.get("text", ""))
        if not body:
            continue

        if _ML_AVAILABLE:
            is_fake, confidence = _ml_detect(body)
            if is_fake:
                suspicious_count += 1
                flagged_reviews.append({
                    "text": body[:100] + "..." if len(body) > 100 else body,
                    "confidence": round(confidence, 3),
                    "method": "ml"
                })
        else:
            if _keyword_detect(review):
                suspicious_count += 1
                flagged_reviews.append({
                    "text": body[:100] + "..." if len(body) > 100 else body,
                    "confidence": 0.6,
                    "method": "keyword"
                })

    # Guard: limited data (5-14 reviews) — binary flag only, no percentage
    if total < MIN_REVIEWS_FOR_PERCENTAGE:
        has_suspicious = suspicious_count > 0
        return {
            "score": 0,  # No percentage with limited data
            "risk": "limited",
            "reason": f"Only {total} reviews — showing binary flag (need {MIN_REVIEWS_FOR_PERCENTAGE}+ for percentages)",
            "has_suspicious": has_suspicious,
            "suspicious_count": suspicious_count,
            "total_analyzed": total,
            "method": "ml" if _ML_AVAILABLE else "keyword",
            "model_accuracy": "90.2%" if _ML_AVAILABLE else "~60%",
            "flagged_reviews": flagged_reviews[:3],  # Show fewer with limited data
        }

    # Normal mode: 15+ reviews — full percentage analysis
    fake_score = int((suspicious_count / total) * 100) if total > 0 else 0
    risk = "high" if fake_score > FAKE_REVIEW_THRESHOLD else "medium" if fake_score > 20 else "low"

    return {
        "score": fake_score,
        "risk": risk,
        "suspicious_count": suspicious_count,
        "total_analyzed": total,
        "method": "ml" if _ML_AVAILABLE else "keyword",
        "model_accuracy": "90.2%" if _ML_AVAILABLE else "~60%",
        "flagged_reviews": flagged_reviews[:5],
    }


def analyze_regret_pattern(reviews: List[Dict]) -> Dict:
    """Detect if ratings drop over time (regret indicator)."""
    if not reviews:
        return {"severity": "unknown", "warning": None}
    dated_reviews = [r for r in reviews if r.get("date")]
    if len(dated_reviews) < 5:
        return {"severity": "low", "warning": "Not enough data"}
    early_ratings = [r["rating"] for r in dated_reviews[-3:]]
    recent_ratings = [r["rating"] for r in dated_reviews[:3]]
    early_avg = sum(early_ratings) / len(early_ratings)
    recent_avg = sum(recent_ratings) / len(recent_ratings)
    drop = early_avg - recent_avg
    if drop > 1.0:
        return {"severity": "high", "warning": f"⚠️ Ratings dropped {drop:.1f} stars over time", "early_avg": round(early_avg, 2), "recent_avg": round(recent_avg, 2)}
    elif drop > 0.5:
        return {"severity": "medium", "warning": f"Slight rating decline ({drop:.1f} stars)", "early_avg": round(early_avg, 2), "recent_avg": round(recent_avg, 2)}
    return {"severity": "low", "warning": None}


def calculate_confidence(source_results: Dict) -> Dict:
    """
    Multi-dimensional confidence scoring.
    
    Replaces the old binary source counting with weighted scoring across
    three dimensions: data sufficiency, source agreement, and data quality.
    
    Args:
        source_results: Dict from api_layer.fetch_all_sources()
            Expected format: {"sources": {name: Result, ...}, "summary": {...}}
    
    Returns:
        {
            "overall": 0.0-1.0,
            "level": "HIGH" | "MEDIUM" | "LOW",
            "sufficiency": float,
            "agreement": float,
            "quality": float,
            "sources_used": int,
            "sources_total": int,
            "breakdown": {source_name: weight_earned, ...}
        }
    """
    from .constants import SOURCE_WEIGHTS

    sources = source_results.get("sources", {})
    if not sources:
        return {
            "overall": 0.0,
            "level": "LOW",
            "sufficiency": 0.0,
            "agreement": 0.0,
            "quality": 0.0,
            "sources_used": 0,
            "sources_total": 0,
            "breakdown": {},
        }

    # ── Dimension 1: Data Sufficiency (how many sources returned data) ──
    # Weighted by source importance
    sufficiency = 0.0
    breakdown = {}
    sources_used = 0

    for name, result in sources.items():
        weight = SOURCE_WEIGHTS.get(name, 0.05)
        if result.get("success"):
            sufficiency += weight
            breakdown[name] = round(weight, 3)
            sources_used += 1
        else:
            breakdown[name] = 0.0

    # Normalize sufficiency to 0-1 (weights sum to 1.0)
    total_possible_weight = sum(SOURCE_WEIGHTS.get(name, 0.05) for name in sources)
    sufficiency_score = sufficiency / total_possible_weight if total_possible_weight > 0 else 0.0

    # ── Dimension 2: Source Agreement (do ratings agree across sources?) ──
    ratings = []

    # Amazon rating
    amazon_data = sources.get("amazon", {}).get("data", {})
    if amazon_data.get("rating"):
        ratings.append(amazon_data["rating"] / 5.0)  # Normalize to 0-1

    # Fakespot grade (convert letter to number)
    fakespot_data = sources.get("fakespot", {}).get("data", {})
    grade = fakespot_data.get("grade", "")
    grade_map = {"A": 0.95, "B": 0.80, "C": 0.60, "D": 0.40, "F": 0.20}
    if grade in grade_map:
        ratings.append(grade_map[grade])

    # ReviewMeta adjusted rating
    reviewmeta_data = sources.get("reviewmeta", {}).get("data", {})
    if reviewmeta_data.get("adjusted_rating"):
        ratings.append(reviewmeta_data["adjusted_rating"] / 5.0)

    # Trustpilot score
    trustpilot_data = sources.get("trustpilot", {}).get("data", {})
    if trustpilot_data.get("trust_score"):
        ratings.append(trustpilot_data["trust_score"] / 5.0)

    # RTINGS score
    rtings_data = sources.get("rtings", {}).get("data", {})
    if rtings_data.get("score"):
        ratings.append(rtings_data["score"] / 10.0)

    if len(ratings) >= 2:
        # Agreement = 1 - standard deviation of normalized ratings
        # Low std = high agreement
        std = float(np.std(ratings))
        agreement_score = max(0.0, 1.0 - std * 3)  # Scale: std of 0.33 = 0 agreement
    elif len(ratings) == 1:
        agreement_score = 0.5  # Can't measure agreement with 1 source
    else:
        agreement_score = 0.3  # No rating data at all

    # ── Dimension 3: Data Quality (richness of data) ──
    quality_signals = 0.0
    quality_count = 0

    # Amazon: more reviews = higher quality
    review_count = amazon_data.get("review_count", 0)
    if review_count > 1000:
        quality_signals += 1.0
    elif review_count > 100:
        quality_signals += 0.7
    elif review_count > 10:
        quality_signals += 0.4
    elif review_count > 0:
        quality_signals += 0.2
    quality_count += 1

    # Reddit: engagement level
    reddit_data = sources.get("reddit", {}).get("data", {})
    engagement = reddit_data.get("total_engagement", 0)
    if engagement > 500:
        quality_signals += 1.0
    elif engagement > 100:
        quality_signals += 0.7
    elif engagement > 10:
        quality_signals += 0.4
    elif reddit_data.get("found", 0) > 0:
        quality_signals += 0.2
    quality_count += 1

    # YouTube: total views
    youtube_data = sources.get("youtube", {}).get("data", {})
    total_views = youtube_data.get("total_views", 0)
    if total_views > 100000:
        quality_signals += 1.0
    elif total_views > 10000:
        quality_signals += 0.7
    elif total_views > 1000:
        quality_signals += 0.4
    elif youtube_data.get("found", 0) > 0:
        quality_signals += 0.2
    quality_count += 1

    # Keepa: price history depth
    keepa_data = sources.get("keepa", {}).get("data", {})
    data_points = keepa_data.get("data_points", 0)
    if data_points > 100:
        quality_signals += 1.0
    elif data_points > 30:
        quality_signals += 0.6
    elif data_points > 0:
        quality_signals += 0.3
    quality_count += 1

    quality_score = quality_signals / quality_count if quality_count > 0 else 0.0

    # ── Final Score: Weighted combination of all three dimensions ──
    overall = (sufficiency_score * 0.40) + (agreement_score * 0.30) + (quality_score * 0.30)
    overall = round(min(1.0, max(0.0, overall)), 3)

    # Determine level
    if overall >= 0.65:
        level = "HIGH"
    elif overall >= 0.40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "overall": overall,
        "level": level,
        "sufficiency": round(sufficiency_score, 3),
        "agreement": round(agreement_score, 3),
        "quality": round(quality_score, 3),
        "sources_used": sources_used,
        "sources_total": len(sources),
        "breakdown": breakdown,
    }
