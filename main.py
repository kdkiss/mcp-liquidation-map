import os
import logging
import requests
import time
from datetime import datetime
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from io import BytesIO
from PIL import Image
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Liquidation Map MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class LiquidationMapRequest(BaseModel):
    symbol: str
    timeframe: str

def setup_webdriver(max_retries=5, retry_delay=2):
    """Configure and return a remote Chrome WebDriver instance with retries"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=5400,2950")
    chrome_options.add_argument("--force-device-scale-factor=2")
    
    selenium_host = os.getenv('SELENIUM_HOST', 'localhost')
    selenium_port = os.getenv('SELENIUM_PORT', '4444')
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Selenium at http://{selenium_host}:{selenium_port}/wd/hub (attempt {attempt+1}/{max_retries})")
            driver = webdriver.Remote(
                command_executor=f'http://{selenium_host}:{selenium_port}/wd/hub',
                options=chrome_options
            )
            logger.info("Successfully connected to Selenium")
            return driver
        except Exception as e:
            logger.warning(f"Failed to connect to Selenium: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries exceeded. Could not connect to Selenium.")
                raise

def get_crypto_price(symbol: str) -> Optional[str]:
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

async def capture_coinglass_heatmap(symbol: str = "BTC", time_period: str = "24 hour") -> bytes:
    """
    Capture the Coinglass liquidation heatmap
    
    Args:
        symbol (str): Cryptocurrency symbol (e.g., "BTC", "ETH")
        time_period (str): Time period to select (e.g., "24 hour", "1 month", "3 month")
        
    Returns:
        bytes: PNG image data
    """
    driver = None
    try:
        logger.info(f"Starting capture of Coinglass {symbol} heatmap with {time_period} timeframe")
        driver = setup_webdriver()
        
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

@app.post("/get-liquidation-map")
async def get_liquidation_map(request: LiquidationMapRequest):
    """
    Get a liquidation heatmap for a given symbol and timeframe
    
    Example request body:
    {
        "symbol": "BTC",
        "timeframe": "24 hour"
    }
    """
    try:
        symbol = request.symbol.upper()
        timeframe = request.timeframe.lower()
        
        logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
        
        # Get the heatmap image
        image_data = await capture_coinglass_heatmap(symbol, timeframe)
        
        if image_data:
            # Get current price
            price = get_crypto_price(symbol)
            price_text = f"Current {symbol} price: {price}\\n" if price else ""
            
            # Return the image with metadata
            return StreamingResponse(
                BytesIO(image_data),
                media_type="image/png",
                headers={
                    "X-Symbol": symbol,
                    "X-Timeframe": timeframe,
                    "X-Price": price or "N/A"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate liquidation map")
    except Exception as e:
        logger.error(f"Error in get_liquidation_map: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Liquidation Map MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)