# System Prompt: ML Fake Review Detection Model

## Objective
Design and implement a production-ready Machine Learning model for detecting fake Amazon product reviews with 90%+ accuracy. The model should be lightweight, fast, and deployable in a Python FastAPI marketplace agent.

---

## Requirements

### 1. Model Specifications
- **Algorithm**: RandomForestClassifier (or better alternative)
- **Accuracy Target**: 90%+ on test set
- **Inference Speed**: <100ms per review batch (10 reviews)
- **Model Size**: <50MB for deployment
- **Language**: Python 3.10+
- **Framework**: scikit-learn (or PyTorch/TensorFlow if justified)

### 2. Feature Engineering
Extract 20+ features from each review. Must include:

#### Text Features:
1. Review length (word count)
2. Character count
3. Sentence count
4. Average word length
5. Exclamation mark count
6. Question mark count
7. ALL CAPS words count
8. Repeated punctuation (e.g., "!!!", "???")
9. Lexical diversity (unique words / total words)
10. Reading level (Flesch-Kincaid score)

#### Content Features:
11. Generic phrase count (e.g., "best product ever", "highly recommend")
12. Superlative count (e.g., "amazing", "perfect", "worst")
13. Personal pronoun usage (I, me, my)
14. Technical term count (product-specific keywords)
15. Emoji count
16. URL presence (yes/no)

#### Review Metadata:
17. Star rating (1-5)
18. Verified purchase (boolean)
19. Review helpfulness score
20. Review age (days since posted)
21. Reviewer total reviews
22. Reviewer account age
23. Time between purchase and review

#### Pattern Features:
24. Rating vs text sentiment mismatch
25. Duplicate/near-duplicate text detection
26. Burst posting pattern (multiple reviews same day)

### 3. Dataset Requirements
- **Training Data**: 10,000+ labeled reviews (50% real, 50% fake)
- **Test Data**: 2,000+ labeled reviews (separate from training)
- **Data Sources**: 
  - Amazon reviews dataset (labeled)
  - Fake review datasets from research papers
  - Manual labeling if needed

**Suggested Datasets**:
- [Yelp Fake Review Dataset](https://www.kaggle.com/datasets/rtatman/deceptive-opinion-spam-corpus)
- [Amazon Review Dataset](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/)
- [Fake Reviews Detection Dataset](https://www.kaggle.com/datasets/mexwell/fake-reviews-detection)

### 4. Model Training Pipeline
Provide complete code for:
1. Data preprocessing
2. Feature extraction
3. Model training
4. Hyperparameter tuning (GridSearchCV or Optuna)
5. Model evaluation (accuracy, precision, recall, F1, ROC-AUC)
6. Model serialization (pickle or joblib)

### 5. Production Deployment
Must include:
- Pre-trained model file (`.pkl` or `.joblib`)
- Feature extraction function
- Prediction function (single review + batch)
- Error handling
- Fallback to rule-based if model fails

---

## Expected Output

### Part 1: Training Code
```python
# train_fake_review_model.py
# Complete training pipeline with:
# - Data loading
# - Feature engineering
# - Model training
# - Evaluation metrics
# - Model saving
```

### Part 2: Feature Extraction
```python
# feature_extraction.py
def extract_features(review: Dict) -> np.array:
    """
    Extract 20+ features from a review.
    
    Args:
        review: Dict with keys:
            - body (str): Review text
            - rating (float): 1-5 stars
            - date (str): ISO date
            - verified (bool): Verified purchase?
            - helpful (int): Helpfulness votes
    
    Returns:
        np.array: Feature vector of length 20+
    """
    features = []
    
    # Text features
    features.append(len(review['body'].split()))  # Word count
    features.append(len(review['body']))  # Char count
    # ... (implement all 20+ features)
    
    return np.array(features)
```

### Part 3: Prediction Function
```python
# fake_review_detector.py
class FakeReviewDetector:
    def __init__(self, model_path: str):
        """Load pre-trained model"""
        self.model = joblib.load(model_path)
    
    async def predict(self, reviews: List[Dict]) -> Dict:
        """
        Predict fake probability for each review.
        
        Returns:
            {
                "fake_reviews": [...],  # Reviews with >70% fake probability
                "fake_percentage": 0.23,  # 23% are fake
                "confidence": 0.87,  # Model confidence
                "risk_level": "medium"  # low/medium/high
            }
        """
        pass
```

### Part 4: Integration Code
```python
# agent/analyzers.py (replacement)
from .fake_review_detector import FakeReviewDetector

# Initialize model once
detector = FakeReviewDetector("models/fake_review_model.pkl")

async def analyze_fake_reviews(reviews: List[Dict]) -> Dict:
    """New ML-powered version"""
    if not reviews:
        return {"score": 0, "risk": "unknown"}
    
    result = await detector.predict(reviews)
    return result
```

---

## Deliverables Checklist

Please provide:

- [ ] **Training script** (`train_fake_review_model.py`)
- [ ] **Feature extraction** (`feature_extraction.py`)
- [ ] **Pre-trained model** (`fake_review_model.pkl` or `.joblib`)
- [ ] **Prediction class** (`fake_review_detector.py`)
- [ ] **Integration code** (updated `analyzers.py`)
- [ ] **Requirements** (new dependencies: `scikit-learn`, `joblib`, `nltk`, etc.)
- [ ] **Evaluation report** (accuracy, precision, recall, F1, confusion matrix)
- [ ] **Sample predictions** (5 real reviews + 5 fake reviews with probabilities)
- [ ] **Model size** (in MB)
- [ ] **Inference speed** (ms per review)

---

## Constraints & Preferences

### Must Have:
- ✅ 90%+ accuracy on test set
- ✅ <100ms inference for 10 reviews
- ✅ Deployable in FastAPI without GPU
- ✅ Works with async/await Python
- ✅ Graceful fallback if model errors

### Nice to Have:
- ✅ Explainable predictions (feature importance)
- ✅ Confidence scores per prediction
- ✅ Batch processing optimized
- ✅ Model versioning support
- ✅ A/B testing capability

### Avoid:
- ❌ Deep learning models requiring GPU
- ❌ Models >100MB size
- ❌ External API dependencies
- ❌ Real-time model retraining

---

## Testing Requirements

Provide test cases:

### Test Case 1: Obvious Fake Review
```python
fake_review = {
    "body": "Amazing!!! Best product ever!!! Highly recommend!!! 5 stars!!!",
    "rating": 5.0,
    "date": "2024-03-01",
    "verified": False,
    "helpful": 0
}
# Expected: fake_probability > 0.9
```

### Test Case 2: Obvious Real Review
```python
real_review = {
    "body": "I bought this headset for gaming. Audio quality is decent but the mic picks up too much background noise. Battery lasts about 6 hours. For the price, it's acceptable but not amazing.",
    "rating": 3.0,
    "date": "2024-01-15",
    "verified": True,
    "helpful": 24
}
# Expected: fake_probability < 0.3
```

### Test Case 3: Batch Prediction
```python
reviews = [fake_review, real_review, ...]  # 10 reviews
result = await detector.predict(reviews)
# Expected: completes in <100ms, returns detailed results
```

---

## Performance Metrics Target

| Metric | Target | Current (Rule-Based) |
|--------|--------|----------------------|
| Accuracy | **90%+** | ~60% |
| Precision | **85%+** | ~50% |
| Recall | **85%+** | ~55% |
| F1 Score | **85%+** | ~52% |
| ROC-AUC | **0.90+** | ~0.65 |
| Inference (10 reviews) | **<100ms** | <10ms |

---

## Example Use Case

User inputs Amazon product URL → Agent scrapes 100 reviews → Model predicts:

```
🕵️ FAKE REVIEW DETECTION (ML-Powered)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Reviews Analyzed: 100
Fake Reviews Detected: 23 (23%)

Risk Level: 🟡 MEDIUM

Top Suspicious Patterns:
  • 18 reviews posted on same day (Feb 1, 2024)
  • 12 reviews use generic phrases ("best product ever")
  • 8 reviews from accounts with <5 total reviews

Model Confidence: 87%

⚠️ Recommendation: This product has moderate fake review risk. 
Cross-reference with Reddit/YouTube before buying.
```

---

## Questions to Consider

1. Should we use ensemble methods (Random Forest + XGBoost)?
2. Do we need separate models for different review lengths?
3. Should we detect review bombing (coordinated campaigns)?
4. How to handle non-English reviews?
5. Should we update model periodically with new data?

---

## Success Criteria

Model is considered successful if:
1. ✅ Accuracy ≥ 90% on test set
2. ✅ Works in production without errors for 1 week
3. ✅ User feedback: "fake review detection seems accurate"
4. ✅ Better than current rule-based system (60% accuracy)
5. ✅ Deployment size <50MB
6. ✅ No performance degradation (<100ms latency)

---

## References & Resources

### Research Papers:
- [Fake Review Detection on Amazon](https://arxiv.org/abs/2005.10244)
- [Machine Learning for Fake Review Detection](https://ieeexplore.ieee.org/document/9261141)

### Datasets:
- [Amazon Review Dataset (McAuley)](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/)
- [Yelp Fake Reviews](https://www.kaggle.com/datasets/rtatman/deceptive-opinion-spam-corpus)

### Libraries:
- scikit-learn (RandomForestClassifier, GridSearchCV)
- NLTK (text processing)
- TextBlob (sentiment analysis)
- joblib (model serialization)

---

## Final Notes

- Focus on **production-ready** code, not research quality
- Optimize for **speed** and **accuracy**, not perfect precision
- Must work with **limited data** (Amazon reviews only)
- Should **fail gracefully** if edge cases occur
- Provide **clear documentation** for integration

---

**IMPORTANT**: This model will be used in a paid marketplace agent ($9.99/month). Quality and reliability are critical. Users expect 90%+ accuracy.

---

End of system prompt. Provide complete implementation with all files listed in deliverables.
