# competitor_prices.py — Find cheaper alternatives on other stores

import asyncio
import re
from typing import Dict, List
from scrapling import StealthyFetcher, Fetcher
from bs4 import BeautifulSoup

async def search_walmart(product_name: str, max_results: int = 3) -> List[Dict]:
    """
    Search Walmart for product alternatives
    """
    query = product_name.split(',')[0][:50]  # First part of name
    url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
    
    try:
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            timeout=10
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        products = []
        for item in soup.select('[data-item-id]')[:max_results]:
            name_elem = item.select_one('[data-automation-id="product-title"]')
            price_elem = item.select_one('[data-automation-id="product-price"]')
            
            if name_elem and price_elem:
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                
                # Extract price
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    
                    products.append({
                        "name": name[:80],
                        "price": price,
                        "store": "Walmart",
                        "url": f"https://www.walmart.com{item.get('href', '')}" if item.get('href') else None
                    })
        
        return products
    
    except Exception as e:
        print(f"Walmart search failed: {e}")
        return []


async def search_target(product_name: str, max_results: int = 3) -> List[Dict]:
    """
    Search Target for product alternatives
    """
    query = product_name.split(',')[0][:50]
    url = f"https://www.target.com/s?searchTerm={query.replace(' ', '+')}"
    
    try:
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            timeout=10
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        products = []
        for item in soup.select('[data-test="product-grid"] [data-test*="product"]')[:max_results]:
            name_elem = item.select_one('[data-test="product-title"]')
            price_elem = item.select_one('[data-test="current-price"]')
            
            if name_elem and price_elem:
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    
                    products.append({
                        "name": name[:80],
                        "price": price,
                        "store": "Target",
                        "url": item.select_one('a')['href'] if item.select_one('a') else None
                    })
        
        return products
    
    except Exception as e:
        print(f"Target search failed: {e}")
        return []


async def search_bestbuy(product_name: str, max_results: int = 3) -> List[Dict]:
    """
    Search BestBuy for product alternatives
    """
    query = product_name.split(',')[0][:50]
    url = f"https://www.bestbuy.com/site/searchpage.jsp?st={query.replace(' ', '+')}"
    
    try:
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            timeout=10
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        products = []
        for item in soup.select('.sku-item')[:max_results]:
            name_elem = item.select_one('.sku-title a')
            price_elem = item.select_one('[data-testid="customer-price"]')
            
            if name_elem and price_elem:
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))
                    
                    products.append({
                        "name": name[:80],
                        "price": price,
                        "store": "BestBuy",
                        "url": name_elem['href'] if name_elem.get('href') else None
                    })
        
        return products
    
    except Exception as e:
        print(f"BestBuy search failed: {e}")
        return []


async def find_competitor_prices(product_name: str, current_price: float) -> Dict:
    """
    Search all competitor stores and find cheaper alternatives
    
    Args:
        product_name: Product name from Amazon
        current_price: Current Amazon price
    
    Returns:
        Dict with all competitors and best deal
    """
    # Search all stores in parallel
    results = await asyncio.gather(
        search_walmart(product_name),
        search_target(product_name),
        search_bestbuy(product_name),
        return_exceptions=True
    )
    
    # Filter out exceptions and empty results
    all_products = []
    for result in results:
        if isinstance(result, list):
            all_products.extend(result)
    
    if not all_products:
        return {
            "found": 0,
            "stores_searched": ["Walmart", "Target", "BestBuy"],
            "cheapest": None,
            "savings": 0,
            "message": "No alternatives found (scraping may have been blocked)"
        }
    
    # Find cheapest
    cheapest = min(all_products, key=lambda x: x['price'])
    
    # Calculate savings vs Amazon
    savings = current_price - cheapest['price']
    savings_pct = (savings / current_price * 100) if current_price > 0 else 0
    
    # Find best value (price per rating if available, otherwise just cheapest)
    best_value = cheapest  # Simplified for now
    
    return {
        "found": len(all_products),
        "stores_searched": ["Walmart", "Target", "BestBuy"],
        "all_alternatives": all_products,
        "cheapest": cheapest,
        "best_value": best_value,
        "savings": round(savings, 2),
        "savings_percentage": round(savings_pct, 1),
        "recommendation": "Buy from Amazon" if savings < 5 else f"Save ${savings:.2f} at {cheapest['store']}"
    }


async def compare_with_competitors(product_name: str, amazon_price: float) -> Dict:
    """
    Convenience function: Compare Amazon price with all competitors
    
    Returns formatted comparison
    """
    comparison = await find_competitor_prices(product_name, amazon_price)
    
    if comparison['found'] == 0:
        return {
            "has_data": False,
            "message": "Could not find alternatives (stores may be blocking scraping)"
        }
    
    return {
        "has_data": True,
        "amazon_price": amazon_price,
        "competitors_checked": comparison['stores_searched'],
        "alternatives_found": comparison['found'],
        "cheapest_price": comparison['cheapest']['price'],
        "cheapest_store": comparison['cheapest']['store'],
        "savings_vs_amazon": comparison['savings'],
        "savings_percentage": comparison['savings_percentage'],
        "top_3_alternatives": comparison['all_alternatives'][:3],
        "recommendation": comparison['recommendation']
    }
