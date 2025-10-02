# Crypto Heatmap MCP Server

A Smithery-compatible Model Context Protocol (MCP) server that delivers cryptocurrency market data and Coinglass liquidation heatmap captures over a simple REST API. The service mirrors the functionality of the original script while removing Telegram-specific logic and adding production-ready HTTP endpoints, health checks, and fallbacks.

## Table of Contents
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Server](#running-the-server)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Smithery / BrowserCat Integration](#smithery--browsercat-integration)
  - [Fallback Behaviour](#fallback-behaviour)
- [API Reference](#api-reference)
  - [Crypto Price](#1-get-cryptocurrency-price)
  - [Heatmap Capture](#2-capture-liquidation-heatmap)
  - [Health Check](#3-health-check)
  - [Optional User API](#optional-user-api)
- [Supported Assets](#supported-assets)
- [Development Workflow](#development-workflow)
  - [Testing](#testing)
  - [Linting](#linting)
  - [Database Migrations](#database-migrations)
- [Deployment Notes](#deployment-notes)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## Key Features

- **Real-time pricing** – Fetch up-to-date cryptocurrency prices from the CoinGecko API.
- **Automated heatmaps** – Capture Coinglass liquidation heatmaps using BrowserCat MCP automation tools.
- **Resilient fallbacks** – Provide simulated heatmap payloads when BrowserCat is unavailable.
- **HTTP-first design** – Expose endpoints that can be consumed by Smithery clients, scripts, or other services.
- **Health monitoring** – Report service health with a lightweight `/api/health` endpoint.

## Architecture Overview

The application is a Flask service packaged as an MCP server. It orchestrates three key pieces:

1. **CoinGecko price fetcher** – Simple HTTP calls to retrieve ticker data.
2. **BrowserCat MCP client** – Automates browser interactions for heatmap screenshots.
3. **Optional SQL-backed user API** – A CRUD example demonstrating database integration with SQLAlchemy and Marshmallow.

All HTTP routes live under `/api/*` and are version-agnostic, keeping integration straightforward.

## Quick Start

### Prerequisites

- Python **3.12 or later**
- Optional: virtual environment tooling (`venv`, `virtualenv`, or `conda`)
- (For heatmaps) BrowserCat MCP credentials
- (For optional user API) SQLite or another SQLAlchemy-supported database

### Installation

```bash
# Clone the repository and enter the project directory
cd mcp-liquidation-map

# (Recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install runtime and development dependencies
pip install -r requirements.txt
# or, for development extras
pip install -r requirements-dev.txt
```

### Running the Server

```bash
# Export any configuration you need (see the table below)
export DEBUG=1
export SECRET_KEY="dev-secret-key"

# Start the Flask app
python -m mcp_liquidation_map.main
```

The service listens on `http://localhost:5001` by default. When running through Smithery (`smithery dev`), configuration is handled through `smithery.yaml`.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SECRET_KEY` | Yes (unless `DEBUG=1`) | – | Flask secret key; must be set in production. |
| `DEBUG` | No | `0` | Enables Flask debug mode and auto reload. |
| `APP_LOG_LEVEL` | No | `INFO` | Root logging level (`DEBUG`, `INFO`, etc.). |
| `DATABASE_URI` | No | SQLite at `src/mcp_liquidation_map/database/app.db` | SQLAlchemy connection string for the optional user API. |
| `ENABLE_USER_API` | No | `0` | Enable CRUD endpoints under `/api/users`. |
| `USER_API_TOKEN` | Required when user API enabled | – | Bearer token required for all user API requests. |
| `BROWSERCAT_API_KEY` | Recommended | – | Authentication for BrowserCat MCP. Without it, simulated heatmaps are returned. |
| `BROWSERCAT_BASE_URL` | No | `https://server.smithery.ai/@dmaznest/browsercat-mcp-server` | Override BrowserCat endpoint. |
| `BROWSERCAT_TIMEOUT` | No | `30` | Request timeout (seconds) for BrowserCat operations. |
| `ENABLE_SIMULATED_HEATMAP` | No | `1` | `1`/`true` forces simulated heatmaps; `0` disables fallback. |

### Smithery / BrowserCat Integration

The service uses Smithery MCP to communicate with BrowserCat. The following tools are invoked:

- `browsercat_navigate` – Navigate to the Coinglass page.
- `browsercat_screenshot` – Capture the heatmap image.
- `browsercat_click` – Interact with page filters (e.g., symbol/time period selectors).
- `browsercat_evaluate` – Execute supporting JavaScript snippets.

Override the BrowserCat server URL or timeouts using the environment variables above.

### Fallback Behaviour

If BrowserCat is unreachable (missing credentials, network outage, or 4xx/5xx responses), the server emits a simulated payload containing placeholder image information. Control this behaviour by:

- Passing `allow_simulated=false` in the heatmap request, or
- Exporting `ENABLE_SIMULATED_HEATMAP=false` to disable the fallback globally, or
- Setting `allow_simulated=true`/`ENABLE_SIMULATED_HEATMAP=true` to force the simulated payload (useful for development).

## API Reference

### 1. Get Cryptocurrency Price

- **Endpoint**: `GET /api/get_crypto_price`
- **Query Parameters**:
  - `symbol` (string, required) – Cryptocurrency symbol (e.g., `BTC`, `ETH`). Case-insensitive.

**Example**

```bash
curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"
```

```json
{
  "price": "$113,975.00",
  "symbol": "BTC"
}
```

### 2. Capture Liquidation Heatmap

- **Endpoint**: `POST /api/capture_heatmap`
- **Accepted Methods**: `GET` or `POST` (JSON body or query string)
- **Parameters**:
  - `symbol` (string, required) – Cryptocurrency symbol.
  - `time_period` (string, optional) – One of `12 hour`, `24 hour`, `1 month`, or `3 month`. Defaults to `24 hour`.
  - `allow_simulated` (boolean, optional) – Overrides the fallback behaviour described above.

**Example request**

```bash
curl "http://localhost:5001/api/capture_heatmap?symbol=BTC&time_period=24%20hour"
```

**Successful response**

```json
{
  "image_path": "/tmp/heatmap.png",
  "symbol": "BTC",
  "time_period": "24 hour",
  "browsercat_result": {
    "screenshot_path": "/tmp/heatmap.png"
  }
}
```

**Fallback response (HTTP 502)**

```json
{
  "error": "Failed to capture heatmap via BrowserCat.",
  "browsercat_error": "Request failed with status 401",
  "symbol": "BTC",
  "time_period": "24 hour",
  "fallback_provided": true,
  "fallback": {
    "image_path": "/tmp/btc_liquidation_heatmap_20250802_013339_24_hour.png",
    "symbol": "BTC",
    "time_period": "24 hour",
    "note": "Simulated heatmap placeholder generated without BrowserCat.",
    "simulated": true
  }
}
```

### 3. Health Check

- **Endpoint**: `GET /api/health`

```json
{
  "status": "healthy",
  "timestamp": "2025-08-02T01:34:50.359764"
}
```

### Optional User API

When `ENABLE_USER_API=1`, CRUD endpoints for managing users become available under `/api/users`. Every request must include a bearer token that matches `USER_API_TOKEN`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/users` | List all users. |
| `POST` | `/api/users` | Create a user (`username`, `email`). |
| `GET` | `/api/users/<id>` | Retrieve a specific user. |
| `PUT` | `/api/users/<id>` | Update a user (partial updates allowed). |
| `DELETE` | `/api/users/<id>` | Remove a user. |

When using a database other than SQLite, ensure the schema exists by running migrations before enabling the API (see below).

## Supported Assets

The service proxies CoinGecko and therefore supports any symbol CoinGecko recognises (BTC, ETH, BNB, ADA, SOL, XRP, DOT, DOGE, AVAX, MATIC, and many more). Unknown symbols return a descriptive 400 error.

## Development Workflow

### Testing

Use pytest to run the automated suite:

```bash
pytest
```

API smoke tests can be performed with curl:

```bash
curl "http://localhost:5001/api/health"
curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"
curl "http://localhost:5001/api/capture_heatmap?symbol=ETH&time_period=24%20hour"
```

### Linting

We use [Ruff](https://docs.astral.sh/ruff/) to keep imports tidy and enforce style rules.

```bash
ruff check .
ruff check --fix .  # Auto-fix simple issues
```

### Database Migrations

Flask-Migrate is configured for the optional user API. Typical workflow:

```bash
flask --app mcp_liquidation_map.main db init      # First run only
flask --app mcp_liquidation_map.main db migrate
flask --app mcp_liquidation_map.main db upgrade
```

SQLite users can rely on automatic schema creation when the API starts, but other databases require migrations to be applied manually.

## Deployment Notes

For production deployments:

1. Run behind a production WSGI server (Gunicorn, uWSGI, etc.).
2. Provide all sensitive configuration via environment variables or a secrets manager.
3. Place a reverse proxy (e.g., Nginx) in front of the service and enable HTTPS.
4. Configure logging/monitoring (CloudWatch, Prometheus, etc.) and alerting on failures.
5. Copy the `marshmallow/` compatibility shim when containerising so the app can import the bundled schema patches (see `DEPLOYMENT_GUIDE.md`).

## Troubleshooting

1. **Heatmap calls fail immediately** – Verify `BROWSERCAT_API_KEY` and network access to the BrowserCat MCP server.
2. **Fallbacks not provided** – Ensure `allow_simulated=true` or `ENABLE_SIMULATED_HEATMAP=1` is set while testing without BrowserCat.
3. **User API returns 503** – Check that `USER_API_TOKEN` is set and that migrations have been run (or SQLite schema created).
4. **App refuses to start in production** – Set `SECRET_KEY` and confirm `DEBUG=0`.
5. **Database errors on SQLite** – The project stores SQLite files under `src/mcp_liquidation_map/database/`; ensure the process has write permissions.

## Contributing

1. Fork the repository and create a feature branch.
2. Install development dependencies and activate a virtual environment.
3. Implement your change with tests and lint fixes.
4. Open a pull request describing the change and how to validate it.

## Changelog

### v0.1.0
- Initial release with CoinGecko pricing, BrowserCat heatmaps, RESTful API endpoints, and comprehensive fallback handling.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
