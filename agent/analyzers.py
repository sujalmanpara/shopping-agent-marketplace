# analyzers.py — Fake review detection, regret analysis, confidence scoring

from typing import Dict, List

def analyze_fake_reviews(reviews: List[Dict]) -> Dict:
    """Detect suspicious review patterns."""
    if not reviews:
        return {"score": 0, "risk": "unknown", "reason": "No reviews to analyze"}
    suspicious_count = 0
    total = len(reviews)
    for review in reviews:
        if any(phrase in review["body"].lower() for phrase in ["amazing", "best product ever", "highly recommend"]):
            if len(review["body"].split()) < 15:
                suspicious_count += 1
        if review["rating"] == 5.0 and len(review["body"]) < 20:
            suspicious_count += 1
    fake_score = int((suspicious_count / total) * 100)
    risk = "high" if fake_score > 40 else "medium" if fake_score > 20 else "low"
    return {"score": fake_score, "risk": risk, "suspicious_count": suspicious_count, "total_analyzed": total}

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
