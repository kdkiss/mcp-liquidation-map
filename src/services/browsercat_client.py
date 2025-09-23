"""
BrowserCat MCP Client Service

This module provides a client interface to interact with the BrowserCat MCP server
for browser automation tasks like navigation, screenshot capture, and JavaScript execution.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

class BrowserCatMCPClient:
    """Client for interacting with BrowserCat MCP server via Smithery"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the BrowserCat MCP client
        
        Args:
            api_key: BrowserCat API key (can also be set via BROWSERCAT_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('BROWSERCAT_API_KEY')
        self.base_url = "https://server.smithery.ai/@dmaznest/browsercat-mcp-server"
        
        if not self.api_key:
            logger.warning("No BrowserCat API key provided. Some functionality may be limited.")
    
    def _make_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the BrowserCat MCP server
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Response from the MCP server
        """
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            payload = {
                "tool": tool_name,
                "arguments": arguments
            }
            
            response = requests.post(
                f"{self.base_url}/tools/{tool_name}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"BrowserCat MCP request failed: {response.status_code} - {response.text}")
                return {"error": f"Request failed with status {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error making BrowserCat MCP request: {e}")
            return {"error": str(e)}
    
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

