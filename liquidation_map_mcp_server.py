#!/usr/bin/env python3
"""
Smithery-compatible MCP Server for Liquidation Maps
Allows users to request liquidation maps (24-hour or 12-hour) and retrieve corresponding images.
"""

import os
import logging
import requests
import time
import json
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from io import BytesIO
from PIL import Image

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class LiquidationMapMCPServer:
    """MCP Server for generating liquidation heatmaps"""
    
    def __init__(self):
        self.name = "liquidation-map-server"
        self.version = "1.0.0"
        self.description = "MCP server for generating cryptocurrency liquidation heatmaps"
        
    def get_server_info(self) -> Dict[str, Any]:
        """Return server information for MCP initialization"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities for MCP"""
        return {
            "tools": {
                "get_liquidation_map": {
                    "description": "Get a liquidation heatmap for a cryptocurrency",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Cryptocurrency symbol (e.g., BTC, ETH)"
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Time period for the heatmap (12 hour or 24 hour)",
                                "enum": ["12 hour", "24 hour"]
                            }
                        },
                        "required": ["symbol", "timeframe"]
                    }
                }
            }
        }
    
    def setup_webdriver(self, max_retries=3, retry_delay=2):
        """Configure and return a local Chrome WebDriver instance with retries using webdriver-manager"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Creating ChromeDriver instance with webdriver-manager (attempt {attempt+1}/{max_retries})")
                    
                    # Use webdriver-manager to automatically download and manage ChromeDriver
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    
                    logger.info("Successfully created ChromeDriver instance")
                    return driver
                    
                except Exception as e:
                    logger.warning(f"Failed to create ChromeDriver: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error("Max retries exceeded. Could not create ChromeDriver.")
                        raise
                        
        except ImportError:
            logger.error("webdriver-manager not found. Please install it with: pip install webdriver-manager")
            raise

    def get_crypto_price(self, symbol: str) -> Optional[str]:
        """Fetch the current crypto price from CoinGecko API"""
        try:
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
                    return f"${price:,.2f}"
            
            return None
        except Exception as e:
            logger.error(f"Error fetching {symbol} price: {e}")
            return None

    async def capture_coinglass_heatmap(self, symbol: str = "BTC", time_period: str = "24 hour") -> bytes:
        """
        Capture the Coinglass liquidation heatmap
        
        Args:
            symbol (str): Cryptocurrency symbol (e.g., "BTC", "ETH")
            time_period (str): Time period to select (e.g., "24 hour", "12 hour")
            
        Returns:
            bytes: PNG image data
        """
        driver = None
        try:
            logger.info(f"Starting capture of Coinglass {symbol} heatmap with {time_period} timeframe")
            driver = self.setup_webdriver()
            
            # Navigate to Coinglass liquidation page
            driver.get("https://www.coinglass.com/pro/futures/LiquidationHeatMap")
            wait = WebDriverWait(driver, 20)
            
            # Optimize page for screenshot
            driver.execute_script("""
                var style = document.createElement('style');
                style.innerHTML = `
                    * {
                        transition: none !important;
                        animation: none !important;
                    }
                    .echarts-for-react {
                        width: 100% !important;
                        height: 100% !important;
                    }
                    canvas {
                        image-rendering: -webkit-optimize-contrast !important;
                        image-rendering: crisp-edges !important;
                    }
                `;
                document.head.appendChild(style);
                window.devicePixelRatio = 2;
            """)
            
            # Wait for page to load
            time.sleep(5)
            
            # Use JavaScript to force symbol change
            if symbol != "BTC":
                try:
                    # Click Symbol tab first
                    symbol_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@role='tab' and contains(text(), 'Symbol')]")))
                    symbol_tab.click()
                    time.sleep(2)
                    logger.info("Clicked Symbol tab")
                    
                    # Use actual user simulation instead of JavaScript
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Find the input element
                    input_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.MuiAutocomplete-input")))
                    
                    # Clear the input by selecting all and typing
                    actions = ActionChains(driver)
                    actions.click(input_element)
                    actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                    actions.send_keys(symbol)
                    actions.perform()
                    
                    time.sleep(2)
                    logger.info(f"Typed {symbol} into input field")
                    
                    # Try to click on dropdown option or press Enter
                    try:
                        # Wait for dropdown to appear and click option
                        option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[@role='option' and text()='{symbol}']")))
                        option.click()
                        logger.info(f"Clicked {symbol} option from dropdown")
                    except:
                        # Fallback: press Enter
                        actions = ActionChains(driver)
                        actions.send_keys(Keys.ENTER)
                        actions.perform()
                        logger.info(f"Pressed Enter to select {symbol}")
                    
                    # Wait for chart to update
                    time.sleep(15)
                    logger.info(f"Waited for chart to update with {symbol} data")
                    
                except Exception as symbol_e:
                    logger.warning(f"Could not select symbol {symbol}: {symbol_e}")
            else:
                logger.info("Using default BTC symbol")
            
            # Find and click the time period dropdown button
            time_dropdown = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "div.MuiSelect-root button.MuiSelect-button"
            )))
            
            if time_dropdown.text.strip() != time_period:
                time_dropdown.click()
                time.sleep(2)
                
                driver.execute_script(f"""
                    var options = document.querySelectorAll('li[role="option"]');
                    for(var i = 0; i < options.length; i++) {{
                        if(options[i].textContent.includes('{time_period}')) {{
                            options[i].click();
                            break;
                        }}
                    }}
                """)
                time.sleep(3)
            
            # Find and capture the chart
            try:
                heatmap_container = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, "div.echarts-for-react"
                )))
            except Exception:
                heatmap_container = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//div[contains(@class, 'echarts-for-react')]"
                )))
            
            time.sleep(3)
            
            rect = driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return {
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height
                };
            """, heatmap_container)
            
            # Capture screenshot with CDP
            result = driver.execute_cdp_cmd('Page.captureScreenshot', {
                'clip': {
                    'x': rect['x'],
                    'y': rect['y'],
                    'width': rect['width'],
                    'height': rect['height'],
                    'scale': 2
                },
                'captureBeyondViewport': True,
                'fromSurface': True
            })
            
            png_data = base64.b64decode(result['data'])
            return png_data
            
        except Exception as e:
            logger.error(f"Error capturing heatmap: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    async def get_liquidation_map(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Handle get_liquidation_map tool call"""
        symbol = symbol.upper()
        timeframe = timeframe.lower()
        
        # Validate timeframe
        if timeframe not in ["12 hour", "24 hour"]:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be '12 hour' or '24 hour'")
        
        logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
        
        # Get the heatmap image
        image_data = await self.capture_coinglass_heatmap(symbol, timeframe)
        
        if not image_data:
            raise Exception("Failed to generate liquidation map")
        
        # Convert image to base64 for JSON-RPC response
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get current price
        price = self.get_crypto_price(symbol)
        
        return {
            "content": [
                {
                    "type": "image",
                    "data": image_base64,
                    "mimeType": "image/png"
                },
                {
                    "type": "text",
                    "text": f"Liquidation heatmap for {symbol} ({timeframe})" + (f" - Current price: {price}" if price else "")
                }
            ]
        }

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool calls"""
        if tool_name == "get_liquidation_map":
            symbol = arguments.get("symbol", "BTC")
            timeframe = arguments.get("timeframe", "24 hour")
            return await self.get_liquidation_map(symbol, timeframe)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

# For FastMCP compatibility
def create_server():
    """Create and return the MCP server instance"""
    return LiquidationMapMCPServer()

if __name__ == "__main__":
    # For testing purposes
    import asyncio
    
    async def test_server():
        server = LiquidationMapMCPServer()
        
        # Test the tool
        result = await server.get_liquidation_map("BTC", "24 hour")
        print("Tool result:", result)
    
    asyncio.run(test_server())

