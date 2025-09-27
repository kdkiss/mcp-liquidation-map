import os
import unittest
from unittest.mock import patch

from flask import Flask

from src.routes.crypto import crypto_bp


class CaptureHeatmapRouteTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop('ENABLE_SIMULATED_HEATMAP', None)
        app = Flask(__name__)
        app.register_blueprint(crypto_bp, url_prefix='/api')
        self.client = app.test_client()

    def tearDown(self):
        os.environ.pop('ENABLE_SIMULATED_HEATMAP', None)

    @patch('src.routes.crypto.browsercat_client.capture_coinglass_heatmap')
    def test_capture_heatmap_success(self, mock_capture):
        mock_capture.return_value = {'screenshot_path': '/tmp/test.png'}

        response = self.client.get('/api/capture_heatmap?symbol=BTC&time_period=24%20hour')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['image_path'], '/tmp/test.png')
        self.assertEqual(data['symbol'], 'BTC')
        self.assertEqual(data['time_period'], '24 hour')
        self.assertNotIn('fallback', data)
        mock_capture.assert_called_once_with('BTC', '24 hour')

    @patch('src.routes.crypto.browsercat_client.capture_coinglass_heatmap')
    def test_capture_heatmap_uses_path_when_screenshot_missing(self, mock_capture):
        mock_capture.return_value = {'path': '/tmp/fallback.png'}

        response = self.client.get('/api/capture_heatmap?symbol=BTC&time_period=24%20hour')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['image_path'], '/tmp/fallback.png')
        self.assertEqual(data['symbol'], 'BTC')
        self.assertEqual(data['time_period'], '24 hour')
        mock_capture.assert_called_once_with('BTC', '24 hour')

    @patch('src.routes.crypto.browsercat_client.capture_coinglass_heatmap')
    def test_capture_heatmap_browsercat_failure_without_fallback(self, mock_capture):
        mock_capture.return_value = {'error': 'Request failed with status 401'}

        response = self.client.get('/api/capture_heatmap?symbol=ETH&time_period=12%20hour')

        self.assertEqual(response.status_code, 502)
        data = response.get_json()
        self.assertFalse(data['fallback_provided'])
        self.assertNotIn('fallback', data)
        self.assertEqual(data['browsercat_error'], 'Request failed with status 401')
        mock_capture.assert_called_once_with('ETH', '12 hour')

    @patch('src.routes.crypto.browsercat_client.capture_coinglass_heatmap')
    def test_capture_heatmap_browsercat_exception_with_fallback(self, mock_capture):
        mock_capture.side_effect = RuntimeError('network outage')

        response = self.client.get('/api/capture_heatmap?symbol=SOL&time_period=24%20hour&allow_simulated=true')

        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertTrue(data['fallback_provided'])
        self.assertIn('fallback', data)
        self.assertEqual(data['browsercat_error'], 'network outage')

        fallback = data['fallback']
        self.assertEqual(fallback['symbol'], 'SOL')
        self.assertEqual(fallback['time_period'], '24 hour')
        self.assertTrue(fallback['simulated'])
        self.assertTrue(fallback['image_path'].startswith('/tmp/sol_liquidation_heatmap_'))


if __name__ == '__main__':
    unittest.main()
