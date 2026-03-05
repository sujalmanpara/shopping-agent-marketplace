# analyzers.py — ML-powered fake review detection, regret analysis, confidence scoring
# Upgraded from keyword-based (~60%) to XGBoost ML model (90.2% accuracy)

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
    """
    if not reviews:
        return {"score": 0, "risk": "unknown", "reason": "No reviews to analyze"}

    suspicious_count = 0
    total = len(reviews)
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

    fake_score = int((suspicious_count / total) * 100) if total > 0 else 0
    risk = "high" if fake_score > 40 else "medium" if fake_score > 20 else "low"

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


def calculate_confidence(amazon_data: Dict, reddit_data: Dict, youtube_data: Dict, twitter_data: Dict) -> int:
    """Calculate confidence score based on source availability."""
    from .constants import SOURCE_WEIGHTS
    score = 0
    if amazon_data.get("rating", 0) > 0:
        score += 30
    if reddit_data.get("found", 0) > 0:
        score += SOURCE_WEIGHTS["reddit"]
    if youtube_data.get("found", 0) > 0:
        score += SOURCE_WEIGHTS["youtube"]
    if twitter_data.get("found", 0) > 0:
        score += SOURCE_WEIGHTS["twitter"]
    return min(score, 100)
