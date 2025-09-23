"""
BrowserCat MCP Client Service

This module provides a client interface to interact with the BrowserCat MCP server
for browser automation tasks like navigation, screenshot capture, and JavaScript execution.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class BrowserCatMCPClient:
    """Client for interacting with BrowserCat MCP server via Smithery"""

    DEFAULT_BASE_URL = "https://server.smithery.ai/@dmaznest/browsercat-mcp-server"
    DEFAULT_TIMEOUT = 30
    RETRY_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """Initialize the BrowserCat MCP client.

        Args:
            api_key: BrowserCat API key (can also be set via BROWSERCAT_API_KEY env var).
            base_url: Base URL for the BrowserCat MCP server (defaults to env or Smithery URL).
            timeout: Request timeout in seconds (defaults to env or 30 seconds).
            max_retries: Maximum retry attempts for transient failures.
            backoff_factor: Exponential backoff factor applied between retries.
        """

        env_base_url = os.getenv("BROWSERCAT_BASE_URL")
        env_timeout = os.getenv("BROWSERCAT_TIMEOUT")

        self.api_key = api_key or os.getenv("BROWSERCAT_API_KEY")
        self.base_url = base_url or env_base_url or self.DEFAULT_BASE_URL
        self.timeout = self._resolve_timeout(timeout, env_timeout)
        self.max_retries = max(1, max_retries)
        self.backoff_factor = max(0.0, backoff_factor)
        self._session = requests.Session()

        if not self.api_key:
            logger.warning(
                "No BrowserCat API key provided. Some functionality may be limited."
            )

    @classmethod
    def _resolve_timeout(cls, timeout_arg: Optional[float], env_timeout: Optional[str]) -> float:
        """Resolve timeout precedence and ensure a valid float value."""

        if timeout_arg is not None:
            return float(timeout_arg)

        if env_timeout:
            try:
                return float(env_timeout)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid BROWSERCAT_TIMEOUT value '%s'. Falling back to default.",
                    env_timeout,
                )

        return float(cls.DEFAULT_TIMEOUT)

    def _sleep_with_backoff(self, attempt: int) -> None:
        """Sleep using exponential backoff based on the attempt count."""

        if self.backoff_factor <= 0:
            return

        delay = self.backoff_factor * (2 ** attempt)
        time.sleep(delay)

    def _should_retry(self, status_code: Optional[int]) -> bool:
        """Return True when the response status warrants a retry."""

        if status_code is None:
            return True

        return status_code in self.RETRY_STATUS_CODES
    
    def _make_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the BrowserCat MCP server

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool

        Returns:
            Response from the MCP server
        """
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"tool": tool_name, "arguments": arguments}

        last_error: Optional[Dict[str, Any]] = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.post(
                    f"{self.base_url}/tools/{tool_name}",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return response.json()

                error_details: Dict[str, Any] = {
                    "error": f"Request failed with status {response.status_code}",
                    "status_code": response.status_code,
                }

                try:
                    error_details["response"] = response.json()
                except (json.JSONDecodeError, ValueError):
                    error_details["response_text"] = response.text

                logger.error(
                    "BrowserCat MCP request failed: %s - %s",
                    response.status_code,
                    response.text,
                )

                last_error = error_details

                if attempt < self.max_retries - 1 and self._should_retry(response.status_code):
                    self._sleep_with_backoff(attempt)
                    continue

                return error_details

            except RequestException as exc:
                logger.error("Error making BrowserCat MCP request: %s", exc)
                last_error = {"error": str(exc), "status_code": None}

                if attempt < self.max_retries - 1 and self._should_retry(None):
                    self._sleep_with_backoff(attempt)
                    continue

                return last_error

        return last_error or {"error": "Unknown error", "status_code": None}
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            Response from navigation
        """
        return self._make_request("browsercat_navigate", {"url": url})
    
    def screenshot(self, name: str, selector: Optional[str] = None, 
                  width: int = 1200, height: int = 800) -> Dict[str, Any]:
        """
        Take a screenshot
        
        Args:
            name: Name for the screenshot
            selector: CSS selector for element to screenshot (optional)
            width: Screenshot width
            height: Screenshot height
            
        Returns:
            Response with screenshot information
        """
        arguments = {
            "name": name,
            "width": width,
            "height": height
        }
        
        if selector:
            arguments["selector"] = selector
            
        return self._make_request("browsercat_screenshot", arguments)
    
    def click(self, selector: str) -> Dict[str, Any]:
        """
        Click an element
        
        Args:
            selector: CSS selector for element to click
            
        Returns:
            Response from click action
        """
        return self._make_request("browsercat_click", {"selector": selector})
    
    def evaluate(self, script: str) -> Dict[str, Any]:
        """
        Execute JavaScript in the browser
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Response from script execution
        """
        return self._make_request("browsercat_evaluate", {"script": script})
    
    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """
        Fill an input field
        
        Args:
            selector: CSS selector for input field
            value: Value to fill
            
        Returns:
            Response from fill action
        """
        return self._make_request("browsercat_fill", {"selector": selector, "value": value})
    
    def capture_coinglass_heatmap(self, symbol: str = "BTC", time_period: str = "24 hour") -> Dict[str, Any]:
        """
        Capture Coinglass liquidation heatmap
        
        Args:
            symbol: Cryptocurrency symbol
            time_period: Time period for the heatmap
            
        Returns:
            Response with screenshot path or error
        """
        try:
            # Navigate to Coinglass liquidation heatmap page
            nav_result = self.navigate("https://www.coinglass.com/pro/futures/LiquidationHeatMap")
            if "error" in nav_result:
                return nav_result
            
            # Wait for page to load
            wait_script = "new Promise(resolve => setTimeout(resolve, 5000))"
            self.evaluate(wait_script)
            
            # Select symbol if not BTC
            if symbol != "BTC":
                # Click Symbol tab using text matching since :contains is not supported
                symbol_tab_script = """
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button[role="tab"]'));
                    const target = buttons.find(btn => (btn.textContent || '').trim().toLowerCase() === 'symbol');
                    if (target) {
                        target.click();
                        return true;
                    }
                    return false;
                })();
                """
                symbol_tab_result = self.evaluate(symbol_tab_script)
                if isinstance(symbol_tab_result, dict) and symbol_tab_result.get("error"):
                    logger.warning(f"Could not click symbol tab: {symbol_tab_result}")
                elif not (isinstance(symbol_tab_result, dict) and symbol_tab_result.get("result")):
                    logger.warning("Symbol tab not found via text search.")

                # Wait for symbol autocomplete input to be present before interacting
                wait_for_symbol_input_script = """
                new Promise((resolve) => {
                    const timeoutMs = 10000;
                    const intervalMs = 250;
                    const start = Date.now();

                    const poll = () => {
                        if (document.querySelector('input.MuiAutocomplete-input')) {
                            resolve(true);
                        } else if (Date.now() - start >= timeoutMs) {
                            resolve(false);
                        } else {
                            setTimeout(poll, intervalMs);
                        }
                    };

                    poll();
                });
                """
                wait_for_input = self.evaluate(wait_for_symbol_input_script)
                input_ready = isinstance(wait_for_input, dict) and not wait_for_input.get("error") and bool(wait_for_input.get("result"))

                if input_ready:
                    # Fill symbol input
                    symbol_input_result = self.fill("input.MuiAutocomplete-input", symbol)
                    if "error" in symbol_input_result:
                        logger.warning(f"Could not fill symbol input: {symbol_input_result}")
                else:
                    logger.warning("Symbol autocomplete input did not appear before timeout.")

                # Press Enter to select
                enter_script = """
                const input = document.querySelector('input.MuiAutocomplete-input');
                if (input) {
                    const event = new KeyboardEvent('keydown', { key: 'Enter' });
                    input.dispatchEvent(event);
                }
                """
                self.evaluate(enter_script)
                
                # Wait for chart to update
                self.evaluate("new Promise(resolve => setTimeout(resolve, 10000))")
            
            # Select time period
            time_select_script = f"""
            const timeDropdown = document.querySelector('div.MuiSelect-root button.MuiSelect-button');
            if (timeDropdown && timeDropdown.textContent.trim() !== '{time_period}') {{
                timeDropdown.click();
                setTimeout(() => {{
                    const options = document.querySelectorAll('li[role="option"]');
                    for(let i = 0; i < options.length; i++) {{
                        if(options[i].textContent.includes('{time_period}')) {{
                            options[i].click();
                            break;
                        }}
                    }}
                }}, 1000);
            }}
            """
            self.evaluate(time_select_script)
            
            # Wait for chart to update
            self.evaluate("new Promise(resolve => setTimeout(resolve, 5000))")
            
            # Take screenshot of the heatmap
            screenshot_name = f"{symbol.lower()}_heatmap_{time_period.replace(' ', '_')}"
            screenshot_result = self.screenshot(
                name=screenshot_name,
                selector="div.echarts-for-react",
                width=1200,
                height=800
            )
            
            return screenshot_result
            
        except Exception as e:
            logger.error(f"Error capturing Coinglass heatmap: {e}")
            return {"error": str(e)}


# Singleton instance
browsercat_client = BrowserCatMCPClient()

