import os
import logging
import requests
import time
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

# MCP Server Implementation
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]

class ResourceInfo(BaseModel):
    name: str
    description: str
    type: str

# Create FastAPI app
app = FastAPI(title="Liquidation Map MCP Server", version="1.0.0")

# Create sub-application for MCP endpoints
mcp_app = FastAPI()

# Add CORS middleware to both apps
for _app in [app, mcp_app]:
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount MCP app at /mcp
app.mount("/mcp", mcp_app)

# For backward compatibility, also include the endpoints on the root path
jsonrpc_app = app

# Tool definitions
TOOLS = {
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
                    "description": "Time period for the heatmap",
                    "enum": ["12 hour", "24 hour", "1 month", "3 month"]
                }
            },
            "required": ["symbol", "timeframe"]
        },
        "returns": {
            "type": "string",
            "format": "binary",
            "description": "PNG image of the liquidation heatmap"
        }
    }
}

# MCP Endpoints
@mcp_app.post("/")
@app.post("/")  # Keep for backward compatibility
async def handle_jsonrpc(request: JSONRPCRequest):
    """Handle JSON-RPC 2.0 requests"""
    if request.jsonrpc != "2.0":
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "jsonrpc version must be 2.0"
                },
                "id": request.id
            }
        )
    
    handler = {
        "initialize": handle_initialize,
        "tools/list": handle_tools_list,
        "tools/call": handle_tools_call,
        "resources/list": handle_resources_list,
    }.get(request.method)
    
    if not handler:
        return JSONResponse(
            status_code=404,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                },
                "id": request.id
            }
        )
    
    try:
        result = await handler(request.params or {})
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id
        }
    except Exception as e:
        logger.error(f"Error handling {request.method}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": request.id
            }
        )

# MCP Handlers
async def handle_initialize(params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle initialize method
    
    Args:
        params: Optional parameters from the MCP client (unused in this implementation)
    """
    # params is unused but required by the MCP protocol
    return {
        "protocolVersion": "1.0",
        "serverInfo": {
            "name": "Liquidation Map MCP Server",
            "description": "MCP server for generating and serving cryptocurrency liquidation heatmaps",
            "version": "1.0.0"
        },
        "capabilities": {
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
                                "description": "Timeframe for the liquidation map (e.g., '24 hour', '12 hour')",
                                "pattern": "^\\d+\\s+(minute|hour|day|week|month)$"
                            }
                        },
                        "required": ["symbol", "timeframe"]
                    }
                }
            }
        }
    }

async def handle_tools_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/list method"""
    return {"tools": [{"name": name, **info} for name, info in TOOLS.items()]}

async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/call method"""
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    
    if tool_name == "get_liquidation_map":
        return await get_liquidation_map_handler(tool_args)
    
    raise HTTPException(status_code=400, detail=f"Unhandled tool: {tool_name}")

async def handle_resources_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle resources/list method"""
    return {"resources": []}

def setup_webdriver(max_retries=3, retry_delay=2):
    """Configure and return a local Chrome WebDriver instance with retries"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating local ChromeDriver instance (attempt {attempt+1}/{max_retries})")
            
            # Use ChromeDriver from environment or default path
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
            service = Service(chromedriver_path)
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

async def get_liquidation_map_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle get_liquidation_map tool call"""
    symbol = args.get("symbol", "BTC").upper()
    timeframe = args.get("timeframe", "24 hour").lower()
    
    logger.info(f"Generating {symbol} liquidation heatmap for {timeframe}")
    
    # Get the heatmap image
    image_data = await capture_coinglass_heatmap(symbol, timeframe)
    
    if not image_data:
        raise HTTPException(status_code=500, detail="Failed to generate liquidation map")
    
    # Convert image to base64 for JSON-RPC response
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Get current price
    price = get_crypto_price(symbol)
    
    return {
        "image": f"data:image/png;base64,{image_base64}",
        "metadata": {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": price
        }
    }

@app.get("/health")
@mcp_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Legacy endpoint for backward compatibility
@app.get("/get-liquidation-map")
@mcp_app.get("/get-liquidation-map")
async def legacy_get_liquidation_map(
    symbol: str = Query(..., regex="^[A-Za-z0-9-]+$"),
    timeframe: str = Query(..., regex="^[0-9]+ (minute|hour|day|week|month)$")
):
    """Legacy endpoint for backward compatibility"""
    try:
        image_data = await capture_coinglass_heatmap(symbol, timeframe)
        if not image_data:
            raise HTTPException(status_code=500, detail="Failed to generate liquidation map")
            
        price = get_crypto_price(symbol)
        return StreamingResponse(
            BytesIO(image_data),
            media_type="image/png",
            headers={
                "X-Symbol": symbol,
                "X-Timeframe": timeframe,
                "X-Price": price or "N/A"
            }
        )
    except Exception as e:
        logger.error(f"Error in legacy endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Liquidation Map MCP Server on port {port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )