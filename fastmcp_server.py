#!/usr/bin/env python3
"""
FastMCP-compatible MCP Server for Liquidation Maps
Uses the FastMCP library for simplified MCP server creation.
"""

import asyncio
import base64
import logging
from typing import Optional
from playwright.async_api import async_playwright
from mcp.types import Context
import requests
from fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

mcp: FastMCP | None = None

def get_server_info() -> dict:
    return {
        "name": "liquidation-map-server",
        "version": "1.0.0",
        "description": "MCP server for generating cryptocurrency liquidation heatmaps",
        "connectionTypes": {"stdio": {}},
    }

def get_crypto_price(symbol: str) -> Optional[str]:
    try:
        symbol_map = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'BNB': 'binancecoin', 'ADA': 'cardano',
            'SOL': 'solana', 'XRP': 'ripple', 'DOT': 'polkadot', 'DOGE': 'dogecoin',
            'AVAX': 'avalanche-2', 'MATIC': 'matic-network'
        }
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            price = response.json().get(coin_id, {}).get('usd')
            if price:
                return f"${price:,.2f}"
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol}: {e}")
    return None

async def capture_coinglass_heatmap(symbol: str = "BTC", time_period: str = "24 hour", ctx: Optional[Context] = None) -> bytes:
    try:
        if ctx:
            await ctx.report_progress(5, 100, "Launching browser")

        logger.info(f"Capturing Coinglass {symbol} heatmap for {time_period}")
        p = await async_playwright()
        try:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
            page = await context.new_page()

            await page.goto("https://www.coinglass.com/pro/futures/LiquidationHeatMap", timeout=60000)
            if ctx:
                await ctx.report_progress(25, 100, "Page loaded")

            await page.add_style_tag(content="""
                * { transition: none !important; animation: none !important; }
                .echarts-for-react { width: 100% !important; height: 100% !important; }
                canvas { image-rendering: -webkit-optimize-contrast !important; image-rendering: crisp-edges !important; }
            """)

            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector("div.MuiSelect-root button.MuiSelect-button")

            if symbol != "BTC":
                try:
                    await page.click("//button[@role='tab' and contains(text(), 'Symbol')]")
                    await page.wait_for_selector("input.MuiAutocomplete-input")
                    await page.fill("input.MuiAutocomplete-input", symbol)
                    try:
                        await page.click(f"//li[@role='option' and text()='{symbol}']", timeout=5000)
                    except:
                        await page.keyboard.press("Enter")
                    await page.wait_for_load_state("networkidle")
                except Exception as symbol_e:
                    logger.warning(f"Could not select symbol {symbol}: {symbol_e}")

            current_time = (await page.inner_text("div.MuiSelect-root button.MuiSelect-button")).strip()
            if current_time != time_period:
                await page.click("div.MuiSelect-root button.MuiSelect-button")
                await page.wait_for_selector("li[role='option']")
                await page.click(f"//li[@role='option' and contains(text(), '{time_period}')]")
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
    symbol = symbol.upper()
    timeframe = timeframe.lower()

    if timeframe not in ["12 hour", "24 hour"]:
        raise ValueError(f"Invalid timeframe: {timeframe}. Must be '12 hour' or '24 hour'")

    logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
    await ctx.report_progress(0, 100, "Starting")

    image_data = await capture_coinglass_heatmap(symbol, timeframe, ctx)
    if not image_data:
        raise RuntimeError("Failed to generate liquidation map: no image data")

    await ctx.report_progress(95, 100, "Preparing result")
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    await ctx.report_progress(100, 100, "Encoding image")

    price = get_crypto_price(symbol)
    result = f"Liquidation heatmap for {symbol} ({timeframe})"
    if price:
        result += f" - Current price: {price}"
    result += f"\n\nImage data (base64): data:image/png;base64,{image_base64}"

    await ctx.report_progress(100, 100, "Done")
    return result

def create_server() -> FastMCP:
    global mcp
    if mcp is None:
        mcp = FastMCP("Liquidation Map Server")
        if hasattr(mcp, "request_timeout"):
            mcp.request_timeout = 120
        mcp.tool()(get_liquidation_map)
        mcp.get_server_info = get_server_info  # type: ignore[attr-defined]
    return mcp

if __name__ == "__main__":
    create_server().run()
