# price_scraper.py — Real price history scraping from CamelCamelCamel and Keepa

import asyncio
import re
import json
from typing import Dict, Optional, List
from datetime import datetime
from scrapling import StealthyFetcher, Fetcher
from bs4 import BeautifulSoup

async def scrape_camelcamelcamel(asin: str, months: int = 6) -> Dict:
    """
    Scrape CamelCamelCamel for real price history
    URL: https://camelcamelcamel.com/product/{asin}
    """
    url = f"https://camelcamelcamel.com/product/{asin}"
    
    try:
        # Use StealthyFetcher for reliable scraping
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=15
        )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract current price
        current_price = None
        price_elem = soup.select_one('.product_pane .price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if price_match:
                current_price = float(price_match.group(1).replace(',', ''))
        
        # Extract price history from JavaScript
        price_data = extract_price_data_from_scripts(soup)
        
        if not price_data:
            # Try alternative: look for data-* attributes
            chart_elem = soup.find('div', {'id': 'chart'})
            if chart_elem and chart_elem.get('data-chart'):
                price_data = parse_chart_data(chart_elem['data-chart'])
        
        if not price_data:
            raise Exception("Could not find price data in CamelCamelCamel")
        
        # Filter to last N months
        cutoff_days = months * 30
        recent_prices = price_data[-cutoff_days:] if len(price_data) > cutoff_days else price_data
        
        # Calculate statistics
        price_values = [p['price'] for p in recent_prices]
        
        return {
            "source": "camelcamelcamel",
            "asin": asin,
            "current_price": current_price or price_values[-1],
            "prices": recent_prices,
            "average_price": sum(price_values) / len(price_values),
            "lowest_price": min(price_values),
            "highest_price": max(price_values),
            "data_points": len(recent_prices),
            "success": True
        }
    
    except Exception as e:
        return {
            "source": "camelcamelcamel",
            "success": False,
            "error": str(e)
        }


def extract_price_data_from_scripts(soup: BeautifulSoup) -> Optional[List[Dict]]:
    """
    Extract price history from embedded JavaScript
    CCC typically embeds data like: var priceHistory = [[timestamp, price], ...]
    """
    script_tags = soup.find_all('script')
    
    for script in script_tags:
        if not script.string:
            continue
        
        script_text = script.string
        
        # Look for patterns like: [[1640995200000, 299.99], [1641081600000, 289.99], ...]
        # Try multiple variable names
        for var_name in ['priceHistory', 'amazonData', 'chartData', 'data']:
            pattern = rf'{var_name}\s*=\s*(\[\[.*?\]\])'
            match = re.search(pattern, script_text, re.DOTALL)
            
            if match:
                try:
                    # Extract the array
                    array_str = match.group(1)
                    
                    # Parse as JSON
                    price_array = json.loads(array_str)
                    
                    # Convert to our format
                    prices = []
                    for item in price_array:
                        if len(item) >= 2 and item[1] is not None:
                            timestamp = item[0] / 1000  # Convert milliseconds to seconds
                            price = float(item[1])
                            
                            prices.append({
                                "date": datetime.fromtimestamp(timestamp).isoformat(),
                                "price": price
                            })
                    
                    if prices:
                        return prices
                
                except:
                    continue
    
    return None


def parse_chart_data(chart_data_str: str) -> Optional[List[Dict]]:
    """Parse chart data from data-chart attribute"""
    try:
        data = json.loads(chart_data_str)
        
        prices = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    timestamp = item[0] / 1000
                    price = float(item[1])
                    
                    prices.append({
                        "date": datetime.fromtimestamp(timestamp).isoformat(),
                        "price": price
                    })
        
        return prices if prices else None
    
    except:
        return None


async def scrape_keepa(asin: str, months: int = 6) -> Dict:
    """
    Scrape Keepa as fallback
    URL: https://keepa.com/#!product/1-{asin}
    
    Note: Keepa is harder to scrape (more bot detection)
    """
    url = f"https://keepa.com/#!product/1-{asin}"
    
    try:
        # Try StealthyFetcher first
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            timeout=20
        )
        
        # Keepa loads data via XHR - check if we got actual data
        if len(response.text) < 1000:
            raise Exception("Keepa returned minimal content (likely bot detected)")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Keepa embeds price data differently
        # Look for API responses in script tags or data attributes
        price_data = extract_keepa_price_data(soup)
        
        if not price_data:
            raise Exception("Could not extract Keepa price data")
        
        # Filter and format
        cutoff_days = months * 30
        recent_prices = price_data[-cutoff_days:] if len(price_data) > cutoff_days else price_data
        price_values = [p['price'] for p in recent_prices]
        
        return {
            "source": "keepa",
            "asin": asin,
            "current_price": price_values[-1],
            "prices": recent_prices,
            "average_price": sum(price_values) / len(price_values),
            "lowest_price": min(price_values),
            "highest_price": max(price_values),
            "data_points": len(recent_prices),
            "success": True
        }
    
    except Exception as e:
        return {
            "source": "keepa",
            "success": False,
            "error": str(e)
        }


def extract_keepa_price_data(soup: BeautifulSoup) -> Optional[List[Dict]]:
    """
    Extract price data from Keepa
    Keepa uses different format - often compressed data
    """
    # Try to find embedded data
    script_tags = soup.find_all('script')
    
    for script in script_tags:
        if not script.string:
            continue
        
        # Look for Keepa's data structure
        if 'csv' in script.string and 'AMAZON' in script.string:
            # Keepa uses CSV-like format
            # Try to parse it
            try:
                # This is a simplified parser - real Keepa data is more complex
                lines = script.string.split('\n')
                prices = []
                
                for line in lines:
                    if ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            try:
                                timestamp = int(parts[0])
                                price = float(parts[1])
                                
                                prices.append({
                                    "date": datetime.fromtimestamp(timestamp).isoformat(),
                                    "price": price
                                })
                            except:
                                continue
                
                if prices:
                    return prices
            
            except:
                continue
    
    return None


async def get_price_history(asin: str, months: int = 6) -> Dict:
    """
    Main function: Try multiple sources with fallback chain
    
    Priority:
    1. CamelCamelCamel (fast, reliable)
    2. Keepa (slower, backup)
    3. Fallback (calendar-based from existing system)
    """
    # Try CamelCamelCamel first
    ccc_data = await scrape_camelcamelcamel(asin, months)
    
    if ccc_data.get('success'):
        return ccc_data
    
    print(f"CCC failed for {asin}: {ccc_data.get('error')}")
    
    # Try Keepa as backup
    keepa_data = await scrape_keepa(asin, months)
    
    if keepa_data.get('success'):
        return keepa_data
    
    print(f"Keepa failed for {asin}: {keepa_data.get('error')}")
    
    # Both failed - return fallback indicator
    return {
        "source": "fallback",
        "success": False,
        "has_data": False,
        "error": "All price history sources failed",
        "ccc_error": ccc_data.get('error'),
        "keepa_error": keepa_data.get('error')
    }
