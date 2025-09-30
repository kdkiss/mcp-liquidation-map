# Deployment Guide - Crypto Heatmap MCP Server

This guide provides instructions for deploying the Crypto Heatmap MCP Server in various environments.

## Quick Start

### Local Development

1. **Navigate to project directory**:
   ```bash
   cd mcp-liquidation-map
   ```

2. **Create (optional) virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
   Use whatever virtual environment tooling fits your workflow if you already have one configured.

   Install the project in editable mode if you want its imports to be available globally while you develop locally:

   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Run the server**:
   ```bash
   python -m src.main
   ```

4. **(Optional) Generate initial database migration**:
   The default SQLite database is empty. Run these commands only if you intend to persist data (for example, when using the example `/api/users` routes):
   ```bash
   flask --app src.main db init        # run once if migrations/ does not exist yet
   flask --app src.main db migrate -m "initial schema"
   flask --app src.main db upgrade
   ```

5. **Test the endpoints**:
   ```bash
   curl "http://localhost:5001/api/health"
   curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"
   ```

### Production Deployment

#### Option 1: Using Gunicorn (Recommended)

1. **Install Gunicorn**:
   ```bash
   pip install gunicorn
   ```
   Add `gunicorn` to `requirements.txt` manually or use a dependency management tool such as `pip-tools` to regenerate locked
   requirements in a controlled manner.

2. **Create Gunicorn configuration** (`gunicorn.conf.py`):
   ```python
   bind = "0.0.0.0:5001"
   workers = 4
   worker_class = "sync"
   timeout = 30
   keepalive = 2
   max_requests = 1000
   max_requests_jitter = 100
   preload_app = True
   ```

3. **Run with Gunicorn**:
   ```bash
   gunicorn -c gunicorn.conf.py src.main:app
   ```

#### Option 2: Using Docker

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.12-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY src/ ./src/
   COPY marshmallow/ ./marshmallow/

   EXPOSE 5001

   CMD ["python", "-m", "src.main"]
   ```

   The extra `marshmallow/` copy step is required because this project ships a
   lightweight shim that patches a compatibility gap with older Marshmallow
   consumers. Without copying it into the container image, the runtime import
   hook is missing and requests that depend on the shim will fail.

2. **Build and run**:
   ```bash
   docker build -t mcp-liquidation-map .
   docker run -p 5001:5001 -e BROWSERCAT_API_KEY=your-key mcp-liquidation-map
   ```

## Environment Configuration

### Required Environment Variables

- `BROWSERCAT_API_KEY`: BrowserCat API key for real heatmap capture. Get a free key at https://browsercat.xyz/mcp. Without this
  key, BrowserCat requests fail and the server automatically falls back to simulated responses (unless explicitly disabled).

### Optional Environment Variables

- `ENABLE_SIMULATED_HEATMAP`: Force-enable (`true`) or disable (`false`) simulated fallbacks when BrowserCat fails. When unset,
  simulated payloads are provided by default.
- `BROWSERCAT_BASE_URL`: Override the BrowserCat MCP server URL. Default:
  `https://server.smithery.ai/@dmaznest/browsercat-mcp-server`.
- `DATABASE_URI`: Database connection string. Defaults to the bundled SQLite database at `sqlite:///src/database/app.db`.
- `FLASK_ENV`: Set to `production` for production deployment.
- `SECRET_KEY`: Flask secret key. When `DEBUG` is false this value is required
  and the app will abort on startup if it is missing. A `dev-secret-key` default
  is only applied for local debug sessions.


### Setting Environment Variables

**Linux/macOS**:
```bash
export SECRET_KEY="change-me"
export DATABASE_URI="postgresql+psycopg://user:pass@host:5432/dbname"
export BROWSERCAT_BASE_URL="https://server.smithery.ai/@dmaznest/browsercat-mcp-server"

export FLASK_ENV="production"
```

**Windows**:
```cmd
set BROWSERCAT_API_KEY=your-api-key-here
set SECRET_KEY=change-me
set DATABASE_URI=postgresql+psycopg://user:pass@host:5432/dbname
set BROWSERCAT_BASE_URL=https://server.smithery.ai/@dmaznest/browsercat-mcp-server

set FLASK_ENV=production
```

**Docker**:
```bash
docker run \
  -e BROWSERCAT_API_KEY=your-key \
  -e SECRET_KEY=change-me \
  -e DATABASE_URI=postgresql+psycopg://user:pass@host:5432/dbname \
  -e BROWSERCAT_BASE_URL=https://server.smithery.ai/@dmaznest/browsercat-mcp-server \
  -e FLASK_ENV=production \
  mcp-liquidation-map

```

## Reverse Proxy Setup (Nginx)

### Nginx Configuration

Create `/etc/nginx/sites-available/mcp-liquidation-map`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/mcp-liquidation-map /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/HTTPS Setup

### Using Certbot (Let's Encrypt)

1. **Install Certbot**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Obtain SSL certificate**:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

3. **Auto-renewal**:
   ```bash
   sudo crontab -e
   # Add: 0 12 * * * /usr/bin/certbot renew --quiet
   ```

## Systemd Service (Linux)

### Create Service File

Create `/etc/systemd/system/mcp-liquidation-map.service`:

```ini
[Unit]
Description=Crypto Heatmap MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mcp-liquidation-map
Environment="PATH=/home/ubuntu/mcp-liquidation-map/.venv/bin:/usr/bin"
Environment=BROWSERCAT_API_KEY=your-api-key-here
Environment=SECRET_KEY=change-me
Environment=DATABASE_URI=postgresql+psycopg://user:pass@host:5432/dbname
Environment=BROWSERCAT_BASE_URL=https://server.smithery.ai/@dmaznest/browsercat-mcp-server
ExecStart=/home/ubuntu/mcp-liquidation-map/.venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-liquidation-map
sudo systemctl start mcp-liquidation-map
sudo systemctl status mcp-liquidation-map
```

## Monitoring and Logging

### Application Logs

The Flask application logs to stdout. To capture logs:

```bash
# View real-time logs
sudo journalctl -u mcp-liquidation-map -f

# View recent logs
sudo journalctl -u mcp-liquidation-map -n 100
```

### Health Monitoring

Set up monitoring for the health endpoint:

```bash
# Simple health check script
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/health)
if [ $response -eq 200 ]; then
    echo "Service is healthy"
else
    echo "Service is unhealthy (HTTP $response)"
    # Add alerting logic here
fi
```

### Log Rotation

Configure log rotation in `/etc/logrotate.d/mcp-liquidation-map`:

```
/var/log/mcp-liquidation-map/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload mcp-liquidation-map
    endscript
}
```

## Performance Tuning

### Gunicorn Workers

Adjust worker count based on CPU cores:
```python
# In gunicorn.conf.py
workers = (2 * cpu_cores) + 1
```

### Connection Pooling

For high-traffic deployments, consider connection pooling for external API calls.

### Caching

Implement caching for cryptocurrency prices:
```python
from functools import lru_cache
import time

@lru_cache(maxsize=128)
def get_cached_price(symbol, timestamp):
    # Cache prices for 1 minute
    return get_crypto_price_internal(symbol)

def get_crypto_price(symbol):
    current_minute = int(time.time() // 60)
    return get_cached_price(symbol, current_minute)
```

## Security Considerations

### API Key Security

- Never commit API keys to version control
- Use environment variables or secure key management systems
- Rotate API keys regularly

### Network Security

- Use HTTPS in production
- Implement rate limiting
- Consider API authentication for public deployments

### Input Validation

The server includes input validation, but consider additional measures:
- Request size limits
- Input sanitization
- SQL injection protection (if using databases)

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   sudo lsof -i :5001
   # Kill the process or use a different port
   ```

2. **Permission denied**:
   ```bash
   # Ensure proper file permissions
   chmod +x src/main.py
   ```

3. **Module not found**:
   ```bash
   # Ensure virtual environment is activated
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **BrowserCat API errors**:
   - Verify API key is correct
   - Check API quota/limits
   - Review BrowserCat service status

### Debug Mode

Enable debug mode for troubleshooting:
```python
# In src/main.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

## Scaling

### Horizontal Scaling

Deploy multiple instances behind a load balancer:

```nginx
upstream mcp_liquidation_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    location / {
        proxy_pass http://mcp_liquidation_backend;
    }
}
```

### Database Considerations

For high-volume deployments, consider:
- Caching layer (Redis)
- Database for request logging
- Queue system for heatmap capture requests

## Backup and Recovery

### Configuration Backup

Backup important files:
- Application code
- Configuration files
- Environment variables
- SSL certificates

### Automated Backups

```bash
#!/bin/bash
# backup-script.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backups/mcp-liquidation-map-$DATE.tar.gz \
    /home/ubuntu/mcp-liquidation-map \
    /etc/nginx/sites-available/mcp-liquidation-map \
    /etc/systemd/system/mcp-liquidation-map.service
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Update dependencies**:
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   # Update requirements.txt manually or via pip-tools once changes are verified
   ```

2. **Monitor logs**:
   ```bash
   sudo journalctl -u mcp-liquidation-map --since "1 hour ago"
   ```

3. **Check service status**:
   ```bash
   sudo systemctl status mcp-liquidation-map
   ```

4. **Test endpoints**:
   ```bash
   curl "http://localhost:5001/api/health"
   ```

### Version Updates

1. Stop the service
2. Backup current version
3. Deploy new version
4. Test functionality
5. Start the service
6. Monitor for issues

This completes the deployment guide for the Crypto Heatmap MCP Server.

