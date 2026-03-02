# Deployment Guide

Complete guide for deploying the VPN Sales Bot to production.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platforms](#cloud-platforms)
4. [Production Configuration](#production-configuration)
5. [Monitoring & Logging](#monitoring--logging)
6. [Scaling](#scaling)

## Local Development

### Prerequisites
- Python 3.11+
- Redis
- Git

### Setup

```bash
# Clone repository
git clone <repo_url>
cd bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start Redis (separate terminal)
redis-server

# Run bot
python bot/main.py
```

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t vpn-sales-bot .

# Run container
docker run -d \
  --name vpn-bot \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e ADMIN_IDS=123456 \
  -e API_BASE_URL=http://backend:8000/api \
  -e REDIS_URL=redis://redis:6379 \
  --link redis:redis \
  vpn-sales-bot
```

### Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Docker Compose Configuration

Update `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass password123
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  bot:
    build: .
    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      ADMIN_IDS: ${ADMIN_IDS}
      API_BASE_URL: ${API_BASE_URL}
      API_KEY: ${API_KEY}
      REDIS_URL: redis://:password123@redis:6379
      DEBUG: "False"
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  redis_data:
```

## Cloud Platforms

### Heroku Deployment

```bash
# Login to Heroku
heroku login

# Create app
heroku create vpn-sales-bot

# Add Redis addon
heroku addons:create heroku-redis:premium-0

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set ADMIN_IDS=123456
heroku config:set API_BASE_URL=your_api_url
heroku config:set API_KEY=your_api_key

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Procfile:**
```
worker: python bot/main.py
```

### AWS Deployment (ECS)

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag vpn-sales-bot:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/vpn-sales-bot:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/vpn-sales-bot:latest

# Create ECS task definition
# Use the image URI and set environment variables
```

### DigitalOcean App Platform

```bash
# Create app.yaml
app:
  name: vpn-sales-bot
  services:
    - name: bot
      github:
        repo: your_repo
        branch: main
      build_command: pip install -r requirements.txt
      run_command: python bot/main.py
      envs:
        - key: TELEGRAM_BOT_TOKEN
          value: ${TELEGRAM_BOT_TOKEN}
        - key: API_BASE_URL
          value: ${API_BASE_URL}

databases:
  - name: redis
    engine: REDIS
    version: "7"
```

### Google Cloud Run

```bash
# Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/vpn-sales-bot

# Deploy
gcloud run deploy vpn-sales-bot \
  --image gcr.io/PROJECT_ID/vpn-sales-bot \
  --platform managed \
  --region us-central1 \
  --set-env-vars TELEGRAM_BOT_TOKEN=your_token \
  --set-env-vars API_BASE_URL=your_api_url \
  --memory 512Mi \
  --timeout 3600
```

## Production Configuration

### Environment Variables

Create `.env` with production values:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
ADMIN_IDS=123456789,987654321
TELEGRAM_CHANNEL_URL=https://t.me/your_channel
TELEGRAM_SUPPORT_URL=https://t.me/your_support

# Backend API
API_BASE_URL=https://api.yourdomain.com/api
API_TIMEOUT=30
API_KEY=your_secure_api_key_here

# Payment
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_API_KEY=your_api_key

# Redis (with authentication in production)
REDIS_URL=redis://:password@redis.yourdomain.com:6379/0

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db.yourdomain.com:5432/bot_db

# Security
DEBUG=False
```

### Security Best Practices

1. **Never commit `.env` to git**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Use strong Redis password**
   ```bash
   redis-cli CONFIG SET requirepass "strong_password_here"
   ```

3. **Restrict API key access**
   - Use separate API keys per service
   - Implement rate limiting on backend
   - Use IP whitelisting if possible

4. **Enable HTTPS**
   - Use SSL certificates (Let's Encrypt)
   - Configure webhooks with HTTPS only

5. **Monitor sensitive operations**
   - Log all admin actions
   - Alert on unusual activity

### Health Checks

Add health check endpoint to your deployment:

```python
# In bot/main.py
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        async with APIClient(config.api.base_url) as client:
            # Test API connectivity
            await client.get("/health")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Monitoring & Logging

### Structured Logging

```python
# In bot/config.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'bot.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Sentry Integration

```bash
pip install sentry-sdk
```

```python
# In bot/main.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production")
)
```

### Prometheus Metrics

```python
# In bot/main.py
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
user_messages = Counter('user_messages_total', 'Total user messages')
handler_duration = Histogram('handler_duration_seconds', 'Handler execution time')
api_errors = Counter('api_errors_total', 'Total API errors')

# Start metrics server
start_http_server(8000)
```

### Log Aggregation

**ELK Stack:**
```bash
# Configure Filebeat to ship logs
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/bot.log
  json.message_key: message
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

**CloudWatch (AWS):**
```bash
pip install watchtower

import watchtower
logging.getLogger().addHandler(
    watchtower.CloudWatchLogHandler()
)
```

## Scaling

### Horizontal Scaling

For multiple bot instances:

1. **Use shared Redis** for session storage (already configured)
2. **Load balance** Telegram webhook requests
3. **Separate notification worker**

```yaml
# docker-compose.yml with multiple instances
services:
  bot-1:
    build: .
    environment:
      # ... same env vars
  
  bot-2:
    build: .
    environment:
      # ... same env vars
  
  bot-3:
    build: .
    environment:
      # ... same env vars
```

### Database Optimization

```sql
-- Useful indexes for production
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_expire_date ON subscriptions(expire_date);
CREATE INDEX idx_devices_user_id ON devices(user_id);
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
```

### Redis Optimization

```bash
# Configure Redis for production
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
```

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# backup.sh

# Backup Redis
redis-cli --rdb /backups/redis-$(date +%Y%m%d_%H%M%S).rdb

# Backup database
pg_dump $DATABASE_URL > /backups/db-$(date +%Y%m%d_%H%M%S).sql.gz

# Upload to S3
aws s3 sync /backups s3://your-bucket/backups/
```

## Troubleshooting

### Common Production Issues

**Bot not responding**
- Check Redis connection
- Verify API endpoint health
- Review logs for errors
- Check rate limiting

**High memory usage**
- Monitor event loop
- Check for memory leaks
- Reduce FSM timeout

**Slow responses**
- Monitor API response times
- Check database query performance
- Review Redis latency

**Payment failures**
- Verify YooKassa credentials
- Check webhook configuration
- Review payment logs

## Performance Targets

- **Message handling**: < 100ms
- **API response**: < 1s (including backend)
- **Memory usage**: < 512MB per instance
- **Redis latency**: < 10ms
- **Uptime**: > 99.5%

## Checklist

Production deployment checklist:

- [ ] Set `DEBUG=False`
- [ ] Configure logging (Sentry/ELK)
- [ ] Setup monitoring (Prometheus/Datadog)
- [ ] Enable backups
- [ ] Configure health checks
- [ ] Setup alerting
- [ ] Test failover
- [ ] Document procedures
- [ ] Setup CI/CD pipeline
- [ ] Load test with realistic data
- [ ] Security audit
- [ ] Performance baseline
- [ ] Disaster recovery plan

## Support

For deployment issues:
1. Check logs first
2. Review configuration
3. Test each component
4. Contact cloud provider support if needed
