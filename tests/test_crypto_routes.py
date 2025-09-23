"""Tests for the cryptocurrency API routes."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from src.routes import crypto


class _DummyResponse:
    """Lightweight HTTP response stub for mocking ``requests`` calls."""

    def __init__(self, status_code: int, payload: Dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload


@pytest.mark.usefixtures("db_session")
class TestGetCryptoPrice:
    """Unit tests for the ``/api/get_crypto_price`` endpoint."""

    def test_returns_formatted_price_for_valid_symbol(self, client, monkeypatch):
        """Endpoint should return a 200 with the formatted USD price."""
        fake_payload = {"bitcoin": {"usd": 12345.6789}}
        monkeypatch.setattr(
            crypto.requests,
            "get",
            lambda url, timeout=10: _DummyResponse(200, fake_payload),
        )

        response = client.get("/api/get_crypto_price", query_string={"symbol": "btc"})

        assert response.status_code == 200
        body = response.get_json()
        assert body == {"price": "$12,345.68", "symbol": "BTC"}

    def test_missing_symbol_returns_validation_error(self, client):
        """A request without a symbol should respond with HTTP 400."""
        response = client.get("/api/get_crypto_price")

        assert response.status_code == 400
        assert response.get_json()["error"] == "Symbol parameter is required"


@pytest.mark.usefixtures("db_session")
class TestCaptureHeatmap:
    """Unit tests for the ``/api/capture_heatmap`` endpoint."""

    def test_returns_success_payload_when_browsercat_succeeds(self, client, monkeypatch):
        """BrowserCat success should return the screenshot path payload."""
        monkeypatch.setattr(
            crypto.browsercat_client,
            "capture_coinglass_heatmap",
            lambda symbol, time_period: {"screenshot_path": "/tmp/success.png"},
        )

        response = client.post(
            "/api/capture_heatmap",
            json={"symbol": "eth", "time_period": "24 hour"},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["image_path"] == "/tmp/success.png"
        assert body["symbol"] == "ETH"
        assert body["time_period"] == "24 hour"

    def test_returns_simulated_fallback_when_browsercat_reports_error(
        self, client, monkeypatch
    ):
        """A BrowserCat error should trigger a fallback when allowed."""
        monkeypatch.setattr(
            crypto.browsercat_client,
            "capture_coinglass_heatmap",
            lambda symbol, time_period: {"error": "service unavailable"},
        )

        response = client.post(
            "/api/capture_heatmap",
            json={
                "symbol": "BTC",
                "time_period": "24 hour",
                "allow_simulated": True,
            },
        )

        assert response.status_code == 502
        body = response.get_json()
        assert body["error"] == "Failed to capture heatmap via BrowserCat."
        assert body["browsercat_error"] == "service unavailable"
        assert body["fallback_provided"] is True
        assert body["fallback"]["simulated"] is True
        assert body["fallback"]["symbol"] == "BTC"

    def test_handles_browsercat_exception_without_fallback(self, client, monkeypatch):
        """An unexpected BrowserCat exception should be surfaced cleanly."""

        def _raise_error(symbol: str, time_period: str) -> Dict[str, Any]:
            raise RuntimeError("boom")

        monkeypatch.setattr(
            crypto.browsercat_client,
            "capture_coinglass_heatmap",
            _raise_error,
        )

        response = client.get(
            "/api/capture_heatmap",
            query_string={"symbol": "BTC", "time_period": "24 hour"},
        )

        assert response.status_code == 503
        body = response.get_json()
        assert body["error"] == "BrowserCat client error while capturing heatmap."
        assert body["browsercat_error"] == "boom"
        assert body["fallback_provided"] is False
        assert "fallback" not in body
