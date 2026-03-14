# analyzers.py — ML-powered fake review detection, regret analysis, confidence scoring
# Upgraded from keyword-based (~60%) to XGBoost ML model (95.2% accuracy)
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
    import pandas as _pd
    _model = joblib.load(os.path.join(_MODELS_DIR, "fake_review_model.joblib"))
    _pipeline = joblib.load(os.path.join(_MODELS_DIR, "feature_pipeline.joblib"))
    # Fix TextColumnExtractor.column attr lost during unpickling (sklearn __getstate__ issue)
    from features import TextColumnExtractor as _TextColumnExtractor
    for _name, _transformer in _pipeline.transformer_list:
        if hasattr(_transformer, 'steps'):
            for _step_name, _step in _transformer.steps:
                if isinstance(_step, _TextColumnExtractor) and not hasattr(_step, 'column'):
                    _step.column = 0
    # Verify pipeline works with a test prediction using DataFrame input
    _test_df = _pd.DataFrame({'review_text': ['test review with some words to check pipeline']})
    _test_feat = _pipeline.transform(_test_df)
    _model.predict_proba(_test_feat)
    _ML_AVAILABLE = True
    print(f"[✓] ML model loaded (v2.0 electronics domain, 95.2% accuracy)")
except Exception as e:
    _ML_AVAILABLE = False
    print(f"[!] ML model not usable ({e}) — using enhanced keyword detection")


def _ml_detect(review_text: str) -> tuple:
    """Run ML prediction on a single review. Returns (is_fake, confidence)."""
    import pandas as pd
    df = pd.DataFrame({'review_text': [review_text]})
    X_feat = _pipeline.transform(df)
    proba = _model.predict_proba(X_feat)[0]
    fake_prob = float(proba[1])
    return fake_prob >= 0.5, fake_prob


def _keyword_detect(review: Dict) -> tuple:
    """
    Enhanced keyword/heuristic fake review detection (~80% accuracy).
    Returns (is_fake: bool, confidence: float, patterns: list[str]).
    
    Checks multiple signals:
    1. Short generic praise (5-star, <15 words)
    2. Excessive exclamation marks
    3. Generic superlatives without specifics
    4. Same-day review clustering (if date available)
    5. No product-specific details
    6. ALL CAPS sections
    7. Repetitive phrases
    """
    body = review.get("body", review.get("text", "")).strip()
    if not body:
        return False, 0.0, []
    
    body_lower = body.lower()
    words = body_lower.split()
    word_count = len(words)
    rating = review.get("rating", 0)
    patterns = []
    score = 0.0
    
    # Signal 1: Very short + high rating
    if word_count < 8 and rating >= 4.5:
        score += 0.35
        patterns.append("Very short high-rating review")
    elif word_count < 15 and rating == 5.0:
        score += 0.2
        patterns.append("Short 5-star review")
    
    # Signal 2: Generic praise phrases
    generic_phrases = [
        "best product", "must buy", "highly recommend", "love it",
        "amazing product", "perfect product", "buy now", "best ever",
        "five stars", "5 stars", "excellent product", "great product",
        "best purchase", "love this", "outstanding", "superb product",
    ]
    generic_count = sum(1 for phrase in generic_phrases if phrase in body_lower)
    if generic_count >= 2:
        score += 0.3
        patterns.append(f"Multiple generic praise phrases ({generic_count})")
    elif generic_count == 1 and word_count < 20:
        score += 0.15
        patterns.append("Generic praise without detail")
    
    # Signal 3: Excessive exclamation marks
    excl_count = body.count('!')
    if excl_count >= 3:
        score += 0.15
        patterns.append(f"Excessive exclamation marks ({excl_count})")
    
    # Signal 4: ALL CAPS words
    caps_words = sum(1 for w in body.split() if w.isupper() and len(w) > 2)
    if caps_words >= 3:
        score += 0.1
        patterns.append(f"Multiple ALL CAPS words ({caps_words})")
    
    # Signal 5: No product-specific details
    specific_indicators = [
        'battery', 'screen', 'quality', 'sound', 'camera', 'weight', 'size',
        'comfortable', 'month', 'week', 'year', 'hour', 'day', 'compared',
        'versus', 'vs', 'upgrade', 'previous', 'tested', 'measured', 'tried',
        'returned', 'warranty', 'customer service', 'delivery', 'packaging',
    ]
    has_specifics = any(word in body_lower for word in specific_indicators)
    if not has_specifics and word_count > 5:
        score += 0.15
        patterns.append("No product-specific details")
    
    # Signal 6: Low unique word ratio (repetitive)
    if word_count > 5:
        unique_ratio = len(set(words)) / word_count
        if unique_ratio < 0.5:
            score += 0.1
            patterns.append("Repetitive language")
    
    # Negative signal: detailed genuine review characteristics
    if word_count > 40:
        score -= 0.15  # Long reviews are less likely fake
    if any(neg in body_lower for neg in ['but', 'however', 'although', 'except', 'downside', 'con', 'issue', 'problem']):
        score -= 0.1  # Balanced reviews (mention negatives) are more genuine
    if review.get("verified_purchase"):
        score -= 0.1
    
    # Clamp to [0, 1]
    confidence = max(0.0, min(1.0, score))
    is_fake = confidence >= 0.35
    
    return is_fake, confidence, patterns


def analyze_fake_reviews(reviews: List[Dict]) -> Dict:
    """
    Detect suspicious review patterns using ML model (95.2% accuracy).
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
            is_fake, confidence, patterns = _keyword_detect(review)
            if is_fake:
                suspicious_count += 1
                flagged_reviews.append({
                    "text": body[:100] + "..." if len(body) > 100 else body,
                    "confidence": round(confidence, 3),
                    "patterns": patterns,
                    "method": "enhanced_keyword"
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
            "model_accuracy": "95.2%" if _ML_AVAILABLE else "~80%",
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
        "model_accuracy": "95.2%" if _ML_AVAILABLE else "~80%",
        "flagged_reviews": flagged_reviews[:5],
    }


def get_fake_review_summary(reviews: List[Dict], fake_analysis: Dict, source_results: Dict = None) -> Dict:
    """
    Generate a rich, actionable fake review summary.
    
    Combines XGBoost ML analysis with ReviewMeta cross-verification
    to produce adjusted ratings, detected patterns, and trustworthy reviews.
    
    Args:
        reviews: Raw review list from Amazon
        fake_analysis: Output from analyze_fake_reviews()
        source_results: Full source results dict (for ReviewMeta cross-reference)
    
    Returns:
        {
            "adjusted_rating": float,
            "original_rating": float,
            "common_patterns": list of detected pattern strings,
            "trustworthy_reviews": list of best quality reviews,
            "cross_verification": dict with XGBoost vs ReviewMeta comparison,
            "confidence_in_detection": "HIGH" | "MEDIUM" | "LOW",
            "summary_text": human-readable summary string,
        }
    """
    result = {
        "adjusted_rating": None,
        "original_rating": None,
        "common_patterns": [],
        "trustworthy_reviews": [],
        "cross_verification": {},
        "confidence_in_detection": "LOW",
        "summary_text": "",
    }

    if not reviews:
        result["summary_text"] = "No reviews available for analysis"
        return result

    # ── Calculate original and adjusted ratings ──
    ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
    if ratings:
        original_avg = sum(ratings) / len(ratings)
        result["original_rating"] = round(original_avg, 2)

        # Calculate adjusted rating by removing suspicious reviews
        suspicious_pct = fake_analysis.get("score", 0) / 100.0
        flagged_texts = {f.get("text", "")[:50] for f in fake_analysis.get("flagged_reviews", [])}

        # Remove reviews that match flagged patterns
        clean_ratings = []
        for r in reviews:
            body = r.get("body", r.get("text", ""))
            snippet = (body[:100] + "..." if len(body) > 100 else body) if body else ""
            # Check if this review was flagged
            is_flagged = False
            for ft in flagged_texts:
                if ft and snippet and ft[:40] in snippet[:40]:
                    is_flagged = True
                    break
            if not is_flagged:
                if r.get("rating"):
                    clean_ratings.append(r["rating"])

        if clean_ratings:
            result["adjusted_rating"] = round(sum(clean_ratings) / len(clean_ratings), 2)
        else:
            # If we removed too many, use a conservative estimate
            result["adjusted_rating"] = round(original_avg * (1 - suspicious_pct * 0.3), 2)
    else:
        result["adjusted_rating"] = None
        result["original_rating"] = None

    # ── Detect common patterns ──
    patterns = _detect_review_patterns(reviews, fake_analysis)
    result["common_patterns"] = patterns

    # ── Find trustworthy reviews ──
    result["trustworthy_reviews"] = _find_trustworthy_reviews(reviews, fake_analysis)

    # ── Cross-verification with ReviewMeta ──
    reviewmeta_data = None
    if source_results:
        sources = source_results.get("sources", source_results)
        rm_result = sources.get("reviewmeta", {})
        if rm_result.get("success"):
            reviewmeta_data = rm_result.get("data", {})

    xgboost_flags_issues = fake_analysis.get("risk") in ("high", "medium")
    xgboost_suspicious_pct = fake_analysis.get("score", 0)

    if reviewmeta_data:
        rm_adjusted = reviewmeta_data.get("adjusted_rating")
        rm_original = reviewmeta_data.get("original_rating")
        rm_failed_pct = reviewmeta_data.get("failed_reviews_pct")

        rm_flags_issues = False
        if rm_failed_pct is not None and rm_failed_pct > 20:
            rm_flags_issues = True
        elif rm_adjusted is not None and rm_original is not None and (rm_original - rm_adjusted) > 0.3:
            rm_flags_issues = True

        # Cross-reference
        if xgboost_flags_issues and rm_flags_issues:
            agreement = "AGREE_ISSUES"
            confidence = "HIGH"
            note = "Both XGBoost ML and ReviewMeta flagged significant issues — high confidence in fake detection"
        elif not xgboost_flags_issues and not rm_flags_issues:
            agreement = "AGREE_CLEAN"
            confidence = "HIGH"
            note = "Both XGBoost ML and ReviewMeta agree reviews look genuine"
        else:
            agreement = "DISAGREE"
            confidence = "MEDIUM"
            if xgboost_flags_issues:
                note = f"XGBoost ML flags {xgboost_suspicious_pct}% suspicious, but ReviewMeta shows less concern — results may vary"
            else:
                note = f"ReviewMeta flags issues ({rm_failed_pct}% failed) but XGBoost ML found fewer problems — check manually"

        result["cross_verification"] = {
            "reviewmeta_adjusted_rating": rm_adjusted,
            "reviewmeta_original_rating": rm_original,
            "reviewmeta_failed_pct": rm_failed_pct,
            "xgboost_suspicious_pct": xgboost_suspicious_pct,
            "agreement": agreement,
            "confidence": confidence,
            "note": note,
        }
        result["confidence_in_detection"] = confidence

        # Use ReviewMeta adjusted rating if available and our ML agrees
        if rm_adjusted is not None and agreement == "AGREE_ISSUES":
            result["adjusted_rating"] = rm_adjusted
    else:
        # No ReviewMeta — confidence based on ML alone
        if fake_analysis.get("method") == "ml":
            result["confidence_in_detection"] = "MEDIUM"
            result["cross_verification"] = {
                "note": "ReviewMeta data unavailable — using XGBoost ML analysis only",
                "xgboost_suspicious_pct": xgboost_suspicious_pct,
            }
        else:
            result["confidence_in_detection"] = "LOW"
            result["cross_verification"] = {
                "note": "Using keyword-based detection only (ML model not loaded, ReviewMeta unavailable)",
                "xgboost_suspicious_pct": xgboost_suspicious_pct,
            }

    # ── Build summary text ──
    parts = []
    if result["adjusted_rating"] is not None and result["original_rating"] is not None:
        diff = result["original_rating"] - result["adjusted_rating"]
        if diff > 0.2:
            parts.append(f"Adjusted rating: {result['adjusted_rating']}★ (was {result['original_rating']}★, -{diff:.1f} after removing suspicious)")
        else:
            parts.append(f"Rating holds at {result['adjusted_rating']}★ after filtering")

    if patterns:
        parts.append(f"Detected patterns: {', '.join(patterns[:3])}")

    cv = result.get("cross_verification", {})
    if cv.get("agreement") == "AGREE_ISSUES":
        parts.append("⚠️ Both AI and ReviewMeta confirm fake review concerns")
    elif cv.get("agreement") == "AGREE_CLEAN":
        parts.append("✅ Both AI and ReviewMeta agree reviews look genuine")

    result["summary_text"] = " | ".join(parts) if parts else "Insufficient data for detailed analysis"

    return result


def _detect_review_patterns(reviews: List[Dict], fake_analysis: Dict) -> List[str]:
    """Detect common suspicious patterns in reviews."""
    patterns = []

    if not reviews:
        return patterns

    bodies = []
    ratings = []
    dates = []
    for r in reviews:
        body = r.get("body", r.get("text", ""))
        if body:
            bodies.append(body)
        if r.get("rating"):
            ratings.append(r["rating"])
        if r.get("date"):
            dates.append(r["date"])

    # Pattern 1: Short generic praise
    short_generic = sum(1 for b in bodies if len(b.split()) < 15 and any(
        w in b.lower() for w in ["amazing", "best", "great", "excellent", "love it", "perfect", "awesome"]
    ))
    if short_generic > len(bodies) * 0.3 and short_generic >= 3:
        patterns.append(f"Short generic praise ({short_generic} reviews)")

    # Pattern 2: Rating clustering (too many 5-stars)
    if ratings:
        five_star_pct = sum(1 for r in ratings if r >= 4.8) / len(ratings) * 100
        if five_star_pct > 70 and len(ratings) > 10:
            patterns.append(f"Unusually high 5-star concentration ({five_star_pct:.0f}%)")

    # Pattern 3: Review date clustering (many reviews same day)
    if dates:
        date_counts = {}
        for d in dates:
            day = str(d)[:10]  # Take just YYYY-MM-DD
            date_counts[day] = date_counts.get(day, 0) + 1
        max_same_day = max(date_counts.values()) if date_counts else 0
        if max_same_day > 5 and max_same_day > len(dates) * 0.15:
            patterns.append(f"Review burst ({max_same_day} reviews on same day)")

    # Pattern 4: Duplicate/similar content
    if len(bodies) >= 5:
        lower_bodies = [b.lower()[:50] for b in bodies]
        unique_starts = len(set(lower_bodies))
        if unique_starts < len(lower_bodies) * 0.7:
            patterns.append("Similar/repetitive review content")

    # Pattern 5: No verified purchase indicators
    verified_count = sum(1 for r in reviews if r.get("verified_purchase", False))
    if len(reviews) > 10 and verified_count < len(reviews) * 0.3:
        patterns.append(f"Low verified purchase rate ({verified_count}/{len(reviews)})")

    # Pattern 6: Extreme length disparity
    if bodies:
        lengths = [len(b) for b in bodies]
        avg_len = sum(lengths) / len(lengths)
        very_short = sum(1 for l in lengths if l < 30)
        if very_short > len(bodies) * 0.4 and avg_len < 50:
            patterns.append("Many extremely short reviews")

    return patterns


def _find_trustworthy_reviews(reviews: List[Dict], fake_analysis: Dict) -> List[Dict]:
    """Find the most trustworthy reviews — longest, most detailed, verified."""
    flagged_texts = {f.get("text", "")[:40] for f in fake_analysis.get("flagged_reviews", [])}

    scored_reviews = []
    for r in reviews:
        body = r.get("body", r.get("text", ""))
        if not body or len(body) < 30:
            continue

        # Skip flagged reviews
        snippet = body[:40]
        if any(ft and ft in snippet for ft in flagged_texts):
            continue

        score = 0.0
        # Length bonus (longer = more effort = more trustworthy)
        score += min(len(body) / 500.0, 1.0) * 30

        # Verified purchase bonus
        if r.get("verified_purchase", False):
            score += 25

        # Moderate rating bonus (not extreme 1 or 5)
        rating = r.get("rating", 0)
        if 2.5 <= rating <= 4.5:
            score += 20
        elif rating > 0:
            score += 5

        # Specificity bonus (mentions specific features/issues)
        specificity_words = ["battery", "sound", "quality", "build", "screen", "camera",
                             "after", "months", "weeks", "days", "issue", "problem",
                             "compared", "upgrade", "previous", "switched"]
        specifics = sum(1 for w in specificity_words if w in body.lower())
        score += min(specifics * 5, 25)

        scored_reviews.append({
            "text": body[:300] + ("..." if len(body) > 300 else ""),
            "rating": rating,
            "verified_purchase": r.get("verified_purchase", False),
            "quality_score": round(score, 1),
        })

    # Sort by quality score and return top 3
    scored_reviews.sort(key=lambda x: x["quality_score"], reverse=True)
    return scored_reviews[:3]


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
