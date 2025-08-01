# Crypto Heatmap MCP Server

A Smithery-compatible Model Context Protocol (MCP) server that provides cryptocurrency price fetching and Coinglass liquidation heatmap capture functionality. This server replicates the core functionality of the original Python script without Telegram notifications.

## Features

- **Cryptocurrency Price Fetching**: Get real-time cryptocurrency prices using CoinGecko API
- **Liquidation Heatmap Capture**: Capture Coinglass liquidation heatmaps using BrowserCat MCP integration
- **RESTful API**: Clean HTTP endpoints for easy integration
- **Error Handling**: Graceful fallback responses when external services are unavailable
- **Health Monitoring**: Built-in health check endpoint

## API Endpoints

### 1. Get Cryptocurrency Price

**Endpoint**: `/api/get_crypto_price`  
**Methods**: GET, POST  
**Parameters**:
- `symbol` (string, required): Cryptocurrency symbol (e.g., "BTC", "ETH")

**Example Request**:
```bash
curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"
```

**Example Response**:
```json
{
  "price": "$113,975.00",
  "symbol": "BTC"
}
```

### 2. Capture Liquidation Heatmap

**Endpoint**: `/api/capture_heatmap`  
**Methods**: GET, POST  
**Parameters**:
- `symbol` (string, required): Cryptocurrency symbol (e.g., "BTC", "ETH")
- `time_period` (string, optional, default: "24 hour"): Time period ("12 hour", "24 hour", "1 month", "3 month")

**Example Request**:
```bash
curl "http://localhost:5001/api/capture_heatmap?symbol=BTC&time_period=24%20hour"
```

**Example Response**:
```json
{
  "image_path": "/tmp/btc_liquidation_heatmap_20250802_013339_24_hour.png",
  "symbol": "BTC",
  "time_period": "24 hour",
  "note": "BrowserCat capture failed: Request failed with status 401. Returning simulated response.",
  "browsercat_error": "Request failed with status 401"
}
```

### 3. Health Check

**Endpoint**: `/api/health`  
**Method**: GET

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-02T01:34:50.359764"
}
```

## Installation and Setup

### Prerequisites

- Python 3.11+
- Virtual environment support

### Installation Steps

1. **Clone or extract the project**:
   ```bash
   cd crypto_heatmap_mcp
   ```

2. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies** (already included):
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up BrowserCat API Key** (optional, for real heatmap capture):
   ```bash
   export BROWSERCAT_API_KEY="your-api-key-here"
   ```
   Get a free API key at: https://browsercat.xyz/mcp

5. **Run the server**:
   ```bash
   python src/main.py
   ```

The server will start on `http://localhost:5001`

## Architecture

### Core Components

- **Flask Application**: Main web server framework
- **Crypto Routes**: API endpoints for cryptocurrency operations
- **BrowserCat Client**: Integration with Smithery's BrowserCat MCP for browser automation
- **Error Handling**: Graceful fallbacks when external services are unavailable

### File Structure

```
crypto_heatmap_mcp/
├── src/
│   ├── main.py                     # Main Flask application
│   ├── routes/
│   │   ├── crypto.py              # Cryptocurrency API endpoints
│   │   └── user.py                # Template user routes (unused)
│   ├── services/
│   │   └── browsercat_client.py   # BrowserCat MCP integration
│   ├── models/                    # Database models (unused)
│   └── static/                    # Static files
├── venv/                          # Virtual environment
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Smithery MCP Integration

This server integrates with Smithery's Model Context Protocol ecosystem:

### BrowserCat MCP Server
- **URL**: `https://server.smithery.ai/@dmaznest/browsercat-mcp-server`
- **Purpose**: Browser automation for capturing Coinglass heatmaps
- **Tools Used**:
  - `browsercat_navigate`: Navigate to web pages
  - `browsercat_screenshot`: Capture screenshots
  - `browsercat_click`: Click page elements
  - `browsercat_evaluate`: Execute JavaScript

### Fallback Behavior

When BrowserCat MCP is unavailable (e.g., missing API key or service errors), the server provides simulated responses to ensure functionality continues. This makes the server robust and suitable for development/testing environments.

## Supported Cryptocurrencies

The server supports all major cryptocurrencies available on CoinGecko, including:
- BTC (Bitcoin)
- ETH (Ethereum)
- BNB (Binance Coin)
- ADA (Cardano)
- SOL (Solana)
- XRP (Ripple)
- DOT (Polkadot)
- DOGE (Dogecoin)
- AVAX (Avalanche)
- MATIC (Polygon)

## Error Handling

The server implements comprehensive error handling:

1. **Invalid Parameters**: Returns 400 Bad Request with descriptive error messages
2. **External Service Failures**: Graceful fallbacks with simulated responses
3. **Network Issues**: Timeout handling and retry logic
4. **API Rate Limits**: Proper HTTP status codes and error messages

## Development and Testing

### Running Tests

Test the endpoints using curl:

```bash
# Test health endpoint
curl "http://localhost:5001/api/health"

# Test crypto price
curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"

# Test heatmap capture
curl "http://localhost:5001/api/capture_heatmap?symbol=ETH&time_period=24%20hour"
```

### Development Mode

The server runs in debug mode by default, providing:
- Automatic reloading on code changes
- Detailed error messages
- Debug console access

## Deployment

For production deployment, consider:

1. **Use a production WSGI server** (e.g., Gunicorn, uWSGI)
2. **Set up environment variables** for API keys
3. **Configure reverse proxy** (e.g., Nginx)
4. **Enable HTTPS** for secure communication
5. **Set up monitoring** and logging

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the error logs in the console
2. Verify API keys are correctly set
3. Ensure all dependencies are installed
4. Check network connectivity to external services

## Changelog

### v1.0.0
- Initial release
- Cryptocurrency price fetching via CoinGecko API
- BrowserCat MCP integration for heatmap capture
- RESTful API endpoints
- Comprehensive error handling and fallbacks

