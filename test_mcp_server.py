#!/usr/bin/env python3
"""
Test script for the Liquidation Map MCP Server
"""

import asyncio
import base64
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from liquidation_map_mcp_server import LiquidationMapMCPServer
from playwright.sync_api import sync_playwright


def playwright_available() -> bool:
    """Return True if Playwright and its browsers are available."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        print(f"Playwright not available: {e}")
        return False

async def test_server_basic():
    """Test basic server functionality"""
    print("Testing basic server functionality...")
    
    server = LiquidationMapMCPServer()
    
    # Test server info
    info = server.get_server_info()
    print(f"Server info: {info}")
    
    # Test capabilities
    capabilities = server.get_capabilities()
    print(f"Server capabilities: {capabilities}")
    
    print("✓ Basic server functionality test passed")

async def test_liquidation_map_tool():
    """Test the get_liquidation_map tool"""
    print("\nTesting get_liquidation_map tool...")
    
    server = LiquidationMapMCPServer()
    
    # Test with BTC 24 hour
    try:
        print("Testing BTC 24 hour liquidation map...")
        result = await server.get_liquidation_map("BTC", "24 hour")
        
        if "content" in result and len(result["content"]) > 0:
            # Check if we have image content
            image_content = None
            text_content = None
            
            for content in result["content"]:
                if content["type"] == "image":
                    image_content = content
                elif content["type"] == "text":
                    text_content = content
            
            if image_content:
                print("✓ Image content found")
                # Save the image for verification
                image_data = base64.b64decode(image_content["data"])
                with open("/home/ubuntu/test_btc_24h.png", "wb") as f:
                    f.write(image_data)
                print(f"✓ Image saved to test_btc_24h.png ({len(image_data)} bytes)")
            else:
                print("✗ No image content found")
            
            if text_content:
                print(f"✓ Text content: {text_content['text']}")
            else:
                print("✗ No text content found")
        else:
            print("✗ No content in result")
            
    except Exception as e:
        print(f"✗ Error testing BTC 24 hour: {e}")
    
    # Test with ETH 12 hour
    try:
        print("\nTesting ETH 12 hour liquidation map...")
        result = await server.get_liquidation_map("ETH", "12 hour")
        
        if "content" in result and len(result["content"]) > 0:
            # Check if we have image content
            image_content = None
            
            for content in result["content"]:
                if content["type"] == "image":
                    image_content = content
                    break
            
            if image_content:
                print("✓ Image content found")
                # Save the image for verification
                image_data = base64.b64decode(image_content["data"])
                with open("/home/ubuntu/test_eth_12h.png", "wb") as f:
                    f.write(image_data)
                print(f"✓ Image saved to test_eth_12h.png ({len(image_data)} bytes)")
            else:
                print("✗ No image content found")
        else:
            print("✗ No content in result")
            
    except Exception as e:
        print(f"✗ Error testing ETH 12 hour: {e}")

async def test_invalid_inputs():
    """Test invalid inputs"""
    print("\nTesting invalid inputs...")
    
    server = LiquidationMapMCPServer()
    
    # Test invalid timeframe
    try:
        await server.get_liquidation_map("BTC", "1 week")
        print("✗ Should have failed with invalid timeframe")
    except ValueError as e:
        print(f"✓ Correctly rejected invalid timeframe: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

async def main():
    """Run all tests"""
    print("Starting MCP Server Tests...")
    print("=" * 50)

    await test_server_basic()

    if not playwright_available():
        print("Playwright not available. Skipping tool tests.")

    else:
        await test_liquidation_map_tool()

    await test_invalid_inputs()
    
    print("\n" + "=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

