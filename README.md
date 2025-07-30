# Liquidation Map MCP Server

[![smithery badge](https://smithery.ai/badge/@kdkiss/mcp-liquidation-map)](https://smithery.ai/server/@kdkiss/mcp-liquidation-map)

A Smithery-compatible Model Context Protocol (MCP) server that provides cryptocurrency liquidation heatmaps. Users can request liquidation maps for different cryptocurrencies with 12-hour or 24-hour timeframes, and the server returns high-quality images of the liquidation data.

## Features

- **Cryptocurrency Support**: Works with major cryptocurrencies (BTC, ETH, BNB, ADA, SOL, XRP, DOT, DOGE, AVAX, MATIC, and more)
- **Multiple Timeframes**: Supports both 12-hour and 24-hour liquidation maps
- **High-Quality Images**: Returns PNG images with optimized resolution and clarity
- **Real-time Price Data**: Includes current cryptocurrency prices from CoinGecko API
- **Smithery Compatible**: Fully compatible with Smithery's MCP server registry and deployment platform
- **FastMCP Integration**: Built using the FastMCP library for simplified development

## Quick Start

### Installing via Smithery

To install Liquidation Map for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@kdkiss/mcp-liquidation-map):

```bash
npx -y @smithery/cli install @kdkiss/mcp-liquidation-map --client claude
```

### Option 1: Deploy on Smithery (Recommended)

1. Fork this repository to your GitHub account
2. Visit [Smithery.ai](https://smithery.ai)
3. Click "Deploy" and connect your GitHub repository
4. Smithery will automatically build and deploy your MCP server
5. The deployment sets the `CHROMEDRIVER_PATH` environment variable to
   `/usr/local/bin/chromedriver` so ChromeDriver works out of the box. If you
   use a custom path or your environment is offline, update `smithery.yaml`
   accordingly and ensure ChromeDriver is pre-installed at that location.
6. Use the provided URL to connect to your server from any MCP-compatible client

### Option 2: Local Development

#### Prerequisites

- Python 3.11+
- Google Chrome browser
- ChromeDriver (compatible with your Chrome version)
- Git

#### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd liquidation-map-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Chrome and ChromeDriver:
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Download compatible ChromeDriver
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+')
wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip
sudo unzip /tmp/chromedriver.zip -d /tmp/
sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

4. Set environment variables (optional):
```bash
export CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
```
If `CHROMEDRIVER_PATH` is not set or the path does not exist, Selenium will
attempt to download a compatible ChromeDriver using Selenium Manager.
In offline environments, this download will fail, so you must pre-install
ChromeDriver and set `CHROMEDRIVER_PATH` accordingly.

5. Run the server:
```bash
python fastmcp_server.py
```

## Usage

### Tool: get_liquidation_map

Retrieves a liquidation heatmap for a specified cryptocurrency and timeframe.

**Parameters:**
- `symbol` (string, required): Cryptocurrency symbol (e.g., "BTC", "ETH", "SOL")
- `timeframe` (string, required): Time period for the heatmap ("12 hour" or "24 hour")

**Returns:**
- Base64-encoded PNG image of the liquidation heatmap
- Text description with symbol, timeframe, and current price

**Example Usage:**

```python
# Using the MCP client
result = await client.call_tool("get_liquidation_map", {
    "symbol": "BTC",
    "timeframe": "24 hour"
})
```

### Supported Cryptocurrencies

The server supports all major cryptocurrencies available on Coinglass, including:
- Bitcoin (BTC)
- Ethereum (ETH)
- Binance Coin (BNB)
- Cardano (ADA)
- Solana (SOL)
- Ripple (XRP)
- Polkadot (DOT)
- Dogecoin (DOGE)
- Avalanche (AVAX)
- Polygon (MATIC)
- And many more...

## Architecture

### Core Components

1. **LiquidationMapMCPServer**: Main server class implementing MCP protocol
2. **FastMCP Integration**: Simplified server setup using FastMCP library
3. **Web Scraping Engine**: Selenium-based automation for capturing Coinglass heatmaps
4. **Price API Integration**: CoinGecko API for real-time cryptocurrency prices
5. **Image Processing**: High-quality PNG generation with optimized compression

### Data Sources

- **Liquidation Data**: [Coinglass](https://www.coinglass.com/pro/futures/LiquidationHeatMap)
- **Price Data**: [CoinGecko API](https://api.coingecko.com/api/v3/)

## Configuration

### Environment Variables

 - `CHROMEDRIVER_PATH`: Path to ChromeDriver executable (default: `/usr/local/bin/chromedriver`). If the path doesn't exist, Selenium Manager will try to download a compatible driver. For offline setups, install ChromeDriver manually and set this path.
 - `PYTHONUNBUFFERED`: Set to `1` for real-time logging

### Docker Configuration

The included Dockerfile provides a complete containerized environment. It
automatically installs a ChromeDriver version that matches the Chrome browser
installed in the image:

```dockerfile
FROM python:3.11-slim
# Installs Chrome, ChromeDriver, and all dependencies
# Exposes port 8000 for the MCP server
```

## Testing

Run the test suite to verify functionality:

```bash
python test_mcp_server.py
```

The tests that capture screenshots require ChromeDriver. If the executable is not
found at the path specified by `CHROMEDRIVER_PATH`, those tests will be skipped.

The test suite includes:
- Basic server functionality tests
- Tool execution tests for both 12-hour and 24-hour timeframes
- Input validation tests
- Image generation verification

## Deployment

### Smithery Deployment

1. Ensure your repository includes:
   - `fastmcp_server.py` (main server file)
   - `requirements.txt` (dependencies)
   - `Dockerfile` (container configuration)

2. Push to GitHub and deploy via Smithery dashboard

3. Smithery automatically sets `CHROMEDRIVER_PATH` to
   `/usr/local/bin/chromedriver`. Adjust the path in `smithery.yaml` if your
   deployment uses a different location.

4. Smithery will provide a public URL for your MCP server

### Manual Docker Deployment

```bash
# Build the Docker image
docker build -t liquidation-map-mcp .

# Run the container
docker run -p 8000:8000 liquidation-map-mcp
```

## Troubleshooting

### Common Issues

1. **ChromeDriver Version Mismatch**
   - Ensure ChromeDriver version matches your Chrome browser version
   - Download the correct version from [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)

2. **Selenium Timeout Errors**
   - Check internet connectivity
   - Verify Coinglass website accessibility
   - Increase timeout values if needed

3. **Image Generation Failures**
   - Ensure sufficient memory for Chrome browser
   - Check that the heatmap container element is found on the page

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the [Smithery Documentation](https://smithery.ai/docs)
- Review the [FastMCP Documentation](https://gofastmcp.com)

## Acknowledgments

- [Smithery.ai](https://smithery.ai) for MCP server hosting and registry
- [FastMCP](https://gofastmcp.com) for the Python MCP framework
- [Coinglass](https://www.coinglass.com) for liquidation data
- [CoinGecko](https://www.coingecko.com) for cryptocurrency price data
