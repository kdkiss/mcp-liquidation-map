import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.browsercat_client import BrowserCatMCPClient


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
