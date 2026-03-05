#!/usr/bin/env python3
"""
Test Feature 7: Price Drop Prophet (ML-powered)
"""

import asyncio
import sys
sys.path.insert(0, 'agent')

from agent.price_scraper import get_price_history
from agent.price_analyzer import PriceAnalyzer
from agent.price_predictor import PricePredictor, generate_final_recommendation

async def test_price_tracking():
    """Test the complete ML price tracking system"""
    
    print("="*60)
    print("🧪 TESTING FEATURE 7: ML PRICE TRACKING")
    print("="*60)
    
    # Test ASIN (Sony headphones)
    test_asin = "B08N5WRWNW"
    
    print(f"\n📦 Testing with ASIN: {test_asin}")
    print("⏳ Scraping price history...")
    
    # Step 1: Get price history
    price_data = await get_price_history(test_asin, months=6)
    
    if not price_data.get('success'):
        print(f"\n❌ Price scraping failed:")
        print(f"   CCC Error: {price_data.get('ccc_error')}")
        print(f"   Keepa Error: {price_data.get('keepa_error')}")
        print("\n⚠️  This is expected in datacenter environment")
        print("   Scrapers will work better with:")
        print("   - Residential IP")
        print("   - Real user traffic patterns")
        return
    
    print(f"\n✅ Price history retrieved from {price_data['source']}")
    print(f"   Data points: {price_data['data_points']}")
    print(f"   Current price: ${price_data['current_price']:.2f}")
    
    # Step 2: Analyze current price
    print("\n📊 Analyzing current price...")
    analyzer = PriceAnalyzer()
    analysis = analyzer.analyze(price_data)
    
    print(f"   Average: ${analysis['metrics']['avg_price']:.2f}")
    print(f"   Lowest: ${analysis['metrics']['lowest_price']:.2f}")
    print(f"   Highest: ${analysis['metrics']['highest_price']:.2f}")
    print(f"   Deal Quality: {analysis['deal_quality'].upper()}")
    print(f"   Trend: {analysis['trend']}")
    print(f"   Base Recommendation: {analysis['recommendation']}")
    
    # Step 3: ML Predictions
    print("\n🤖 Running ML price predictions...")
    predictor = PricePredictor(use_polynomial=True)
    predictions = predictor.predict_next_30_days(price_data)
    
    if predictions.get('error'):
        print(f"   ⚠️  {predictions['error']}")
    else:
        print(f"   Predicted lowest: ${predictions['predicted_lowest']:.2f} (day {predictions['best_day_to_buy']})")
        print(f"   Drop probability: {predictions['drop_probability']*100:.0f}%")
        print(f"   Expected savings: ${predictions['expected_savings']:.2f} ({predictions['savings_percentage']}%)")
        print(f"   Model confidence: {predictions['confidence']*100:.0f}%")
        print(f"   R² score: {predictions['r2_score']}")
    
    # Step 4: Check upcoming sales
    print("\n📅 Checking upcoming sales...")
    upcoming_sales = predictor.check_upcoming_sales()
    
    if upcoming_sales:
        for sale in upcoming_sales:
            print(f"   {sale['event']}: {sale['days_away']} days ({sale['expected_discount']})")
    else:
        print("   No major sales in next 60 days")
    
    # Step 5: Final recommendation
    print("\n🎯 FINAL RECOMMENDATION:")
    final_rec = generate_final_recommendation(analysis, predictions, upcoming_sales)
    
    print(f"   Action: {final_rec['action']}")
    print(f"   Reason: {final_rec['reason']}")
    if 'confidence' in final_rec:
        print(f"   Confidence: {final_rec.get('confidence', 'N/A')}")
    
    print("\n" + "="*60)
    print("✅ Feature 7 test complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_price_tracking())
