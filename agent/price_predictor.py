# price_predictor.py — ML-based price prediction and sale event tracking

from typing import Dict, List
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

class PricePredictor:
    """
    ML-based price prediction for next 30 days
    Uses Polynomial Regression for better seasonal pattern capture
    """
    
    def __init__(self, use_polynomial: bool = True):
        """
        Args:
            use_polynomial: Use polynomial features (degree=2) for better accuracy
        """
        self.use_polynomial = use_polynomial
        self.model = None
        self.poly = PolynomialFeatures(degree=2) if use_polynomial else None
    
    def predict_next_30_days(self, price_data: Dict) -> Dict:
        """
        Predict prices for next 30 days using ML
        
        Args:
            price_data: Dict from get_price_history()
        
        Returns:
            Predictions with confidence scores
        """
        if not price_data.get('success'):
            return {
                "error": "No price data available",
                "confidence": 0
            }
        
        prices = [p['price'] for p in price_data['prices']]
        
        if len(prices) < 30:
            return {
                "error": "Not enough historical data (need 30+ days)",
                "confidence": 0
            }
        
        # Prepare training data
        X = np.array(range(len(prices))).reshape(-1, 1)
        y = np.array(prices)
        
        # Train model
        if self.use_polynomial:
            X_poly = self.poly.fit_transform(X)
            self.model = LinearRegression()
            self.model.fit(X_poly, y)
            r2_score = self.model.score(X_poly, y)
        else:
            self.model = LinearRegression()
            self.model.fit(X, y)
            r2_score = self.model.score(X, y)
        
        # Predict next 30 days
        future_X = np.array(range(len(prices), len(prices) + 30)).reshape(-1, 1)
        
        if self.use_polynomial:
            future_X_poly = self.poly.transform(future_X)
            predictions = self.model.predict(future_X_poly)
        else:
            predictions = self.model.predict(future_X)
        
        # Ensure predictions are positive
        predictions = np.maximum(predictions, 0)
        
        # Analyze predictions
        current_price = prices[-1]
        predicted_lowest = float(np.min(predictions))
        predicted_avg = float(np.mean(predictions))
        lowest_day = int(np.argmin(predictions)) + 1
        
        # Calculate drop probability
        drops = sum(1 for p in predictions if p < current_price)
        drop_prob = drops / len(predictions)
        
        # Expected savings
        if predicted_lowest < current_price:
            savings = current_price - predicted_lowest
            savings_pct = (savings / current_price) * 100
        else:
            savings = 0
            savings_pct = 0
        
        # Confidence based on R² score and trend stability
        confidence = self._calculate_confidence(r2_score, prices)
        
        return {
            "predicted_lowest": round(predicted_lowest, 2),
            "predicted_average": round(predicted_avg, 2),
            "best_day_to_buy": lowest_day,
            "drop_probability": round(drop_prob, 2),
            "expected_savings": round(savings, 2),
            "savings_percentage": round(savings_pct, 1),
            "confidence": round(confidence, 2),
            "model_type": "polynomial" if self.use_polynomial else "linear",
            "r2_score": round(r2_score, 2),
            "next_7_days": [round(p, 2) for p in predictions[:7]]
        }
    
    def _calculate_confidence(self, r2_score: float, prices: List[float]) -> float:
        """
        Calculate confidence score (0-1) based on:
        - R² score (model fit)
        - Price volatility (more stable = higher confidence)
        """
        # R² score component (0-1)
        r2_component = max(0, min(1, r2_score))
        
        # Volatility component
        if len(prices) > 30:
            recent = prices[-30:]
            volatility = np.std(recent) / np.mean(recent)
            
            # Lower volatility = higher confidence
            # Normalize: volatility 0-0.2 maps to confidence 1-0.5
            volatility_component = max(0.5, 1 - volatility * 2.5)
        else:
            volatility_component = 0.7
        
        # Weighted average
        confidence = (r2_component * 0.7) + (volatility_component * 0.3)
        
        return confidence
    
    def check_upcoming_sales(self) -> List[Dict]:
        """
        Check for major sale events in next 60 days
        
        Returns:
            List of upcoming sales with days away and expected discounts
        """
        today = datetime.now()
        
        SALE_EVENTS = {
            "Prime Day": {"month": 7, "day": 15, "discount": "15-25%"},
            "Black Friday": {"month": 11, "day": 24, "discount": "20-40%"},
            "Cyber Monday": {"month": 11, "day": 27, "discount": "15-30%"},
            "Prime Early Access": {"month": 10, "day": 10, "discount": "10-20%"},
            "Valentine's Day": {"month": 2, "day": 14, "discount": "10-15%"},
            "Memorial Day": {"month": 5, "day": 27, "discount": "10-20%"},
            "Labor Day": {"month": 9, "day": 2, "discount": "10-20%"},
        }
        
        upcoming = []
        
        for event_name, info in SALE_EVENTS.items():
            event_date = datetime(today.year, info['month'], info['day'])
            
            # If event already passed this year, check next year
            if event_date < today:
                event_date = datetime(today.year + 1, info['month'], info['day'])
            
            days_away = (event_date - today).days
            
            # Only include if within 60 days
            if 0 < days_away <= 60:
                upcoming.append({
                    "event": event_name,
                    "date": event_date.strftime("%B %d, %Y"),
                    "days_away": days_away,
                    "expected_discount": info['discount'],
                    "recommendation": f"WAIT {days_away} days for {info['discount']} off"
                })
        
        return sorted(upcoming, key=lambda x: x['days_away'])


def generate_final_recommendation(analysis: Dict, predictions: Dict, 
                                  upcoming_sales: List[Dict]) -> Dict:
    """
    Combine analysis, predictions, and sales calendar into final recommendation
    
    Args:
        analysis: From PriceAnalyzer
        predictions: From PricePredictor
        upcoming_sales: From check_upcoming_sales()
    
    Returns:
        Final recommendation with reasoning
    """
    # Default recommendation from analysis
    base_recommendation = analysis.get('recommendation', 'OKAY')
    
    # Check if there's a major sale coming soon
    major_sale_soon = None
    if upcoming_sales:
        nearest_sale = upcoming_sales[0]
        if nearest_sale['days_away'] <= 30:
            major_sale_soon = nearest_sale
    
    # Check ML predictions
    will_drop = predictions.get('drop_probability', 0) > 0.6  # >60% chance
    significant_savings = predictions.get('expected_savings', 0) > 20  # >$20
    
    # Decision logic
    if base_recommendation == "BUY NOW":
        # Already a good deal, but check if waiting is even better
        if major_sale_soon and major_sale_soon['days_away'] <= 14:
            return {
                "action": "WAIT",
                "reason": f"Good deal now, but {major_sale_soon['event']} in {major_sale_soon['days_away']} days",
                "alternative": f"Buy now if urgent, otherwise wait for {major_sale_soon['expected_discount']} discount"
            }
        else:
            return {
                "action": "BUY NOW",
                "reason": analysis['reasoning'],
                "confidence": "high"
            }
    
    elif base_recommendation == "WAIT":
        # Price is poor - recommend waiting
        if will_drop and significant_savings:
            return {
                "action": "WAIT",
                "reason": f"Price expected to drop ${predictions['expected_savings']:.0f} in {predictions['best_day_to_buy']} days",
                "predicted_price": predictions['predicted_lowest'],
                "confidence": predictions['confidence']
            }
        elif major_sale_soon:
            return {
                "action": "WAIT",
                "reason": f"Wait for {major_sale_soon['event']} in {major_sale_soon['days_away']} days ({major_sale_soon['expected_discount']} discount)",
                "confidence": "medium"
            }
        else:
            return {
                "action": "WAIT",
                "reason": "Price is above average - wait for drop",
                "confidence": "medium"
            }
    
    else:  # OKAY
        # Borderline case - provide options
        if will_drop and significant_savings:
            return {
                "action": "WAIT",
                "reason": f"Consider waiting {predictions['best_day_to_buy']} days to save ${predictions['expected_savings']:.0f}",
                "alternative": "Buy now if needed urgently",
                "confidence": predictions['confidence']
            }
        else:
            return {
                "action": "OKAY",
                "reason": "Fair price - buy now if needed, or wait for sales",
                "confidence": "medium"
            }
