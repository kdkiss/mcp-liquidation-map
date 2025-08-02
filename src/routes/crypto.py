from flask import Blueprint, jsonify, request
import requests
import os
import time
from datetime import datetime
import logging
from src.services.browsercat_client import browsercat_client

crypto_bp = Blueprint('crypto', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@crypto_bp.route('/get_crypto_price', methods=['GET', 'POST'])
def get_crypto_price():
    """
    Get current cryptocurrency price
    
    Parameters:
    - symbol (string): Cryptocurrency symbol (e.g., "BTC", "ETH")
    
    Returns:
    - price (string): Formatted price (e.g., "$30,000.00")
    - error (string, optional): Error message if operation fails
    """
    try:
        if request.method == 'GET':
            symbol = request.args.get('symbol')
        else:  # POST
            data = request.get_json()
            symbol = data.get('symbol') if data else None
        
        if not symbol:
            return jsonify({'error': 'Symbol parameter is required'}), 400
        
        symbol = symbol.upper()
        
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'ADA': 'cardano',
            'SOL': 'solana',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network'
        }
        
        coin_id = symbol_map.get(symbol, symbol.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price = data.get(coin_id, {}).get('usd')
            if price:
                formatted_price = f"${price:,.2f}"
                return jsonify({'price': formatted_price, 'symbol': symbol})
            else:
                return jsonify({'error': f'Price not found for {symbol}'}), 404
        else:
            return jsonify({'error': f'Failed to fetch price for {symbol}'}), 500
            
    except Exception as e:
        logger.error(f"Error fetching {symbol} price: {e}")
        return jsonify({'error': str(e)}), 500

@crypto_bp.route('/capture_heatmap', methods=['GET', 'POST'])
def capture_heatmap():
    """
    Capture Coinglass liquidation heatmap
    
    Parameters:
    - symbol (string): Cryptocurrency symbol (e.g., "BTC", "ETH")
    - time_period (string, optional): Time period ("12 hour", "24 hour", "1 month", "3 month")
    
    Returns:
    - image_path (string): Path to captured image file
    - error (string, optional): Error message if operation fails
    """
    try:
        if request.method == 'GET':
            symbol = request.args.get('symbol', 'BTC')
            time_period = request.args.get('time_period', '24 hour')
        else:  # POST
            data = request.get_json()
            symbol = data.get('symbol', 'BTC') if data else 'BTC'
            time_period = data.get('time_period', '24 hour') if data else '24 hour'
        
        symbol = symbol.upper()
        
        # Validate time period
        valid_timeframes = ["12 hour", "24 hour", "1 month", "3 month"]
        if time_period not in valid_timeframes:
            return jsonify({'error': f'Invalid timeframe. Use: {", ".join(valid_timeframes)}'}), 400
        
        # Use BrowserCat MCP client to capture heatmap
        try:
            heatmap_result = browsercat_client.capture_coinglass_heatmap(symbol, time_period)
            
            if "error" in heatmap_result:
                logger.error(f"BrowserCat heatmap capture failed: {heatmap_result['error']}")
                # Fallback to simulated response
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                image_filename = f"{symbol.lower()}_liquidation_heatmap_{timestamp}_{time_period.replace(' ', '_')}.png"
                simulated_path = f"/tmp/{image_filename}"
                
                return jsonify({
                    'image_path': simulated_path,
                    'symbol': symbol,
                    'time_period': time_period,
                    'note': f'BrowserCat capture failed: {heatmap_result["error"]}. Returning simulated response.',
                    'browsercat_error': heatmap_result['error']
                })
            else:
                # Success - return actual screenshot path
                return jsonify({
                    'image_path': heatmap_result.get('screenshot_path', '/tmp/heatmap.png'),
                    'symbol': symbol,
                    'time_period': time_period,
                    'browsercat_result': heatmap_result
                })
                
        except Exception as browsercat_error:
            logger.error(f"BrowserCat client error: {browsercat_error}")
            # Fallback to simulated response
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{symbol.lower()}_liquidation_heatmap_{timestamp}_{time_period.replace(' ', '_')}.png"
            simulated_path = f"/tmp/{image_filename}"
            
            return jsonify({
                'image_path': simulated_path,
                'symbol': symbol,
                'time_period': time_period,
                'note': f'BrowserCat client error: {str(browsercat_error)}. Returning simulated response.',
                'browsercat_error': str(browsercat_error)
            })
        
    except Exception as e:
        logger.error(f"Error capturing heatmap: {e}")
        return jsonify({'error': str(e)}), 500

@crypto_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

