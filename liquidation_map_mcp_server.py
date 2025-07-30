#!/usr/bin/env python3
"""
Smithery-compatible MCP Server for Liquidation Maps
Allows users to request liquidation maps (24-hour or 12-hour) and retrieve corresponding images.
"""

import base64
import logging
from typing import Any, Dict, Optional

import requests
from fastmcp import Context


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
            "description": self.description,
            "connectionTypes": {"stdio": {}},
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

    import base64
import logging
from playwright.async_api import async_playwright
from mcp.types import Context

logger = logging.getLogger(__name__)

async def capture_coinglass_heatmap(
    symbol: str = "BTC",
    time_period: str = "24 hour",
    ctx: Context | None = None,
) -> bytes:
    """Capture the Coinglass liquidation heatmap using Playwright."""
    try:
        if ctx:
            await ctx.report_progress(5, 100, "Launching browser")

        logger.info(f"Starting capture of Coinglass {symbol} heatmap with {time_period} timeframe")

        p = await async_playwright()
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=2,
            )
            page = await context.new_page()

            await page.goto(
                "https://www.coinglass.com/pro/futures/LiquidationHeatMap",
                timeout=60000,
            )
            if ctx:
                await ctx.report_progress(25, 100, "Page loaded")

            await page.add_style_tag(
                content="""
                * { transition: none !important; animation: none !important; }
                .echarts-for-react { width: 100% !important; height: 100% !important; }
                canvas { image-rendering: -webkit-optimize-contrast !important; image-rendering: crisp-edges !important; }
                """
            )

            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector("div.MuiSelect-root button.MuiSelect-button")

            if symbol != "BTC":
                try:
                    await page.click("//button[@role='tab' and contains(text(), 'Symbol')]")
                    await page.wait_for_selector("input.MuiAutocomplete-input")
                    await page.fill("input.MuiAutocomplete-input", symbol)
                    try:
                        await page.click(
                            f"//li[@role='option' and text()='{symbol}']",
                            timeout=5000,
                        )
                    except Exception:
                        await page.keyboard.press("Enter")
                    await page.wait_for_load_state("networkidle")
                except Exception as symbol_e:
                    logger.warning(f"Could not select symbol {symbol}: {symbol_e}")

            current_time = (
                await page.inner_text("div.MuiSelect-root button.MuiSelect-button")
            ).strip()
            if current_time != time_period:
                await page.click("div.MuiSelect-root button.MuiSelect-button")
                await page.wait_for_selector("li[role='option']")
                await page.click(
                    f"//li[@role='option' and contains(text(), '{time_period}')]"
                )
                await page.wait_for_load_state("networkidle")

            heatmap = await page.wait_for_selector("div.echarts-for-react")
            box = await heatmap.bounding_box()

            png_data = await page.screenshot(clip=box, type="png")
            if ctx:
                await ctx.report_progress(90, 100, "Screenshot captured")

            await context.close()
            await browser.close()
            return png_data

        finally:
            await p.stop()

    except Exception as e:
        logger.error(f"Error capturing heatmap: {e}")
        raise RuntimeError(f"Error capturing heatmap: {e}")



async def get_liquidation_map(ctx: Context, symbol: str, timeframe: str) -> str:
    """
    Get a liquidation heatmap for a cryptocurrency.

    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH)
        timeframe: Time period for the heatmap (12 hour or 24 hour)

    Returns:
        Base64 encoded PNG image of the liquidation heatmap
    """
    symbol = symbol.upper()
    timeframe = timeframe.lower()

    if timeframe not in ["12 hour", "24 hour"]:
        raise ValueError(f"Invalid timeframe: {timeframe}. Must be '12 hour' or '24 hour'")

    logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
    await ctx.report_progress(0, 100, "Starting")

    try:
        image_data = await capture_coinglass_heatmap(symbol, timeframe, ctx)
    except Exception as e:
        raise RuntimeError(f"Failed to generate liquidation map: {e}") from e

    if not image_data:
        raise RuntimeError("Failed to generate liquidation map: no image data")

    await ctx.report_progress(95, 100, "Preparing result")

    image_base64 = base64.b64encode(image_data).decode("utf-8")
    await ctx.report_progress(100, 100, "Encoding image")

    # Optional: enrich result with current price (assuming this function exists)
    try:
        price = get_crypto_price(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
        price = None

    result = f"Liquidation heatmap for {symbol} ({timeframe})"
    if price:
        result += f" - Current price: {price}"

    result += f"\n\nImage data (base64): data:image/png;base64,{image_base64}"

    await ctx.report_progress(100, 100, "Done")
    return result


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
