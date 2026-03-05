# System Prompt: Real-Time Price Tracking & ML Price Prediction

## Objective
Build a production-ready price tracking and prediction system that tells users whether the current Amazon price is good, predicts future price drops, and recommends the best time to buy. Must integrate seamlessly with the existing shopping agent.

---

## Current State (What We Have Now)

**File**: `agent/scrapers.py` - `scrape_price_history()`

**Current Logic:**
```python
async def scrape_price_history(asin: str) -> Dict:
    """
    Current implementation:
    - Checks if near Prime Day (July 15)
    - Checks if near Black Friday (Nov 24)
    - Returns static prediction based on calendar dates
    - NO ACTUAL PRICE DATA
    """
    # Just date-based predictions like:
    # "WAIT 134 days for Prime Day (15-20% drop)"
```

**Problems:**
- ❌ No actual price history
- ❌ No idea if current price is good
- ❌ No ML predictions
- ❌ Just calendar date guessing
- ❌ Accuracy: ~30% (very unreliable)

---

## What We Need (Upgrade to 400% Better)

### **Part 1: Real Price History Scraping**

Scrape **CamelCamelCamel** or **Keepa** to get actual historical prices:

```python
async def scrape_price_history(asin: str, months: int = 6) -> Dict:
    """
    Scrape real price data from CamelCamelCamel
    
    Returns:
        {
            "current_price": 278.00,
            "average_price": 315.00,
            "lowest_price": 240.00,
            "highest_price": 349.99,
            "price_history": [
                {"date": "2024-09-01", "price": 315.00},
                {"date": "2024-10-01", "price": 289.99},
                ...
            ],
            "is_good_deal": True,  # Current < avg
            "deal_quality": "excellent"  # Within 10% of lowest
        }
    """
```

**Data Sources to Scrape:**
1. **CamelCamelCamel** - https://camelcamelcamel.com/product/{asin}
2. **Keepa** - https://keepa.com/#!product/1-{asin}
3. **Amazon Price History API** (if available)

**Required Data Points:**
- Last 6 months of daily prices
- Current price
- Historical average
- All-time lowest price
- Price trend (increasing/decreasing)

---

### **Part 2: Price Analysis Engine**

Analyze the price data to tell users if it's a good deal:

```python
class PriceAnalyzer:
    def analyze_current_price(self, history: Dict) -> Dict:
        """
        Compare current price to historical data
        
        Returns:
            {
                "current_vs_average": "-12%",  # 12% below average
                "current_vs_lowest": "+15%",   # 15% above lowest
                "deal_quality": "good",         # excellent/good/fair/poor
                "recommendation": "BUY NOW",    # BUY NOW / WAIT / OKAY
                "reasoning": "Price is 12% below 6-month average"
            }
        """
        current = history['current_price']
        avg = history['average_price']
        lowest = history['lowest_price']
        
        # Calculate percentages
        vs_avg = ((current - avg) / avg) * 100
        vs_lowest = ((current - lowest) / lowest) * 100
        
        # Determine deal quality
        if vs_lowest <= 10:
            deal = "excellent"
            recommendation = "BUY NOW"
        elif vs_avg <= 0:
            deal = "good"
            recommendation = "BUY NOW"
        elif vs_avg <= 10:
            deal = "fair"
            recommendation = "OKAY"
        else:
            deal = "poor"
            recommendation = "WAIT"
        
        return {
            "current_vs_average": f"{vs_avg:+.1f}%",
            "current_vs_lowest": f"{vs_lowest:+.1f}%",
            "deal_quality": deal,
            "recommendation": recommendation,
            "reasoning": f"Price is {abs(vs_avg):.0f}% {'below' if vs_avg < 0 else 'above'} average"
        }
```

---

### **Part 3: ML Price Prediction**

Use machine learning to predict future prices (next 30 days):

```python
from sklearn.linear_model import LinearRegression
import numpy as np

class PricePredictor:
    """
    Predict future prices using:
    - Historical trend
    - Seasonal patterns
    - Sale event calendars
    """
    
    def predict_next_30_days(self, price_history: List[float]) -> Dict:
        """
        Predict prices for next 30 days
        
        Returns:
            {
                "predicted_lowest": 245.00,
                "predicted_average": 285.00,
                "drop_probability": 0.75,  # 75% chance of drop
                "best_day_to_buy": 18,     # Day 18 (predicted lowest)
                "expected_savings": "$33",  # vs current price
                "confidence": 0.82          # Model confidence
            }
        """
        # Train model on historical data
        X = np.array(range(len(price_history))).reshape(-1, 1)
        y = np.array(price_history)
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next 30 days
        future_days = np.array(range(len(price_history), len(price_history) + 30)).reshape(-1, 1)
        predictions = model.predict(future_days)
        
        # Find best day to buy
        lowest_day = np.argmin(predictions)
        lowest_price = predictions[lowest_day]
        
        # Calculate drop probability
        current_price = price_history[-1]
        drop_prob = sum(1 for p in predictions if p < current_price) / len(predictions)
        
        return {
            "predicted_lowest": round(lowest_price, 2),
            "predicted_average": round(predictions.mean(), 2),
            "drop_probability": round(drop_prob, 2),
            "best_day_to_buy": lowest_day + 1,
            "expected_savings": f"${round(current_price - lowest_price, 2)}",
            "confidence": 0.75  # Based on R² score
        }
```

---

### **Part 4: Sale Event Calendar**

Enhance predictions with known sale events:

```python
from datetime import datetime, timedelta

SALE_EVENTS = {
    "Prime Day": {"month": 7, "day": 15, "discount": "15-25%"},
    "Black Friday": {"month": 11, "day": 24, "discount": "20-40%"},
    "Cyber Monday": {"month": 11, "day": 27, "discount": "15-30%"},
    "Prime Early Access": {"month": 10, "day": 10, "discount": "10-20%"},
}

def check_upcoming_sales(current_date: datetime) -> List[Dict]:
    """
    Find upcoming sale events in next 60 days
    
    Returns:
        [
            {
                "event": "Black Friday",
                "days_away": 42,
                "expected_discount": "20-40%",
                "recommendation": "WAIT 42 days for 30% off"
            }
        ]
    """
    upcoming = []
    
    for event, info in SALE_EVENTS.items():
        event_date = datetime(current_date.year, info['month'], info['day'])
        
        # Check if event is in next 60 days
        days_diff = (event_date - current_date).days
        
        if 0 < days_diff < 60:
            upcoming.append({
                "event": event,
                "days_away": days_diff,
                "expected_discount": info['discount'],
                "recommendation": f"WAIT {days_diff} days for {info['discount']} off"
            })
    
    return sorted(upcoming, key=lambda x: x['days_away'])
```

---

## Expected Output (User-Facing)

When user analyzes a product, they see:

```
📈 PRICE DROP PROPHET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Price: $278.00

📊 PRICE HISTORY (6 months)
Average Price: $315.00
Lowest Price: $240.00 (Oct 15, 2024)
Highest Price: $349.99 (Aug 1, 2024)

✅ DEAL QUALITY: GOOD
Current price is 12% below average ✨

📉 PRICE TREND: Decreasing
Prices have dropped 8% in last 30 days

🔮 30-DAY PREDICTION (ML)
Predicted Lowest: $245.00 (in 18 days)
Drop Probability: 75%
Expected Savings: $33 if you wait

📅 UPCOMING SALES
Black Friday in 42 days (20-40% discount)

🎯 RECOMMENDATION: WAIT 18 DAYS
Price likely to drop to $245 (12% savings)
Or wait 42 days for Black Friday (30% discount)

Confidence: 82% 🤖
```

---

## Technical Requirements

### **Scraping Requirements:**
1. Must handle both CamelCamelCamel AND Keepa (fallback)
2. Use StealthyFetcher to avoid bot detection
3. Parse price charts/graphs from HTML
4. Handle missing data gracefully
5. Cache results for 24 hours (avoid re-scraping)

### **ML Model Requirements:**
1. Use scikit-learn (LinearRegression or better)
2. Train on at least 180 days of price data
3. Predict next 30 days
4. Include confidence scores
5. Handle seasonal patterns

### **Performance:**
- Scraping: <5 seconds
- ML Prediction: <100ms
- Total: <6 seconds for full analysis
- Cache: 24 hours

### **Error Handling:**
- If scraping fails → fall back to calendar-based (current system)
- If not enough data → use simpler heuristics
- Always return something (never crash)

---

## Deliverables Needed

### **1. Price Scraper**
```python
# agent/price_scraper.py
async def scrape_camelcamelcamel(asin: str) -> Dict:
    """Scrape CamelCamelCamel for price history"""

async def scrape_keepa(asin: str) -> Dict:
    """Fallback: Scrape Keepa"""

async def get_price_history(asin: str, months: int = 6) -> Dict:
    """Main function: tries CCC, then Keepa, then fallback"""
```

### **2. Price Analyzer**
```python
# agent/price_analyzer.py
class PriceAnalyzer:
    def analyze_current_price(self, history: Dict) -> Dict:
        """Compare current price to historical data"""
    
    def calculate_deal_quality(self, current, avg, lowest) -> str:
        """Determine if it's a good deal"""
```

### **3. Price Predictor**
```python
# agent/price_predictor.py
class PricePredictor:
    def predict_next_30_days(self, price_history: List[float]) -> Dict:
        """ML-based price prediction"""
    
    def check_upcoming_sales(self) -> List[Dict]:
        """Check sale event calendar"""
```

### **4. Integration**
```python
# agent/scrapers.py (updated)
async def scrape_price_history(asin: str) -> Dict:
    """
    NEW VERSION:
    1. Get real price history
    2. Analyze current deal quality
    3. Predict future prices
    4. Check upcoming sales
    5. Generate recommendation
    """
    # Get data
    history = await get_price_history(asin, months=6)
    
    # Analyze
    analysis = PriceAnalyzer().analyze_current_price(history)
    prediction = PricePredictor().predict_next_30_days(history['prices'])
    sales = check_upcoming_sales(datetime.now())
    
    # Combine
    return {
        "has_data": True,
        "current_price": history['current_price'],
        "analysis": analysis,
        "prediction": prediction,
        "upcoming_sales": sales,
        "recommendation": generate_final_recommendation(analysis, prediction, sales)
    }
```

### **5. Dependencies**
```
scikit-learn>=1.3.0  # ML predictions
numpy>=1.24.0        # Numerical operations
pandas>=2.0.0        # Data handling (optional)
```

---

## Test Cases

### **Test 1: Price Below Average**
```python
# Product currently at $278, average is $315
result = await scrape_price_history("B08N5WRWNW")
assert result['analysis']['deal_quality'] == "good"
assert result['analysis']['recommendation'] == "BUY NOW"
```

### **Test 2: Price Near All-Time Low**
```python
# Current $245, lowest ever $240
result = await scrape_price_history("B08N5WRWNW")
assert result['analysis']['deal_quality'] == "excellent"
assert result['prediction']['drop_probability'] < 0.3  # Unlikely to drop more
```

### **Test 3: Upcoming Sale Event**
```python
# Black Friday in 30 days
result = await scrape_price_history("B08N5WRWNW")
assert len(result['upcoming_sales']) > 0
assert "Black Friday" in result['upcoming_sales'][0]['event']
assert result['recommendation']['action'] == "WAIT"
```

---

## Success Criteria

✅ Accuracy: 80%+ predictions correct (price drops when predicted)
✅ Speed: <6 seconds total (scraping + analysis + ML)
✅ Reliability: Works for 95%+ of Amazon products
✅ User Value: Users save average 15%+ by following recommendations
✅ Better than current: 400% improvement over calendar-based guessing

---

## Questions to Answer

1. Should we scrape both CamelCamelCamel AND Keepa for redundancy?
2. How to handle products with <6 months of price data?
3. Should we use more advanced ML models (ARIMA, Prophet)?
4. Do we cache price data? For how long?
5. Should we track competitor prices (Walmart, Target)?

---

## Example Scraping Code Needed

```python
async def scrape_camelcamelcamel(asin: str) -> Dict:
    """
    Scrape CamelCamelCamel for price history
    URL: https://camelcamelcamel.com/product/{asin}
    
    Extract:
    - Current price
    - Price chart data (JSON embedded in page)
    - Historical prices (last 6 months)
    - Lowest/highest prices
    """
    url = f"https://camelcamelcamel.com/product/{asin}"
    
    # Use StealthyFetcher
    response = await asyncio.to_thread(
        StealthyFetcher.fetch,
        url,
        headless=True,
        network_idle=True
    )
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract price chart data (usually in JavaScript variable)
    # Example: var priceData = [[timestamp, price], [timestamp, price], ...]
    
    # Parse and return
    return {
        "current_price": extract_current_price(soup),
        "prices": extract_price_history(soup),
        "average_price": calculate_average(prices),
        "lowest_price": min(prices),
        "highest_price": max(prices)
    }
```

---

## Priority: HIGH 🔥

This is the **#1 recommended upgrade** because:
- ✅ Low effort (1-2 days)
- ✅ High user value (save 15-30%)
- ✅ Easy to test
- ✅ Immediate visible impact

Users will instantly see real price data instead of calendar guessing!

---

End of system prompt. Provide complete implementation with all files and working code.
