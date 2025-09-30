import unittest
from unittest.mock import MagicMock, patch

from flask import Flask
import requests

from mcp_liquidation_map.routes.crypto import crypto_bp


class CryptoPriceRouteTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(crypto_bp, url_prefix='/api')
        self.client = app.test_client()

    def test_get_crypto_price_missing_symbol_returns_400(self):
        response = self.client.get('/api/get_crypto_price')

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['error'], 'Symbol parameter is required')
        self.assertEqual(data['status_code'], 400)

    @patch('mcp_liquidation_map.routes.crypto.requests.get')
    def test_get_crypto_price_success_formats_response(self, mock_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'bitcoin': {'usd': 12345.6789}}
        mock_get.return_value = mock_response

        response = self.client.get('/api/get_crypto_price?symbol=btc')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['symbol'], 'BTC')
        self.assertEqual(data['price'], '$12,345.68')
        mock_get.assert_called_once_with(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
            timeout=10,
        )

    @patch('mcp_liquidation_map.routes.crypto.requests.get')
    def test_get_crypto_price_request_exception_returns_503(self, mock_get: MagicMock):
        mock_get.side_effect = requests.RequestException('boom')

        response = self.client.get('/api/get_crypto_price?symbol=btc')

        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertEqual(data['error'], 'Upstream service error while fetching price.')
        self.assertEqual(data['status_code'], 503)
        self.assertEqual(data['symbol'], 'BTC')
        self.assertEqual(data['request_error'], 'boom')


if __name__ == '__main__':
    unittest.main()
