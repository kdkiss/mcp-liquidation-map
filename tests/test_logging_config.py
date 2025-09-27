import importlib
import logging
import os
import unittest
from unittest.mock import patch

from flask import Flask

from mcp_liquidation_map.routes.crypto import crypto_bp


class CryptoBlueprintLoggingTests(unittest.TestCase):
    def test_capture_heatmap_logs_to_current_app_logger(self):
        app = Flask(__name__)
        app.register_blueprint(crypto_bp, url_prefix='/api')
        records = []

        class CollectorHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        collector = CollectorHandler()
        original_handlers = list(app.logger.handlers)
        original_level = app.logger.level
        os.environ.pop('ENABLE_SIMULATED_HEATMAP', None)
        try:
            app.logger.handlers = [collector]
            app.logger.setLevel(logging.INFO)
            with app.test_client() as client, patch(
                'mcp_liquidation_map.routes.crypto.browsercat_client.capture_coinglass_heatmap',
                side_effect=RuntimeError('boom'),
            ):
                response = client.get('/api/capture_heatmap?symbol=BTC&time_period=24%20hour')
                self.assertEqual(response.status_code, 503)
        finally:
            app.logger.handlers = original_handlers
            app.logger.setLevel(original_level)

        self.assertTrue(
            any('BrowserCat client error' in record.getMessage() for record in records),
            'Expected capture_heatmap to emit an error log through the Flask app logger.',
        )


class ConfigureLoggingTests(unittest.TestCase):
    def setUp(self):
        self.root_logger = logging.getLogger()
        self.original_handlers = list(self.root_logger.handlers)
        self.original_level = self.root_logger.level
        self.original_app_log_level = os.environ.get('APP_LOG_LEVEL')
        self.main_module = importlib.import_module('mcp_liquidation_map.main')

    def tearDown(self):
        for handler in list(self.root_logger.handlers):
            self.root_logger.removeHandler(handler)
        for handler in self.original_handlers:
            self.root_logger.addHandler(handler)
        self.root_logger.setLevel(self.original_level)

        if self.original_app_log_level is None:
            os.environ.pop('APP_LOG_LEVEL', None)
        else:
            os.environ['APP_LOG_LEVEL'] = self.original_app_log_level

        importlib.reload(self.main_module)

    def test_configure_logging_respects_existing_handlers(self):
        sentinel_stream = logging.StreamHandler()
        for handler in list(self.root_logger.handlers):
            self.root_logger.removeHandler(handler)
        self.root_logger.addHandler(sentinel_stream)
        self.root_logger.setLevel(logging.WARNING)

        importlib.reload(self.main_module)

        self.assertEqual(len(self.root_logger.handlers), 1)
        self.assertIs(self.root_logger.handlers[0], sentinel_stream)
        self.assertEqual(self.root_logger.level, logging.WARNING)

    def test_configure_logging_sets_defaults_when_missing(self):
        for handler in list(self.root_logger.handlers):
            self.root_logger.removeHandler(handler)
        self.root_logger.setLevel(logging.NOTSET)
        os.environ['APP_LOG_LEVEL'] = 'DEBUG'

        importlib.reload(self.main_module)

        self.assertGreaterEqual(len(self.root_logger.handlers), 1)
        self.assertEqual(self.root_logger.level, logging.DEBUG)


if __name__ == '__main__':
    unittest.main()
