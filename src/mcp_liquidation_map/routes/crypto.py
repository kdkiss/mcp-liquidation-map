import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests
from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from mcp_liquidation_map.services.browsercat_client import browsercat_client

_TRUTHY_STRINGS = {'1', 'true', 'yes', 'on'}
_FALSY_STRINGS = {'0', 'false', 'no', 'off'}

_COINGECKO_SYMBOL_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'BNB': 'binancecoin',
    'ADA': 'cardano',
    'SOL': 'solana',
    'XRP': 'ripple',
    'DOT': 'polkadot',
    'DOGE': 'dogecoin',
    'AVAX': 'avalanche-2',
    'MATIC': 'matic-network',
}

_VALID_TIMEFRAMES = ["12 hour", "24 hour", "1 month", "3 month"]

crypto_bp = Blueprint('crypto', __name__)

logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    """Container for service responses shared by HTTP and MCP surfaces."""

    payload: dict
    status_code: int = 200


def _resolve_coin_id(symbol: str) -> str:
    """Map a symbol to CoinGecko's identifier when available."""

    return _COINGECKO_SYMBOL_MAP.get(symbol, symbol.lower())


def build_crypto_price_result(
    symbol: Optional[str],
    log: Optional[logging.Logger] = None,
) -> ServiceResult:
    """Return the API payload for the crypto price endpoint."""

    log = log or logger

    if not symbol:
        return ServiceResult({'error': 'Symbol parameter is required', 'status_code': 400}, 400)

    symbol = symbol.upper()
    coin_id = _resolve_coin_id(symbol)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        log.warning('Failed to fetch price for %s (status=%s)', symbol, response.status_code)
        return ServiceResult({
            'error': f'Failed to fetch price for {symbol}',
            'status_code': 500,
        }, 500)

    data = response.json()
    price = data.get(coin_id, {}).get('usd')
    if price is None:
        return ServiceResult({'error': f'Price not found for {symbol}', 'status_code': 404}, 404)

    formatted_price = f"${price:,.2f}"
    return ServiceResult({'price': formatted_price, 'symbol': symbol})


def _resolve_allow_simulated(allow_simulated_override: Optional[bool]) -> bool:
    """Resolve whether simulated payloads are permitted."""

    if allow_simulated_override is not None:
        return allow_simulated_override

    env_allow_simulated = _parse_bool(os.getenv('ENABLE_SIMULATED_HEATMAP'))
    if env_allow_simulated is not None:
        return env_allow_simulated

    return True


def build_heatmap_result(
    symbol: str,
    time_period: str,
    allow_simulated_override: Optional[bool] = None,
    log: Optional[logging.Logger] = None,
) -> ServiceResult:
    """Return the payload for the liquidation heatmap capture endpoint."""

    log = log or logger

    symbol = symbol.upper()
    if time_period not in _VALID_TIMEFRAMES:
        return ServiceResult({
            'error': f'Invalid timeframe. Use: {", ".join(_VALID_TIMEFRAMES)}',
            'status_code': 400,
        }, 400)

    allow_simulated = _resolve_allow_simulated(allow_simulated_override)

    try:
        heatmap_result = browsercat_client.capture_coinglass_heatmap(symbol, time_period)
    except Exception as browsercat_error:
        log.error(
            "BrowserCat client error for symbol=%s, time_period=%s: %s",
            symbol,
            time_period,
            browsercat_error,
            exc_info=True,
        )
        response_payload = {
            'error': 'BrowserCat client error while capturing heatmap.',
            'browsercat_error': str(browsercat_error),
            'browsercat_status_code': getattr(browsercat_error, 'status_code', None),
            'symbol': symbol,
            'time_period': time_period,
            'fallback_provided': False,
        }

        if allow_simulated:
            response_payload['fallback'] = _build_simulated_payload(symbol, time_period)
            response_payload['fallback_provided'] = True

        response_payload.setdefault('status_code', 503)
        return ServiceResult(response_payload, 503)

    if 'error' in heatmap_result:
        status_code = heatmap_result.get('status_code')
        log.error('BrowserCat heatmap capture failed: %s', heatmap_result['error'])
        logger.error(
            'BrowserCat heatmap capture failed (status=%s): %s',
            status_code,
            heatmap_result['error'],
        )

        response_payload = {
            'error': 'Failed to capture heatmap via BrowserCat.',
            'browsercat_error': heatmap_result['error'],
            'browsercat_status_code': status_code,
            'symbol': symbol,
            'time_period': time_period,
            'fallback_provided': False,
        }

        if 'response' in heatmap_result:
            response_payload['browsercat_response'] = heatmap_result['response']

        if 'response_text' in heatmap_result:
            response_payload['browsercat_response_text'] = heatmap_result['response_text']

        if allow_simulated:
            response_payload['fallback'] = _build_simulated_payload(symbol, time_period)
            response_payload['fallback_provided'] = True

        response_payload.setdefault('status_code', 502)
        return ServiceResult(response_payload, 502)

    image_path = (
        heatmap_result.get('screenshot_path')
        or heatmap_result.get('path')
        or '/tmp/heatmap.png'
    )

    payload = {
        'image_path': image_path,
        'symbol': symbol,
        'time_period': time_period,
        'browsercat_result': heatmap_result,
    }

    return ServiceResult(payload)


def _get_logger():
    """Return the active application logger when available."""
    try:
        return current_app.logger
    except RuntimeError:
        return logger

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
    symbol = None
    try:
        if request.method == 'GET':
            symbol = request.args.get('symbol')
        else:  # POST
            data = request.get_json()
            symbol = data.get('symbol') if data else None

        result = build_crypto_price_result(symbol, log=_get_logger())
        return jsonify(result.payload), result.status_code

    except BadRequest as json_error:
        symbol_for_log = symbol or 'unknown'
        _get_logger().warning(
            "Invalid JSON payload while fetching price for symbol=%s: %s",
            symbol_for_log,
            json_error,
        )
        return jsonify({'error': 'Invalid JSON payload.'}), 400
    except Exception as e:
        symbol_for_log = symbol or 'unknown'
        _get_logger().error(
            "Error fetching price for symbol=%s: %s",
            symbol_for_log,
            e,
            exc_info=True,
        )
        return jsonify({'error': 'Internal server error.'}), 500

def _parse_bool(value):
    """Parse common truthy/falsey values to booleans."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lower_value = value.strip().lower()
        if lower_value in _TRUTHY_STRINGS:
            return True
        if lower_value in _FALSY_STRINGS:
            return False
    return None


def _build_simulated_payload(symbol: str, time_period: str):
    """Create a simulated heatmap payload used for non-production fallbacks."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_filename = f"{symbol.lower()}_liquidation_heatmap_{timestamp}_{time_period.replace(' ', '_')}.png"
    simulated_path = f"/tmp/{image_filename}"

    return {
        'image_path': simulated_path,
        'symbol': symbol,
        'time_period': time_period,
        'note': 'Simulated heatmap placeholder generated without BrowserCat.',
        'simulated': True
    }


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
    symbol = None
    time_period = None
    try:
        if request.method == 'GET':
            symbol = request.args.get('symbol', 'BTC')
            time_period = request.args.get('time_period', '24 hour')
            allow_simulated_param = request.args.get('allow_simulated')
        else:  # POST
            data = request.get_json()
            symbol = data.get('symbol', 'BTC') if data else 'BTC'
            time_period = data.get('time_period', '24 hour') if data else '24 hour'
            allow_simulated_param = data.get('allow_simulated') if data else None

        allow_simulated_override = _parse_bool(allow_simulated_param)
        result = build_heatmap_result(
            symbol,
            time_period,
            allow_simulated_override,
            log=_get_logger(),
        )
        return jsonify(result.payload), result.status_code

    except BadRequest as json_error:
        symbol_for_log = symbol or 'unknown'
        time_period_for_log = time_period or 'unknown'
        _get_logger().warning(
            "Invalid JSON payload for capture_heatmap (symbol=%s, time_period=%s): %s",
            symbol_for_log,
            time_period_for_log,
            json_error,
        )
        return jsonify({'error': 'Invalid JSON payload.'}), 400
    except Exception as e:
        symbol_for_log = symbol or 'unknown'
        time_period_for_log = time_period or 'unknown'
        _get_logger().error(
            "Error capturing heatmap for symbol=%s, time_period=%s: %s",
            symbol_for_log,
            time_period_for_log,
            e,
            exc_info=True,
        )
        return jsonify({'error': 'Internal server error.'}), 500

@crypto_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

