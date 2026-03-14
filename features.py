# features.py — Custom feature extractors for the fake review ML model
# Required to unpickle feature_pipeline.joblib (trained with these classes)
# Model: XGBoost 90.2% accuracy, 216 features (16 linguistic + 200 TF-IDF)

import re
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class TextColumnExtractor(BaseEstimator, TransformerMixin):
    """Extract text from input array for TF-IDF pipeline."""
    
    def __init__(self, column=0):
        self.column = column
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        if hasattr(X, 'iloc'):
            return X.iloc[:, self.column] if X.ndim > 1 else X
        if isinstance(X, np.ndarray):
            return X.ravel() if X.ndim > 1 else X
        return np.array(X).ravel()


class LinguisticFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extract 16 linguistic features from review text.
    
    Features (must match training pipeline exactly):
    1.  review_length       — character count
    2.  word_count          — number of words
    3.  avg_word_length     — average word length
    4.  sentiment_score     — positive - negative word ratio
    5.  sentiment_subjectivity — subjective word ratio
    6.  exclamation_ratio   — exclamation marks per character
    7.  caps_ratio          — uppercase characters ratio
    8.  first_person_ratio  — first person pronouns ratio
    9.  adjective_ratio     — adjective-like words ratio
    10. adverb_ratio        — adverb-like words ratio
    11. noun_ratio          — noun-like words ratio
    12. unique_word_ratio   — unique words / total words
    13. readability_score   — simple readability (avg sentence len * avg word len)
    14. avg_sentence_length — words per sentence
    15. question_mark_ratio — question marks per character
    16. digit_ratio         — digits per character
    """
    
    FEATURE_NAMES = [
        'review_length', 'word_count', 'avg_word_length', 'sentiment_score',
        'sentiment_subjectivity', 'exclamation_ratio', 'caps_ratio',
        'first_person_ratio', 'adjective_ratio', 'adverb_ratio', 'noun_ratio',
        'unique_word_ratio', 'readability_score', 'avg_sentence_length',
        'question_mark_ratio', 'digit_ratio'
    ]
    
    # Word sets for feature extraction
    POSITIVE = {'good', 'great', 'love', 'best', 'excellent', 'amazing', 'perfect',
                'wonderful', 'fantastic', 'outstanding', 'superb', 'happy', 'satisfied',
                'recommend', 'impressive', 'brilliant', 'awesome', 'beautiful', 'nice'}
    NEGATIVE = {'bad', 'worst', 'hate', 'terrible', 'horrible', 'awful', 'poor',
                'disappointed', 'waste', 'broken', 'defective', 'return', 'refund',
                'cheap', 'useless', 'garbage', 'junk', 'annoying', 'regret'}
    SUBJECTIVE = {'think', 'feel', 'believe', 'opinion', 'seems', 'looks', 'appears',
                  'personally', 'honestly', 'probably', 'maybe', 'guess', 'suppose'}
    FIRST_PERSON = {'i', 'me', 'my', 'mine', 'myself', 'we', 'our', 'ours'}
    ADJECTIVES = {'good', 'great', 'bad', 'best', 'worst', 'nice', 'poor', 'excellent',
                  'amazing', 'terrible', 'beautiful', 'ugly', 'perfect', 'horrible',
                  'wonderful', 'awful', 'fantastic', 'outstanding', 'superb', 'mediocre',
                  'decent', 'solid', 'impressive', 'comfortable', 'lightweight', 'heavy',
                  'durable', 'cheap', 'expensive', 'loud', 'quiet', 'clear', 'crisp',
                  'smooth', 'rough', 'soft', 'hard', 'big', 'small', 'long', 'short',
                  'fast', 'slow', 'strong', 'weak', 'new', 'old'}
    ADVERBS = {'very', 'really', 'extremely', 'highly', 'absolutely', 'totally',
               'completely', 'quite', 'rather', 'fairly', 'incredibly', 'so',
               'definitely', 'certainly', 'particularly', 'especially', 'genuinely',
               'honestly', 'actually', 'basically', 'essentially'}
    NOUNS = {'product', 'quality', 'price', 'value', 'item', 'purchase', 'delivery',
             'packaging', 'material', 'design', 'feature', 'battery', 'screen',
             'sound', 'camera', 'performance', 'size', 'color', 'weight', 'brand',
             'warranty', 'service', 'support', 'money', 'time', 'day', 'week',
             'month', 'year', 'star', 'review', 'rating', 'order', 'box'}
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        from scipy.sparse import csr_matrix
        if isinstance(X, np.ndarray):
            X = X.ravel()
        elif hasattr(X, 'iloc'):
            # DataFrame input — extract the text column
            X = X.iloc[:, 0] if X.ndim > 1 else X.iloc[:, 0]
        features = []
        for text in X:
            text = str(text) if text else ""
            features.append(self._extract(text))
        result = np.array(features, dtype=np.float64)
        return csr_matrix(result)
    
    def _extract(self, text):
        """Extract 16 linguistic features."""
        if not text:
            return [0.0] * 16
        
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        words_lower = [w.lower().strip('.,!?;:()[]"\'') for w in words]
        
        # 1. review_length
        review_length = float(char_count)
        
        # 2. word_count
        wc = float(word_count)
        
        # 3. avg_word_length
        avg_word_length = np.mean([len(w) for w in words]) if words else 0.0
        
        # 4. sentiment_score (positive - negative ratio)
        pos = sum(1 for w in words_lower if w in self.POSITIVE)
        neg = sum(1 for w in words_lower if w in self.NEGATIVE)
        sentiment_score = (pos - neg) / max(word_count, 1)
        
        # 5. sentiment_subjectivity
        subj = sum(1 for w in words_lower if w in self.SUBJECTIVE)
        sentiment_subjectivity = subj / max(word_count, 1)
        
        # 6. exclamation_ratio
        exclamation_ratio = text.count('!') / max(char_count, 1)
        
        # 7. caps_ratio
        caps_ratio = sum(1 for c in text if c.isupper()) / max(char_count, 1)
        
        # 8. first_person_ratio
        fp = sum(1 for w in words_lower if w in self.FIRST_PERSON)
        first_person_ratio = fp / max(word_count, 1)
        
        # 9. adjective_ratio
        adj = sum(1 for w in words_lower if w in self.ADJECTIVES)
        adjective_ratio = adj / max(word_count, 1)
        
        # 10. adverb_ratio
        adv = sum(1 for w in words_lower if w in self.ADVERBS)
        adverb_ratio = adv / max(word_count, 1)
        
        # 11. noun_ratio
        noun = sum(1 for w in words_lower if w in self.NOUNS)
        noun_ratio = noun / max(word_count, 1)
        
        # 12. unique_word_ratio
        unique_word_ratio = len(set(words_lower)) / max(word_count, 1)
        
        # 13. readability_score (simplified Flesch-like)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sent_count = max(len(sentences), 1)
        avg_sent_len = word_count / sent_count
        readability_score = avg_sent_len * avg_word_length * 0.1  # Simplified
        
        # 14. avg_sentence_length
        avg_sentence_length = avg_sent_len
        
        # 15. question_mark_ratio
        question_mark_ratio = text.count('?') / max(char_count, 1)
        
        # 16. digit_ratio
        digit_ratio = sum(1 for c in text if c.isdigit()) / max(char_count, 1)
        
        return [
            review_length, wc, avg_word_length, sentiment_score,
            sentiment_subjectivity, exclamation_ratio, caps_ratio,
            first_person_ratio, adjective_ratio, adverb_ratio, noun_ratio,
            unique_word_ratio, readability_score, avg_sentence_length,
            question_mark_ratio, digit_ratio
        ]
    
    def get_feature_names_out(self):
        return self.FEATURE_NAMES
