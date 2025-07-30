# MCP Liquidation Map Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-available-2496ED.svg?logo=docker)](https://www.docker.com/)

A high-performance MCP (Model Control Protocol) server for retrieving and serving cryptocurrency liquidation heatmaps. This service captures real-time liquidation data from Coinglass and provides it through a standardized JSON-RPC 2.0 interface.

## 🌟 Features

- **Real-time Liquidation Data**: Capture and serve liquidation heatmaps for various cryptocurrencies
- **Multiple Timeframes**: Support for 12h, 24h, 1 month, and 3 month timeframes
- **MCP Compliance**: Implements the full JSON-RPC 2.0 specification for MCP compatibility
- **Docker Support**: Easy deployment using Docker containers
- **High Performance**: Asynchronous processing for handling multiple requests efficiently

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker (optional)
- Chrome/Chromium and ChromeDriver (for Selenium)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-liquidation-map.git
   cd mcp-liquidation-map
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Using Docker

```bash
# Build the Docker image
docker build -t mcp-liquidation-map .

# Run the container
docker run -p 8000:8000 mcp-liquidation-map
```

## 📡 API Endpoints

### JSON-RPC 2.0 Endpoint

- `POST /` - Main JSON-RPC 2.0 endpoint

### Standard Endpoints

- `GET /health` - Health check endpoint
- `POST /get-liquidation-map` - Legacy endpoint (for backward compatibility)

## 🔧 MCP Tools

The server implements the following MCP tools:

### `get_liquidation_map`

Get a liquidation heatmap for a specific cryptocurrency.

**Parameters:**
- `symbol` (string): Cryptocurrency symbol (e.g., "BTC", "ETH")
- `timeframe` (string): Time period for the heatmap ("12 hour", "24 hour", "1 month", "3 month")

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_liquidation_map",
    "arguments": {
      "symbol": "BTC",
      "timeframe": "24 hour"
    }
  },
  "id": 1
}
```

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

Your Name - [@your_twitter](https://twitter.com/your_handle) - email@example.com

Project Link: [https://github.com/yourusername/mcp-liquidation-map](https://github.com/yourusername/mcp-liquidation-map)

## 🙏 Acknowledgments

- [Coinglass](https://www.coinglass.com) for the liquidation data
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Selenium](https://www.selenium.dev/) for browser automation
