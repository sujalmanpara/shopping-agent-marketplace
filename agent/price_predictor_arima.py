# price_predictor_arima.py — Production ARIMA price prediction with sale calendar
# Phase 2: predict_with_context(), sale calendar, edge case handling

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    print("⚠️  statsmodels not installed. Install with: pip install statsmodels")

from .constants import SALE_CALENDAR, PRICE_DROP_THRESHOLD


class ARIMAPricePredictor:
    """
    ARIMA (AutoRegressive Integrated Moving Average) model for price prediction.
    
    Phase 2 improvements:
    - predict_with_context() for production-ready output
    - Sale calendar integration (India + US)
    - Edge case handling (<10 data points, stable prices)
    - Actionable buy/wait recommendations
    """
    
    def __init__(self, order: tuple = (5, 1, 0)):
        self.order = order
        self.model = None
        self.fitted_model = None
    
    def predict_next_30_days(self, price_data: Dict) -> Dict:
        """
        Original method — kept for backward compatibility.
        Predict prices using ARIMA model.
        """
        if not ARIMA_AVAILABLE:
            return {"error": "ARIMA not available (statsmodels not installed)", "confidence": 0}
        
        if not price_data.get('success') and not price_data.get('prices'):
            return {"error": "No price data available", "confidence": 0}
        
        prices = [p['price'] for p in price_data.get('prices', [])]
        
        if len(prices) < 60:
            return {"error": "ARIMA needs 60+ days of data", "confidence": 0}
        
        try:
            self.model = ARIMA(prices, order=self.order)
            self.fitted_model = self.model.fit()
            
            forecast_result = self.fitted_model.forecast(steps=30)
            predictions = forecast_result.values if hasattr(forecast_result, 'values') else np.array(forecast_result)
            predictions = np.maximum(predictions, 0)
            
            forecast_df = self.fitted_model.get_forecast(steps=30)
            conf_int = forecast_df.conf_int()
            
            current_price = prices[-1]
            predicted_lowest = float(np.min(predictions))
            predicted_avg = float(np.mean(predictions))
            lowest_day = int(np.argmin(predictions)) + 1
            
            drops = sum(1 for p in predictions if p < current_price)
            drop_prob = drops / len(predictions)
            
            if predicted_lowest < current_price:
                savings = current_price - predicted_lowest
                savings_pct = (savings / current_price) * 100
            else:
                savings = 0
                savings_pct = 0
            
            aic = self.fitted_model.aic
            confidence = self._calculate_confidence(aic, prices)
            
            return {
                "predicted_lowest": round(predicted_lowest, 2),
                "predicted_average": round(predicted_avg, 2),
                "best_day_to_buy": lowest_day,
                "drop_probability": round(drop_prob, 2),
                "expected_savings": round(savings, 2),
                "savings_percentage": round(savings_pct, 1),
                "confidence": round(confidence, 2),
                "model_type": "ARIMA",
                "model_order": f"ARIMA{self.order}",
                "aic": round(aic, 2),
                "next_7_days": [round(float(p), 2) for p in predictions[:7]],
                "confidence_intervals": {
                    "lower_7_days": [round(float(c), 2) for c in conf_int.iloc[:7, 0]],
                    "upper_7_days": [round(float(c), 2) for c in conf_int.iloc[:7, 1]]
                }
            }
        
        except Exception as e:
            return {"error": f"ARIMA prediction failed: {str(e)}", "confidence": 0}
    
    def predict_with_context(self, keepa_data: Dict, current_price: float = None, country: str = "IN") -> Dict:
        """
        Production-ready price prediction with full context.
        
        Combines ARIMA forecasting with sale calendar and actionable recommendations.
        Handles edge cases: sparse data, stable prices, no ARIMA.
        
        Args:
            keepa_data: Price history from Keepa API (or api_layer format)
            current_price: Current product price (overrides Keepa's latest if provided)
            country: "IN" or "US" for sale calendar
        
        Returns:
            {
                "predicted_prices": list of next 30 days,
                "predicted_lowest": float,
                "predicted_lowest_date": str (ISO date),
                "drop_probability": float (0-1),
                "current_vs_average": str ("above_average" | "below_average" | "at_average"),
                "best_action": str ("BUY_NOW" | "WAIT_X_DAYS" | "PRICE_IS_LOW"),
                "savings_estimate": float,
                "confidence": float (0-1),
                "upcoming_sales": list of upcoming sales,
                "method": str ("arima" | "sale_calendar_only" | "stable_price"),
                "explanation": str,
            }
        """
        now = datetime.now()
        prices_raw = keepa_data.get("prices", [])
        data_points = len(prices_raw)
        
        # Extract price values
        price_values = [p.get("price", p) if isinstance(p, dict) else p for p in prices_raw]
        price_values = [p for p in price_values if isinstance(p, (int, float)) and p > 0]
        
        if current_price is None and price_values:
            current_price = price_values[-1]
        elif current_price is None:
            current_price = keepa_data.get("current_price", 0)
        
        # Calculate basic stats from history
        avg_price = keepa_data.get("average_price")
        if avg_price is None and price_values:
            avg_price = sum(price_values) / len(price_values)
        
        lowest_price = keepa_data.get("lowest_price")
        if lowest_price is None and price_values:
            lowest_price = min(price_values)
        
        highest_price = keepa_data.get("highest_price")
        if highest_price is None and price_values:
            highest_price = max(price_values)
        
        # Get upcoming sales
        upcoming_sales = _get_upcoming_sales(country, now)
        
        # ── Edge Case: Very sparse data (<10 points) ──
        if data_points < 10:
            return self._sparse_data_prediction(
                current_price, avg_price, lowest_price, upcoming_sales, now
            )
        
        # ── Edge Case: Stable price (no change in 6 months) ──
        if price_values and len(price_values) >= 10:
            price_std = float(np.std(price_values))
            price_mean = float(np.mean(price_values))
            if price_mean > 0 and (price_std / price_mean) < 0.02:
                return self._stable_price_prediction(
                    current_price, avg_price, lowest_price, upcoming_sales, now
                )
        
        # ── Normal case: ARIMA prediction ──
        if ARIMA_AVAILABLE and data_points >= 60:
            arima_result = self._run_arima(price_values, current_price, now)
            if arima_result and not arima_result.get("error"):
                return self._enrich_with_context(
                    arima_result, current_price, avg_price, lowest_price, upcoming_sales, country, now
                )
        
        # ── Fallback: Statistical prediction (10-59 data points) ──
        return self._statistical_prediction(
            price_values, current_price, avg_price, lowest_price, upcoming_sales, now
        )
    
    def _run_arima(self, price_values: List[float], current_price: float, now: datetime) -> Optional[Dict]:
        """Run ARIMA model and return raw predictions."""
        try:
            model = ARIMA(price_values, order=self.order)
            fitted = model.fit()
            
            forecast_result = fitted.forecast(steps=30)
            predictions = forecast_result.values if hasattr(forecast_result, 'values') else np.array(forecast_result)
            predictions = np.maximum(predictions, 0)
            
            aic = fitted.aic
            confidence = self._calculate_confidence(aic, price_values)
            
            return {
                "predictions": [round(float(p), 2) for p in predictions],
                "predicted_lowest": round(float(np.min(predictions)), 2),
                "predicted_lowest_day": int(np.argmin(predictions)) + 1,
                "predicted_avg": round(float(np.mean(predictions)), 2),
                "confidence": round(confidence, 2),
                "aic": round(aic, 2),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _enrich_with_context(self, arima_result: Dict, current_price: float, avg_price: float,
                              lowest_price: float, upcoming_sales: List[Dict], country: str, now: datetime) -> Dict:
        """Enrich ARIMA predictions with context and recommendations."""
        predictions = arima_result["predictions"]
        predicted_lowest = arima_result["predicted_lowest"]
        lowest_day = arima_result["predicted_lowest_day"]
        confidence = arima_result["confidence"]
        
        # Calculate metrics
        drop_prob = sum(1 for p in predictions if p < current_price * (1 - PRICE_DROP_THRESHOLD)) / len(predictions)
        savings_estimate = max(0, current_price - predicted_lowest)
        savings_pct = (savings_estimate / current_price * 100) if current_price > 0 else 0
        
        # Current vs average
        current_vs_avg = _compare_to_average(current_price, avg_price)
        
        # Determine best action
        best_action, explanation = _determine_best_action(
            current_price, predicted_lowest, lowest_day, drop_prob,
            savings_pct, current_vs_avg, upcoming_sales, lowest_price, now
        )
        
        # Predicted lowest date
        predicted_lowest_date = (now + timedelta(days=lowest_day)).strftime("%Y-%m-%d")
        
        return {
            "predicted_prices": predictions,
            "predicted_lowest": predicted_lowest,
            "predicted_lowest_date": predicted_lowest_date,
            "drop_probability": round(drop_prob, 2),
            "current_vs_average": current_vs_avg,
            "best_action": best_action,
            "savings_estimate": round(savings_estimate, 2),
            "savings_percentage": round(savings_pct, 1),
            "confidence": confidence,
            "upcoming_sales": upcoming_sales,
            "method": "arima",
            "model_order": f"ARIMA{self.order}",
            "explanation": explanation,
            "next_7_days": predictions[:7],
            # Backward compatibility
            "predicted_average": arima_result["predicted_avg"],
            "best_day_to_buy": lowest_day,
            "expected_savings": round(savings_estimate, 2),
        }
    
    def _sparse_data_prediction(self, current_price: float, avg_price: float,
                                 lowest_price: float, upcoming_sales: List[Dict], now: datetime) -> Dict:
        """Handle <10 data points — use sale calendar only."""
        current_vs_avg = _compare_to_average(current_price, avg_price)
        
        # Best action based on sale calendar + basic price position
        if upcoming_sales:
            next_sale = upcoming_sales[0]
            days_to_sale = next_sale.get("days_away", 30)
            if days_to_sale <= 30:
                best_action = f"WAIT_{days_to_sale}_DAYS"
                explanation = f"Limited price history, but {next_sale['name']} is {days_to_sale} days away ({next_sale['typical_discount']} off expected)"
            else:
                best_action = "BUY_NOW" if current_vs_avg != "above_average" else f"WAIT_{days_to_sale}_DAYS"
                explanation = f"Limited price data. Next major sale: {next_sale['name']} in {days_to_sale} days"
        else:
            best_action = "BUY_NOW" if current_vs_avg != "above_average" else "WAIT_30_DAYS"
            explanation = "Insufficient price history for prediction. Consider checking price tracking sites."
        
        return {
            "predicted_prices": [],
            "predicted_lowest": lowest_price,
            "predicted_lowest_date": None,
            "drop_probability": 0.3 if upcoming_sales else 0.1,
            "current_vs_average": current_vs_avg,
            "best_action": best_action,
            "savings_estimate": 0,
            "savings_percentage": 0,
            "confidence": 0.2,
            "upcoming_sales": upcoming_sales,
            "method": "sale_calendar_only",
            "explanation": explanation,
        }
    
    def _stable_price_prediction(self, current_price: float, avg_price: float,
                                  lowest_price: float, upcoming_sales: List[Dict], now: datetime) -> Dict:
        """Handle stable prices that haven't changed significantly."""
        current_vs_avg = _compare_to_average(current_price, avg_price)
        
        explanation = "Price has been stable for months — unlikely to drop significantly outside major sales"
        best_action = "BUY_NOW"
        
        if upcoming_sales:
            next_sale = upcoming_sales[0]
            days_to_sale = next_sale.get("days_away", 30)
            if days_to_sale <= 21:
                best_action = f"WAIT_{days_to_sale}_DAYS"
                explanation = f"Stable price, but {next_sale['name']} is {days_to_sale} days away — worth waiting for {next_sale['typical_discount']} potential"
        
        return {
            "predicted_prices": [current_price] * 30,
            "predicted_lowest": current_price,
            "predicted_lowest_date": now.strftime("%Y-%m-%d"),
            "drop_probability": 0.05,
            "current_vs_average": current_vs_avg,
            "best_action": best_action,
            "savings_estimate": 0,
            "savings_percentage": 0,
            "confidence": 0.7,
            "upcoming_sales": upcoming_sales,
            "method": "stable_price",
            "explanation": explanation,
        }
    
    def _statistical_prediction(self, price_values: List[float], current_price: float,
                                 avg_price: float, lowest_price: float,
                                 upcoming_sales: List[Dict], now: datetime) -> Dict:
        """Statistical prediction for 10-59 data points (not enough for ARIMA)."""
        # Use rolling average + trend
        recent = price_values[-min(30, len(price_values)):]
        recent_avg = float(np.mean(recent))
        recent_std = float(np.std(recent))
        
        # Simple trend: compare last 10 vs first 10
        if len(price_values) >= 20:
            first_half_avg = float(np.mean(price_values[:10]))
            last_half_avg = float(np.mean(price_values[-10:]))
            trend = (last_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        else:
            trend = 0
        
        # Simple projection
        predicted_prices = []
        for day in range(30):
            projected = recent_avg + (trend * recent_avg * day / 30)
            noise = float(np.random.normal(0, recent_std * 0.3))  # Reduced noise
            predicted_prices.append(round(max(0, projected + noise), 2))
        
        predicted_lowest = min(predicted_prices) if predicted_prices else current_price
        lowest_day = predicted_prices.index(predicted_lowest) + 1 if predicted_prices else 1
        
        drop_prob = sum(1 for p in predicted_prices if p < current_price * (1 - PRICE_DROP_THRESHOLD)) / max(len(predicted_prices), 1)
        savings_estimate = max(0, current_price - predicted_lowest)
        savings_pct = (savings_estimate / current_price * 100) if current_price > 0 else 0
        
        current_vs_avg = _compare_to_average(current_price, avg_price)
        
        best_action, explanation = _determine_best_action(
            current_price, predicted_lowest, lowest_day, drop_prob,
            savings_pct, current_vs_avg, upcoming_sales, lowest_price, now
        )
        
        predicted_lowest_date = (now + timedelta(days=lowest_day)).strftime("%Y-%m-%d")
        
        return {
            "predicted_prices": predicted_prices,
            "predicted_lowest": predicted_lowest,
            "predicted_lowest_date": predicted_lowest_date,
            "drop_probability": round(drop_prob, 2),
            "current_vs_average": current_vs_avg,
            "best_action": best_action,
            "savings_estimate": round(savings_estimate, 2),
            "savings_percentage": round(savings_pct, 1),
            "confidence": 0.4,
            "upcoming_sales": upcoming_sales,
            "method": "statistical",
            "explanation": explanation + " (limited data — statistical estimate)",
        }
    
    def _calculate_confidence(self, aic: float, prices: List[float]) -> float:
        """Calculate confidence based on AIC and price volatility."""
        # AIC component
        aic_component = max(0, min(1, 1 - (aic - 500) / 1000))
        
        # Volatility component
        if len(prices) > 30:
            recent = prices[-30:]
            volatility = float(np.std(recent) / np.mean(recent)) if np.mean(recent) > 0 else 1
            volatility_component = max(0.3, 1 - volatility * 2.5)
        else:
            volatility_component = 0.5
        
        # Data quantity bonus
        data_bonus = min(len(prices) / 180, 1.0) * 0.2  # Max 0.2 for 180+ points
        
        confidence = (aic_component * 0.5) + (volatility_component * 0.3) + data_bonus
        return round(min(1.0, max(0.1, confidence)), 2)


# ============================================================
# Helper Functions
# ============================================================

def _get_upcoming_sales(country: str, now: datetime = None) -> List[Dict]:
    """Get upcoming sales within 90 days from the sale calendar."""
    if now is None:
        now = datetime.now()
    
    current_month = now.month
    upcoming = []
    
    sales = SALE_CALENDAR.get(country, [])
    # Also check the other country's sales (global sales like Prime Day)
    other_country = "US" if country == "IN" else "IN"
    
    for sale in sales:
        # windows is list of (month, start_day, end_day) tuples
        for window in sale.get("windows", []):
            sale_month, start_day, end_day = window[0], window[1], window[2]
            # Calculate days until this sale window
            try:
                if sale_month > current_month or (sale_month == current_month and end_day >= now.day):
                    target_date = now.replace(month=sale_month, day=start_day)
                    if target_date < now:
                        target_date = now.replace(month=sale_month, day=end_day)
                else:
                    target_date = now.replace(year=now.year + 1, month=sale_month, day=start_day)
            except ValueError:
                try:
                    target_date = now.replace(year=now.year + 1, month=sale_month, day=28)
                except ValueError:
                    continue

            days_away = (target_date - now).days

            if 0 < days_away <= 90:
                upcoming.append({
                    "name": sale["name"],
                    "month": sale_month,
                    "days_away": days_away,
                    "typical_discount": sale["typical_discount"],
                    "country": country,
                })
    
    # Sort by days away
    upcoming.sort(key=lambda x: x["days_away"])
    return upcoming


def _compare_to_average(current_price: float, avg_price: float) -> str:
    """Compare current price to historical average."""
    if not current_price or not avg_price or avg_price <= 0:
        return "unknown"
    
    ratio = current_price / avg_price
    if ratio > 1.05:
        return "above_average"
    elif ratio < 0.95:
        return "below_average"
    else:
        return "at_average"


def _determine_best_action(current_price: float, predicted_lowest: float, lowest_day: int,
                            drop_prob: float, savings_pct: float, current_vs_avg: str,
                            upcoming_sales: List[Dict], historical_lowest: float,
                            now: datetime) -> tuple:
    """Determine the best buy/wait action with explanation."""
    
    # Check if current price is near historical low
    if historical_lowest and current_price:
        near_historical_low = current_price <= historical_lowest * 1.05
    else:
        near_historical_low = False
    
    # Decision logic
    if near_historical_low:
        return "PRICE_IS_LOW", f"Current price is near the historical low of ₹{historical_lowest:,.0f} — this is a good deal"
    
    if savings_pct >= 10 and drop_prob >= 0.3 and lowest_day <= 30:
        days = lowest_day
        # Check if a sale aligns
        for sale in upcoming_sales:
            if abs(sale["days_away"] - lowest_day) < 10:
                return f"WAIT_{sale['days_away']}_DAYS", f"Wait for {sale['name']} (~{sale['days_away']} days) — predicted {savings_pct:.0f}% savings ({sale['typical_discount']} typical)"
        return f"WAIT_{days}_DAYS", f"ARIMA predicts {savings_pct:.0f}% drop in ~{days} days (₹{current_price - predicted_lowest:,.0f} savings)"
    
    if upcoming_sales:
        next_sale = upcoming_sales[0]
        if next_sale["days_away"] <= 21:
            return f"WAIT_{next_sale['days_away']}_DAYS", f"{next_sale['name']} is just {next_sale['days_away']} days away ({next_sale['typical_discount']} off expected)"
    
    if current_vs_avg == "above_average":
        if upcoming_sales:
            next_sale = upcoming_sales[0]
            return f"WAIT_{next_sale['days_away']}_DAYS", f"Price is above average — consider waiting for {next_sale['name']} ({next_sale['days_away']} days)"
        return "WAIT_30_DAYS", "Price is above historical average — wait for a price drop"
    
    if current_vs_avg == "below_average" or drop_prob < 0.2:
        return "BUY_NOW", "Price is at or below average with low probability of significant further drop"
    
    return "BUY_NOW", "No significant price drop predicted — current price appears fair"


def create_best_predictor(price_data: Dict, prefer_arima: bool = True):
    """
    Factory function: Create best available predictor.
    Kept for backward compatibility.
    """
    data_points = price_data.get('data_points', 0)
    
    if ARIMA_AVAILABLE and data_points >= 60:
        return ARIMAPricePredictor(order=(5, 1, 0))
    
    # Return predictor anyway — predict_with_context handles sparse data
    return ARIMAPricePredictor(order=(5, 1, 0))
