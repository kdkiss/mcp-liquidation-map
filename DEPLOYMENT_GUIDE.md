# Deployment Guide - Crypto Heatmap MCP Server

This guide provides instructions for deploying the Crypto Heatmap MCP Server in various environments.

## Quick Start

### Local Development

1. **Navigate to project directory**:
   ```bash
   cd crypto_heatmap_mcp
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Run the server**:
   ```bash
   python src/main.py
   ```

4. **Test the endpoints**:
   ```bash
   curl "http://localhost:5001/api/health"
   curl "http://localhost:5001/api/get_crypto_price?symbol=BTC"
   ```

### Production Deployment

#### Option 1: Using Gunicorn (Recommended)

1. **Install Gunicorn**:
   ```bash
   pip install gunicorn
   pip freeze > requirements.txt
   ```

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
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY src/ ./src/

   EXPOSE 5001

   CMD ["python", "src/main.py"]
   ```

2. **Build and run**:
   ```bash
   docker build -t crypto-heatmap-mcp .
   docker run -p 5001:5001 -e BROWSERCAT_API_KEY=your-key crypto-heatmap-mcp
   ```

## Environment Configuration

### Required Environment Variables

- `BROWSERCAT_API_KEY`: Your BrowserCat API key (optional, for real heatmap capture)
  - Get free key at: https://browsercat.xyz/mcp
  - Without this key, the server will provide simulated responses

### Optional Environment Variables

- `FLASK_ENV`: Set to `production` for production deployment
- `SECRET_KEY`: Flask secret key (change from default for production)

### Setting Environment Variables

**Linux/macOS**:
```bash
export BROWSERCAT_API_KEY="your-api-key-here"
export FLASK_ENV="production"
```

**Windows**:
```cmd
set BROWSERCAT_API_KEY=your-api-key-here
set FLASK_ENV=production
```

**Docker**:
```bash
docker run -e BROWSERCAT_API_KEY=your-key -e FLASK_ENV=production crypto-heatmap-mcp
```

## Reverse Proxy Setup (Nginx)

### Nginx Configuration

Create `/etc/nginx/sites-available/crypto-heatmap-mcp`:

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
sudo ln -s /etc/nginx/sites-available/crypto-heatmap-mcp /etc/nginx/sites-enabled/
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

Create `/etc/systemd/system/crypto-heatmap-mcp.service`:

```ini
[Unit]
Description=Crypto Heatmap MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto_heatmap_mcp
Environment=PATH=/home/ubuntu/crypto_heatmap_mcp/venv/bin
Environment=BROWSERCAT_API_KEY=your-api-key-here
ExecStart=/home/ubuntu/crypto_heatmap_mcp/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-heatmap-mcp
sudo systemctl start crypto-heatmap-mcp
sudo systemctl status crypto-heatmap-mcp
```

## Monitoring and Logging

### Application Logs

The Flask application logs to stdout. To capture logs:

```bash
# View real-time logs
sudo journalctl -u crypto-heatmap-mcp -f

# View recent logs
sudo journalctl -u crypto-heatmap-mcp -n 100
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

Configure log rotation in `/etc/logrotate.d/crypto-heatmap-mcp`:

```
/var/log/crypto-heatmap-mcp/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload crypto-heatmap-mcp
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
   source venv/bin/activate
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
upstream crypto_heatmap_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    location / {
        proxy_pass http://crypto_heatmap_backend;
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
tar -czf /backups/crypto-heatmap-mcp-$DATE.tar.gz \
    /home/ubuntu/crypto_heatmap_mcp \
    /etc/nginx/sites-available/crypto-heatmap-mcp \
    /etc/systemd/system/crypto-heatmap-mcp.service
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Update dependencies**:
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   pip freeze > requirements.txt
   ```

2. **Monitor logs**:
   ```bash
   sudo journalctl -u crypto-heatmap-mcp --since "1 hour ago"
   ```

3. **Check service status**:
   ```bash
   sudo systemctl status crypto-heatmap-mcp
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

