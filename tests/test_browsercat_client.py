import json
import os
from unittest.mock import Mock

from src.services.browsercat_client import BrowserCatMCPClient


def _restore_env(key: str, original_value):
    if original_value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = original_value


def test_browsercat_client_uses_environment_configuration():
    original_base = os.environ.get("BROWSERCAT_BASE_URL")
    original_timeout = os.environ.get("BROWSERCAT_TIMEOUT")

    os.environ["BROWSERCAT_BASE_URL"] = "https://example.test"
    os.environ["BROWSERCAT_TIMEOUT"] = "45"

    try:
        client = BrowserCatMCPClient(api_key="test-env")
        assert client.base_url == "https://example.test"
        assert client.timeout == 45.0
    finally:
        _restore_env("BROWSERCAT_BASE_URL", original_base)
        _restore_env("BROWSERCAT_TIMEOUT", original_timeout)


def test_make_request_retries_and_succeeds_after_transient_error():
    client = BrowserCatMCPClient(
        api_key="test",
        base_url="https://example.test",
        timeout=1,
        max_retries=2,
        backoff_factor=0,
    )

    failing_response = Mock()
    failing_response.status_code = 503
    failing_response.text = "Service unavailable"
    failing_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)

    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {"result": "ok"}

    client._session.post = Mock(side_effect=[failing_response, success_response])
    client._sleep_with_backoff = Mock()

    result = client._make_request("test_tool", {})

    assert result == {"result": "ok"}
    assert client._session.post.call_count == 2
    client._sleep_with_backoff.assert_called_once_with(0)


def test_make_request_returns_structured_error_with_status_code():
    client = BrowserCatMCPClient(
        api_key="test",
        base_url="https://example.test",
        timeout=1,
        max_retries=1,
        backoff_factor=0,
    )

    error_response = Mock()
    error_response.status_code = 500
    error_response.text = "Server error"
    error_response.json.return_value = {"message": "failure"}

    client._session.post = Mock(return_value=error_response)

    result = client._make_request("test_tool", {})

    assert result["status_code"] == 500
    assert result["response"] == {"message": "failure"}
    assert "error" in result


def test_capture_coinglass_heatmap_non_btc_symbol_and_timeframe_selection():
    client = BrowserCatMCPClient(api_key="test")
    events = []

    def record_event(name, payload):
        events.append((name, payload))

    def navigate_side_effect(url):
        record_event("navigate", url)
        return {}

    def evaluate_side_effect(script):
        record_event("evaluate", script)
        if "document.querySelector('input.MuiAutocomplete-input')" in script and "new Promise" in script:
            return {"result": True}
        if "buttons.find" in script and "role=\"tab\"" in script:
            return {"result": True}
        return {"result": None}

    def fill_side_effect(selector, value):
        record_event("fill", {"selector": selector, "value": value})
        return {}

    def screenshot_side_effect(**kwargs):
        record_event("screenshot", kwargs)
        return {"path": "dummy.png"}

    client.navigate = Mock(side_effect=navigate_side_effect)
    client.evaluate = Mock(side_effect=evaluate_side_effect)
    client.fill = Mock(side_effect=fill_side_effect)
    client.screenshot = Mock(side_effect=screenshot_side_effect)

    result = client.capture_coinglass_heatmap(symbol="ETH", time_period="6 hour")

    assert result["path"] == "dummy.png"

    # Ensure navigation to the correct page happened first
    assert events[0] == ("navigate", "https://www.coinglass.com/pro/futures/LiquidationHeatMap")

    # Verify the tab selection was attempted via text-based search
    assert any(
        event_name == "evaluate" and "button[role=\"tab\"]" in payload and "textContent" in payload
        for event_name, payload in events
    )

    # Verify the polling script executes before attempting to fill the input
    wait_indices = [
        idx
        for idx, (event_name, payload) in enumerate(events)
        if event_name == "evaluate"
        and "document.querySelector('input.MuiAutocomplete-input')" in payload
        and "new Promise" in payload
    ]
    assert wait_indices, "Expected polling script to run before filling input"

    fill_index = next(
        idx for idx, (event_name, _) in enumerate(events) if event_name == "fill"
    )
    assert wait_indices[0] < fill_index

    # Ensure the fill call targeted the autocomplete with the requested symbol
    assert any(
        event_name == "fill"
        and event_payload["selector"] == "input.MuiAutocomplete-input"
        and event_payload["value"] == "ETH"
        for event_name, event_payload in events
    )

    # Confirm the timeframe selection script included the requested timeframe
    assert any(
        event_name == "evaluate" and "6 hour" in payload
        for event_name, payload in events
    )
