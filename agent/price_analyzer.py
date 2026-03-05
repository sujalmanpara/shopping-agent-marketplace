# price_analyzer.py — Analyze if current price is a good deal

from typing import Dict, List

class PriceAnalyzer:
    """
    Analyze price data to determine deal quality
    and generate smart recommendations
    """
    
    def analyze(self, price_data: Dict) -> Dict:
        """
        Main analysis function
        
        Args:
            price_data: Dict from get_price_history()
        
        Returns:
            Comprehensive price analysis
        """
        if not price_data.get('success'):
            return {
                "error": "No price data available",
                "recommendation": "UNKNOWN"
            }
        
        current = price_data['current_price']
        avg = price_data['average_price']
        lowest = price_data['lowest_price']
        highest = price_data['highest_price']
        prices = [p['price'] for p in price_data['prices']]
        
        # Calculate key metrics
        vs_avg_pct = ((current - avg) / avg) * 100
        vs_lowest_pct = ((current - lowest) / lowest) * 100
        vs_highest_pct = ((current - highest) / highest) * 100
        
        # Determine deal quality
        deal_quality = self._calculate_deal_quality(vs_avg_pct, vs_lowest_pct)
        
        # Calculate price trend
        trend = self._calculate_trend(prices)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            deal_quality, trend, vs_avg_pct
        )
        
        # Explain reasoning
        reasoning = self._explain_reasoning(
            deal_quality, trend, vs_avg_pct, current, avg, lowest
        )
        
        return {
            "current_price": current,
            "metrics": {
                "vs_average": f"{vs_avg_pct:+.1f}%",
                "vs_lowest": f"{vs_lowest_pct:+.1f}%",
                "vs_highest": f"{vs_highest_pct:+.1f}%",
                "avg_price": avg,
                "lowest_price": lowest,
                "highest_price": highest
            },
            "deal_quality": deal_quality,  # excellent/good/fair/poor
            "trend": trend,  # increasing/decreasing/stable
            "recommendation": recommendation,  # BUY NOW/WAIT/OKAY
            "reasoning": reasoning,
            "price_position": self._describe_price_position(vs_avg_pct)
        }
    
    def _calculate_deal_quality(self, vs_avg: float, vs_lowest: float) -> str:
        """
        Categorize deal quality
        
        Excellent: Within 10% of all-time low
        Good: Below average
        Fair: Near average (±5%)
        Poor: Above average by >5%
        """
        if vs_lowest <= 10:
            return "excellent"
        elif vs_avg <= -5:
            return "good"
        elif -5 < vs_avg < 5:
            return "fair"
        else:
            return "poor"
    
    def _calculate_trend(self, prices: List[float]) -> str:
        """
        Calculate price trend over last 30 days
        """
        if len(prices) < 30:
            return "stable"  # Not enough data
        
        recent_30 = prices[-30:]
        earlier_30 = prices[-60:-30] if len(prices) >= 60 else prices[:-30]
        
        recent_avg = sum(recent_30) / len(recent_30)
        earlier_avg = sum(earlier_30) / len(earlier_30) if earlier_30 else recent_avg
        
        if earlier_avg == 0:
            return "stable"
        
        change_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
        
        if change_pct < -5:
            return "decreasing"
        elif change_pct > 5:
            return "increasing"
        else:
            return "stable"
    
    def _generate_recommendation(self, quality: str, trend: str, vs_avg: float) -> str:
        """
        Smart recommendation logic based on multiple factors
        """
        # Excellent deals are always BUY NOW
        if quality == "excellent":
            return "BUY NOW"
        
        # Good deals - check trend
        if quality == "good":
            if trend == "decreasing":
                return "WAIT"  # Might go lower
            else:
                return "BUY NOW"
        
        # Poor deals - always wait
        if quality == "poor":
            return "WAIT"
        
        # Fair deals - depends on trend
        if quality == "fair":
            if trend == "increasing":
                return "OKAY"  # Buy now before it goes up
            elif trend == "decreasing":
                return "WAIT"  # Wait for it to drop more
            else:
                return "OKAY"
        
        return "OKAY"
    
    def _explain_reasoning(self, quality: str, trend: str, vs_avg: float, 
                          current: float, avg: float, lowest: float) -> str:
        """
        Generate human-readable explanation
        """
        explanations = []
        
        # Deal quality explanation
        if quality == "excellent":
            diff_from_lowest = current - lowest
            explanations.append(
                f"Price is near all-time low (only ${diff_from_lowest:.2f} above lowest)"
            )
        elif quality == "good":
            diff_from_avg = avg - current
            explanations.append(
                f"Price is ${diff_from_avg:.2f} below 6-month average"
            )
        elif quality == "poor":
            diff_from_avg = current - avg
            explanations.append(
                f"Price is ${diff_from_avg:.2f} above average"
            )
        else:
            explanations.append("Price is near average")
        
        # Trend explanation
        if trend == "decreasing":
            explanations.append("Prices have been dropping recently")
        elif trend == "increasing":
            explanations.append("Prices have been rising recently")
        
        return ". ".join(explanations)
    
    def _describe_price_position(self, vs_avg: float) -> str:
        """
        Describe where price sits in historical range
        """
        if vs_avg <= -20:
            return "Much below average"
        elif vs_avg <= -10:
            return "Below average"
        elif vs_avg <= -5:
            return "Slightly below average"
        elif vs_avg < 5:
            return "Near average"
        elif vs_avg < 10:
            return "Slightly above average"
        elif vs_avg < 20:
            return "Above average"
        else:
            return "Much above average"
