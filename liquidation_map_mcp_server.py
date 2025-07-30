#!/usr/bin/env python3
"""
Smithery-compatible MCP Server for Liquidation Maps
Allows users to request liquidation maps (24-hour or 12-hour) and retrieve corresponding images.
"""

import os
import logging
import requests
import time
import base64
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

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
        """Capture the Coinglass liquidation heatmap using Playwright."""
        try:
            logger.info(
                f"Starting capture of Coinglass {symbol} heatmap with {time_period} timeframe"
            )
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080}, device_scale_factor=2
                )
                page = await context.new_page()

                await page.goto("https://www.coinglass.com/pro/futures/LiquidationHeatMap")

                await page.add_style_tag(
                    content="""
                    * { transition: none !important; animation: none !important; }
                    .echarts-for-react { width: 100% !important; height: 100% !important; }
                    canvas { image-rendering: -webkit-optimize-contrast !important; image-rendering: crisp-edges !important; }
                    """
                )

                await page.wait_for_timeout(5000)

                if symbol != "BTC":
                    try:
                        await page.click("//button[@role='tab' and contains(text(), 'Symbol')]")
                        await page.wait_for_timeout(2000)
                        await page.fill("input.MuiAutocomplete-input", symbol)
                        await page.wait_for_timeout(2000)
                        try:
                            await page.click(f"//li[@role='option' and text()='{symbol}']")
                        except Exception:
                            await page.keyboard.press("Enter")
                        await page.wait_for_timeout(15000)
                    except Exception as symbol_e:
                        logger.warning(f"Could not select symbol {symbol}: {symbol_e}")

                current_time = (
                    await page.inner_text("div.MuiSelect-root button.MuiSelect-button")
                ).strip()
                if current_time != time_period:
                    await page.click("div.MuiSelect-root button.MuiSelect-button")
                    await page.wait_for_timeout(2000)
                    await page.evaluate(
                        "(tp) => { const opts = document.querySelectorAll('li[role=\"option\"]'); for (const o of opts) { if (o.textContent.includes(tp)) { o.click(); break; } } }",
                        time_period,
                    )
                    await page.wait_for_timeout(3000)

                heatmap = await page.wait_for_selector("div.echarts-for-react")
                box = await heatmap.bounding_box()

                png_data = await page.screenshot(clip=box, type="png")

                await browser.close()
                return png_data

        except Exception as e:
            logger.error(f"Error capturing heatmap: {e}")
            raise RuntimeError(f"Error capturing heatmap: {e}")


    async def get_liquidation_map(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Handle get_liquidation_map tool call"""
        symbol = symbol.upper()
        timeframe = timeframe.lower()
        
        # Validate timeframe
        if timeframe not in ["12 hour", "24 hour"]:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be '12 hour' or '24 hour'")
        
        logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
        
        # Get the heatmap image
        try:
            image_data = await self.capture_coinglass_heatmap(symbol, timeframe)
        except Exception as e:
            raise RuntimeError(f"Failed to generate liquidation map: {e}") from e

        if not image_data:
            raise RuntimeError("Failed to generate liquidation map: no image data")
        
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

