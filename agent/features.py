"""Feature extraction pipeline for fake review detection."""
import re
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import StandardScaler
import nltk
from textblob import TextBlob
import textstat

# Download required NLTK data
for resource in ["punkt", "punkt_tab", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"]:
    try:
        nltk.data.find(f"tokenizers/{resource}" if "punkt" in resource else f"taggers/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

FIRST_PERSON = {"i", "me", "my", "mine", "myself", "we", "our", "ours", "ourselves"}


class LinguisticFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extract linguistic features from review text."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []
        for text in X:
            features.append(self._extract(str(text)))
        return pd.DataFrame(features)

    def _extract(self, text):
        words = text.split()
        word_count = len(words) if words else 1
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sent_count = len(sentences) if sentences else 1

        # POS tags
        try:
            tagged = nltk.pos_tag(words)
            pos_counts = {}
            for _, tag in tagged:
                pos_counts[tag] = pos_counts.get(tag, 0) + 1
            adj_count = sum(v for k, v in pos_counts.items() if k.startswith("JJ"))
            adv_count = sum(v for k, v in pos_counts.items() if k.startswith("RB"))
            noun_count = sum(v for k, v in pos_counts.items() if k.startswith("NN"))
        except Exception:
            adj_count = adv_count = noun_count = 0

        # Sentiment
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
        except Exception:
            sentiment = 0.0
            subjectivity = 0.5

        # Readability
        try:
            readability = textstat.flesch_reading_ease(text)
        except Exception:
            readability = 50.0

        # First person pronouns
        lower_words = [w.lower().strip(".,!?;:'\"") for w in words]
        first_person_count = sum(1 for w in lower_words if w in FIRST_PERSON)

        # Unique words
        unique_words = len(set(lower_words))

        # Exclamation and caps
        exclamation_count = text.count("!")
        caps_count = sum(1 for c in text if c.isupper())
        char_count = len(text) if text else 1

        return {
            "review_length": len(text),
            "word_count": word_count,
            "avg_word_length": np.mean([len(w) for w in words]) if words else 0,
            "sentiment_score": sentiment,
            "sentiment_subjectivity": subjectivity,
            "exclamation_ratio": exclamation_count / char_count,
            "caps_ratio": caps_count / char_count,
            "first_person_ratio": first_person_count / word_count,
            "adjective_ratio": adj_count / word_count,
            "adverb_ratio": adv_count / word_count,
            "noun_ratio": noun_count / word_count,
            "unique_word_ratio": unique_words / word_count,
            "readability_score": readability,
            "avg_sentence_length": word_count / sent_count,
            "question_mark_ratio": text.count("?") / char_count,
            "digit_ratio": sum(1 for c in text if c.isdigit()) / char_count,
        }

    def get_feature_names_out(self, input_features=None):
        return [
            "review_length", "word_count", "avg_word_length",
            "sentiment_score", "sentiment_subjectivity",
            "exclamation_ratio", "caps_ratio", "first_person_ratio",
            "adjective_ratio", "adverb_ratio", "noun_ratio",
            "unique_word_ratio", "readability_score", "avg_sentence_length",
            "question_mark_ratio", "digit_ratio",
        ]


class TextColumnExtractor(BaseEstimator, TransformerMixin):
    """Pass through text for TF-IDF."""
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return X


def build_feature_pipeline():
    """Build the full feature extraction pipeline."""
    linguistic = Pipeline([
        ("extract", LinguisticFeatureExtractor()),
        ("scale", StandardScaler()),
    ])

    tfidf = Pipeline([
        ("passthrough", TextColumnExtractor()),
        ("tfidf", TfidfVectorizer(max_features=200, ngram_range=(1, 3), stop_words="english", sublinear_tf=True)),
    ])

    combined = FeatureUnion([
        ("linguistic", linguistic),
        ("tfidf", tfidf),
    ])

    return combined


def extract_reasons(text, rating=None):
    """Extract human-readable reasons why a review might be fake."""
    extractor = LinguisticFeatureExtractor()
    feats = extractor._extract(str(text))
    reasons = []

    if feats["exclamation_ratio"] > 0.03:
        reasons.append("Excessive exclamation marks")
    if feats["caps_ratio"] > 0.15:
        reasons.append("Excessive capitalization")
    if feats["sentiment_score"] > 0.8:
        reasons.append("Extreme positive sentiment")
    elif feats["sentiment_score"] < -0.8:
        reasons.append("Extreme negative sentiment")
    if feats["sentiment_subjectivity"] > 0.8:
        reasons.append("Highly subjective language")
    if feats["unique_word_ratio"] < 0.5:
        reasons.append("Repetitive vocabulary")
    if feats["first_person_ratio"] > 0.1:
        reasons.append("Heavy first-person pronoun usage")
    if feats["word_count"] < 15:
        reasons.append("Very short review")
    if feats["adjective_ratio"] > 0.15:
        reasons.append("Unusually high adjective density")
    if feats["readability_score"] > 90:
        reasons.append("Overly simple language")
    if feats["digit_ratio"] < 0.005 and feats["word_count"] > 20:
        reasons.append("No specific numbers or measurements mentioned")

    # Sentiment-rating mismatch
    if rating is not None:
        if rating >= 4 and feats["sentiment_score"] < -0.2:
            reasons.append("Negative sentiment contradicts high rating")
        elif rating <= 2 and feats["sentiment_score"] > 0.2:
            reasons.append("Positive sentiment contradicts low rating")

    return reasons if reasons else ["No strong fake indicators detected"]
