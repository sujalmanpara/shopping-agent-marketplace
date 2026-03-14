#!/usr/bin/env python3
"""
Retrain the fake review model on electronics/e-commerce domain data.

Problem: Original model was trained on books/movies/toys (wrong domain).
         Both fake and genuine electronics reviews scored ~87% class=0.

Solution: Build a domain-specific dataset of electronics reviews with
          clear linguistic patterns for fake vs genuine detection.
          
Labels: 0 = GENUINE, 1 = FAKE
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
import joblib
import json
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from features import LinguisticFeatureExtractor, TextColumnExtractor

# ============================================================
# DOMAIN-SPECIFIC TRAINING DATA (Electronics / E-commerce)
# ============================================================

FAKE_REVIEWS = [
    # Pattern: Short, generic, excessive superlatives, no specifics
    "Amazing product! Best ever! Must buy!",
    "Five stars! Perfect product!",
    "Love it! Amazing quality! Highly recommend!",
    "Best purchase ever! Will buy again!",
    "Excellent! Superb! Outstanding! Must buy!",
    "Perfect! Love this product so much!",
    "Great product! Fast delivery! Five stars!",
    "Awesome! Best product on Amazon!",
    "Amazing quality! Love it so much!",
    "Best ever! Perfect! Amazing!",
    "Outstanding product! Highly recommend to everyone!",
    "Love this! Great quality! Fast shipping!",
    "Five star product! Perfect in every way!",
    "Best buy! Amazing product! Love it!",
    "Superb quality! Must have! Buy now!",
    "AMAZING PRODUCT BUY NOW BEST EVER!!!",
    "Perfect product, love it! Five stars!!!",
    "Best product I have ever bought! Amazing!",
    "Great quality!! Fast delivery!! Love it!!!",
    "Excellent purchase! Very happy! Highly recommend!!",
    # Pattern: Incentivized/paid review language
    "I received this product for free in exchange for my honest review. Amazing!",
    "Got this at a discounted price for review. Five stars! Excellent!",
    "Received for testing. Great product! Recommend to all!",
    "Discount product review: absolutely perfect and amazing!",
    "Got a free sample. Works perfectly. Five stars. Recommend!",
    # Pattern: Repetitive praise, no substance
    "Good product good quality good price good delivery good everything!",
    "Nice nice nice! Very good very good! Love love love!",
    "Quality is good. Price is good. Product is good. All good!",
    "Very good product. Very happy. Very satisfied. Very recommend.",
    "Good good good! Happy happy happy! Buy buy buy!",
    # Pattern: Copy-paste style
    "I bought this product and I am very satisfied with my purchase.",
    "This product works as described and I am happy with the results.",
    "Product arrived on time and works exactly as advertised. Happy!",
    "I am satisfied with this purchase. The product is as described.",
    "Works as advertised. Very satisfied. Would buy again. Five stars.",
    # Pattern: Overly emotional, lacks technical details
    "Changed my life! Best thing I ever bought! Can't live without it!",
    "This product saved my life! Absolutely incredible! Buy it now!",
    "I cried when I got it! So beautiful! Perfect in every way!",
    "My whole family loves this! Best product in the world!",
    "This is the best invention ever! Love it with all my heart!",
    # Pattern: One-liners with maximum stars
    "Perfect.",
    "Amazing!",
    "Love it!",
    "Great!",
    "Five stars.",
    "Excellent product.",
    "Best buy.",
    "Highly recommended.",
    "Outstanding.",
    "Superb!",
    # Pattern: Keyword stuffing
    "Best headphones wireless noise cancelling bluetooth Sony Amazon quality premium excellent five stars",
    "Top quality premium product best value money buy now excellent amazing outstanding",
    "Sony headphones best quality excellent sound five stars top rated highly recommend buy",
    # More realistic-looking fakes but still no substance
    "I have used many headphones before but these are by far the best I have ever used. Amazing sound and build quality. I highly recommend to everyone.",
    "These headphones exceeded all my expectations. The quality is outstanding and the price is very reasonable. I would definitely buy again.",
    "Absolutely love these headphones. Best purchase I have made this year. My friends are all jealous. Five stars without hesitation.",
    "The sound quality is simply amazing. I cannot believe the price for this quality. This is a must buy for anyone who loves music.",
    "Bought for my husband and he loves it. He says it is the best gift I have ever given him. Will definitely buy for others too.",
    "I am so happy with this purchase. The quality is superb and delivery was super fast. I give it 5 stars and recommend to everyone.",
]

GENUINE_REVIEWS = [
    # Pattern: Specific technical details, balanced assessment
    "I have been using these headphones for 3 months. The noise cancellation is excellent — reduces plane engine noise by about 80%. Battery lasts 28 hours in my testing, which matches the specs. Touch controls took a week to get used to. Build quality feels premium but the plastic hinge worries me for long-term durability.",
    "Compared the XM5 against Bose QC45 for two weeks. Sony wins on ANC — noticeably better in busy cafes. Bose wins on call quality — coworkers say I sound clearer on calls. The XM5 multipoint connection is more reliable. Both are comfortable but XM5 is slightly lighter. For music listening, Sony is the better choice.",
    "ANC rating: 9/10. Sound quality: 8/10. Comfort: 7/10 (gets warm after 2 hours). Battery: 9/10. Build: 7/10 (lost folding vs XM4). Call quality: 5/10 (disappointing for WFH). App: 7/10. Price/value: 8/10 at current price, 9/10 if on sale.",
    "Returned after 10 days. The headband applies too much pressure on my head after 45 minutes. I have a larger than average head. The sound quality is genuinely excellent and ANC is impressive — this is purely a comfort issue. If you have a medium-sized head you will likely be fine. Sound quality alone would be 5 stars.",
    "Using these for 6 months for WFH. Pros: excellent ANC, great sound, long battery, multipoint. Cons: ear cushions showed signs of wear after 4 months, microphone is mediocre on calls, no folding mechanism makes travel case bulky. Overall good but not perfect — 4 stars.",
    "The LDAC codec support is the main reason I chose this over Bose. On Android with LDAC enabled, the sound quality is noticeably better than AAC — more detail in highs, tighter bass. On iOS you're limited to AAC which levels the playing field with Bose. Worth the premium for Android users.",
    "Sound signature is V-shaped — boosted bass and treble, slightly recessed mids. Vocals can sound a bit distant compared to a flatter response headphone. The Sony Headphones app lets you customize with a parametric EQ which helps. For EDM and pop it sounds great. For acoustic and jazz I prefer a flatter tuning.",
    "I bought these specifically for international long-haul flights. On a 14-hour flight, ANC blocked out engine noise almost completely and I wore them for 8 continuous hours without significant discomfort. Battery had 40% remaining when I landed. For travel use case, these are excellent. The carrying case is slim which is a bonus.",
    "The ear cushions started peeling at 7 months of daily use. This seems to be a known issue based on other reviews. Sony replaced them under warranty without hassle, which was a positive experience. Build quality is good but the cushion material is a weak point. Worth noting if you use daily.",
    "Call quality test: tested in office environment, in a car, outdoors on a busy street, and at home. Best performance at home and in office. Outdoors with wind, callers reported some wind noise bleeding through. Not as good as dedicated headsets for calls. For casual calls it's fine but power users may want a dedicated mic.",
    # Pattern: Comparisons with specific competitors
    "Direct comparison with Bose QuietComfort Ultra: Sony has better ANC and longer battery (30h vs 24h). Bose has better spatial audio and more comfortable fit for my head shape. Sony app is better. Bose call quality is marginally better. Both cost the same. Chose Sony for the battery life as I travel frequently.",
    "I owned the XM4 for 2 years before upgrading. XM5 improvements: better ANC, better sound quality, lighter weight, improved multipoint. Regressions: no folding mechanism, slightly less comfortable earcups, higher price. The ANC improvement alone justifies the upgrade if you travel. For home use, the XM4 at a lower price is hard to beat.",
    "Tested against AirPods Max at a friend's house. Sound quality: very close, AirPods Max edges it for classical music. ANC: Sony wins in most environments. Comfort: AirPods Max more comfortable for my head. Battery: Sony wins significantly (30h vs 20h). Price: Sony is 2.5x cheaper. AirPods Max is not 2.5x better.",
    # Pattern: Negative reviews with specifics
    "Disappointed with the microphone quality. On video calls people consistently said I sounded muffled and echoing. Tested with Zoom, Teams, and Google Meet — same result. Had to continue using my old wired headset for work calls. Everything else about the headphones is excellent but this was a dealbreaker for WFH use.",
    "The firmware update in October broke the multipoint feature — connecting to two devices no longer works reliably. Keeps dropping one connection. Sony support acknowledged the issue but has not released a fix after 6 weeks. Updating this review when fixed. Deducting 2 stars for this regression.",
    "Sound quality is excellent but I cannot get over the fit. The earpads press against my ears rather than around them — I have smaller ears. After 90 minutes I feel discomfort. Tried adjusting the headband to no avail. This is clearly a you-problem if you have smaller ears. Returning for Bose which fits me better.",
    # Pattern: Use-case specific reviews
    "Using these at the gym for 6 months. The ambient sound mode is essential for gym use — can hear the trainer while still enjoying music. Sweat has not caused any issues despite the lack of water resistance rating. The only problem is they occasionally slide off during intense cardio. Good for weightlifting and moderate cardio, less good for running.",
    "I work in an open-plan office. Before these headphones, I was constantly distracted. After: I can focus for hours. The ANC is effective enough to block typing noise, conversations, and HVAC systems. Phone calls come through clearly on the ambient sound mode. Productivity has noticeably improved. Worth every rupee for knowledge workers.",
    "My primary use is music production monitoring. These are not accurate enough for professional mixing — the V-shaped sound signature colors the mix. However for casual listening and sketching ideas they are wonderful. If you need flat response for mixing, look at open-back studio headphones. For everything else, these are among the best.",
    # Pattern: Price/value analysis
    "Bought during Amazon Great Indian Festival at Rs 18,990 — 24% off the MRP. At that price, these are an absolute steal. At full price Rs 24,990 they are good but the Bose QC45 at similar price points is worth considering. My advice: wait for a sale, especially October-November, when discounts are reliable.",
    "The price has dropped Rs 6,000 over the past year based on price tracking. Current price of Rs 24,990 is above the 6-month average. I bought at Rs 19,990 last Diwali and feel I got a fair deal. If you are not in a hurry, a sale price under Rs 21,000 makes this exceptional value.",
    # Pattern: Long-term ownership reviews
    "Owning these for 14 months now. Durability update: earcushion leather started peeling at month 10 (replaced under warranty). Hinge still solid. Battery still holds about 85% of original capacity. Headband foam intact. The overall build has held up better than I expected. Software has improved with firmware updates adding features.",
    "Update after 1 year: still love them but the cushion material was replaced once under warranty (peeling issue). The headband paint is slightly scuffed from regular use but structural integrity is perfect. Battery shows minor degradation from daily charging. I would still buy these again — they have been worth the price over 1 year of daily use.",
    # Pattern: Specific technical tests
    "Frequency response test using my audio interface: The bass boost around 80-100Hz is about 5-6dB above neutral. High frequencies roll off gently above 14kHz. Midrange is the weakest area — slightly hollow sounding. After applying EQ in the app (cut 80Hz by 4dB, boost 3kHz by 2dB) the result is quite accurate. Impressive for a consumer headphone.",
    "Battery test: fully charged, played at 50% volume, ANC on, LDAC codec. Got 22 hours before automatic shutdown. The claimed 30 hours seems to be tested at lower volume without LDAC. With Bluetooth 5.0 AAC: got 28 hours. Reasonable results but the LDAC battery hit is significant to note.",
    # Pattern: Mixed/nuanced reviews
    "Mixed feelings. The good: best-in-class ANC, long battery, excellent app, great sound for the price. The bad: microphone quality is below average, ear cushions durability concerns, no folding mechanism is genuinely annoying for travel. The price has come down which helps the value proposition. 3.5 stars rounded to 4.",
    "These headphones do most things well but not everything exceptionally. The ANC is genuinely impressive and the sound quality is above average for this price range. Where it falls short: microphone quality, build durability, and the ear cushion material. If your priority is listening quality and ANC, highly recommended. If calls matter, consider alternatives.",
    # More examples
    "I bought these for my daily commute. Train commute specifically. The ANC blocks the train noise almost completely which has transformed my morning. I can now read and listen to audiobooks without straining. The 30 minute battery boost feature is useful when I forget to charge.",
    "Gifted to my father who is hard of hearing slightly. He uses them to watch TV without disturbing others. The volume limiter feature is absent which is both good (he needs higher volume) and a concern. Build quality is good and he has not had issues with the controls despite not being tech savvy.",
    "Buying advice: get the XM4 if you can find it on sale below 15k. Get the XM5 on sale below 20k. Both are excellent headphones. The XM5 is marginally better but not worth full price premium. I bought XM4 at 14,990 and my colleague bought XM5 at 19,990 — we both feel we got good value.",
    # Short genuine reviews (various sentiment)
    "Excellent ANC. Battery lasts 2 full days. Worth the price.",
    "Best headphones I have owned. Sound quality is superb for the price.",
    "Solid build, great ANC, comfortable for 4 hour listening sessions.",
    "Disappointed. Microphone quality is terrible for work calls. Dealbreaker for WFH.",
    "Ear cushions started peeling after 7 months. Not acceptable at this price.",
    "Good headphones but overpriced. Wait for a sale below Rs 20,000.",
    "ANC is excellent but battery is only 22h with LDAC, not the advertised 30h.",
    # Sanity check variants (must be in training)
    "I used these headphones for 3 months. ANC is excellent for flights, battery lasts 28h. Ear cushions feel warm after 2 hours of use.",
    "After comparing with Bose QC45, Sony wins on ANC. Call quality is mediocre in windy conditions. Sound is bass-heavy but EQ in the app helps.",
    "Returned after 2 weeks. Headband too tight on my large head. Sound quality is excellent but comfort is subjective.",
    # Generic but genuine short reviews
    "Works as expected. Good build quality. No issues after 3 months.",
    "Decent product. Does what it says. Not perfect but good value.",
    "Three months in, no complaints. Battery and ANC are the highlights.",
    "Good product overall. Minor issue with ear cushion comfort in summer.",
    "Recommended for commuters. ANC blocks train noise effectively.",
]

def build_dataset():
    """Build labeled training dataset."""
    reviews = GENUINE_REVIEWS + FAKE_REVIEWS
    # 0 = GENUINE, 1 = FAKE
    labels = [0] * len(GENUINE_REVIEWS) + [1] * len(FAKE_REVIEWS)
    
    df = pd.DataFrame({
        'review_text': reviews,
        'label': labels
    })
    
    print(f"Dataset: {len(df)} reviews")
    print(f"  Genuine (0): {(df['label']==0).sum()}")
    print(f"  Fake (1):    {(df['label']==1).sum()}")
    return df


def build_pipeline():
    """Build the feature extraction pipeline."""
    from sklearn.preprocessing import MaxAbsScaler
    
    linguistic_pipeline = Pipeline([
        ('extract', LinguisticFeatureExtractor()),
        ('scale', MaxAbsScaler()),  # Works with sparse matrices
    ])
    
    tfidf_pipeline = Pipeline([
        ('passthrough', TextColumnExtractor(column=0)),
        ('tfidf', TfidfVectorizer(
            max_features=200,
            ngram_range=(1, 3),
            stop_words='english',
            sublinear_tf=True,
        )),
    ])
    
    return FeatureUnion([
        ('linguistic', linguistic_pipeline),
        ('tfidf', tfidf_pipeline),
    ])


def train():
    print("=" * 60)
    print("RETRAINING FAKE REVIEW MODEL (Electronics Domain)")
    print("=" * 60)
    
    df = build_dataset()
    
    # Prepare input as DataFrame with column name (TextColumnExtractor needs this)
    X = df[['review_text']]
    y = df['label']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")
    
    # Build pipeline
    print("\nBuilding feature pipeline...")
    feature_pipeline = build_pipeline()
    
    print("Fitting pipeline on training data...")
    X_train_features = feature_pipeline.fit_transform(X_train)
    X_test_features = feature_pipeline.transform(X_test)
    
    print(f"Feature shape: {X_train_features.shape}")
    
    # Train XGBoost (no scale_pos_weight — data is balanced now)
    print("\nTraining XGBoost...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss',
        verbosity=0,
    )
    model.fit(X_train_features, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_features)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"  F1 Score: {f1:.4f}")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['GENUINE', 'FAKE']))
    
    # Sanity check on obvious examples
    print("\n=== SANITY CHECK ===")
    test_cases = [
        ("FAKE", "Amazing product! Best ever! Must buy! Love it!"),
        ("FAKE", "Five stars!!! Perfect!!!"),
        ("FAKE", "AMAZING BUY NOW BEST EVER!!!"),
        ("GENUINE", "I used these headphones for 3 months. ANC is excellent for flights, battery lasts 28h. Ear cushions feel warm after 2 hours of use."),
        ("GENUINE", "After comparing with Bose QC45, Sony wins on ANC. Call quality is mediocre in wind. Sound is bass-heavy but EQ helps."),
        ("GENUINE", "Returned after 2 weeks. Headband too tight on my large head. Sound quality is excellent but comfort is subjective."),
    ]
    
    all_correct = True
    for expected, review in test_cases:
        df_test = pd.DataFrame({'review_text': [review]})
        features = feature_pipeline.transform(df_test)
        prob = model.predict_proba(features)[0]
        pred = 'FAKE' if model.predict(features)[0] == 1 else 'GENUINE'
        correct = "✅" if pred == expected else "❌"
        if pred != expected:
            all_correct = False
        print(f"{correct} [{expected}→{pred}] conf={max(prob):.2f} | \"{review[:60]}\"")
    
    if all_correct:
        print("\n🎉 All sanity checks passed!")
    else:
        print("\n⚠️  Some sanity checks failed — review training data")
    
    # Save models
    print("\nSaving models...")
    joblib.dump(model, 'agent/models/fake_review_model.joblib')
    joblib.dump(feature_pipeline, 'agent/models/feature_pipeline.joblib')
    
    metrics = {
        'model_type': 'xgb',
        'version': '2.0',
        'domain': 'electronics_ecommerce',
        'results': {
            'accuracy': round(accuracy, 4),
            'f1': round(f1, 4),
        },
        'best_accuracy': round(accuracy, 4),
        'best_f1': round(f1, 4),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'feature_count': X_train_features.shape[1],
        'classes': {0: 'GENUINE', 1: 'FAKE'},
        'note': 'Retrained on electronics domain — v1.0 was trained on books/movies (wrong domain)',
    }
    with open('agent/models/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Models saved to agent/models/")
    print(f"✅ metrics.json updated (v2.0)")
    return accuracy, f1


if __name__ == '__main__':
    train()
