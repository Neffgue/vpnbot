# Deployment Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Docker & Docker Compose (optional)
- Git

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repo_url>
cd backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - BOT_TOKEN
# - YOOKASSA credentials
```

### 5. Initialize Database
```bash
# Create tables
alembic upgrade head

# Or let the app create tables on startup (via lifespan)
```

### 6. Run Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs for API documentation.

## Docker Deployment

### Using Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Services running:
- API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Manual Docker Build

```bash
# Build image
docker build -t vpn-api .

# Run container with PostgreSQL
docker run -d \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/vpn_db \
  -e SECRET_KEY=your-secret-key \
  -p 8000:8000 \
  vpn-api
```

## Production Deployment

### 1. Security Configuration

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate Fernet key for encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Environment Variables

Create `.env` with production values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://prod_user:STRONG_PASSWORD@prod-db.example.com:5432/vpn_prod

# Security
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
ENCRYPTION_KEY=YOUR_FERNET_KEY
DEBUG=False

# API
ALLOWED_ORIGINS=["https://yourdomain.com"]

# Services
BOT_TOKEN=your-production-bot-token
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_API_KEY=your-api-key
```

### 3. Database Setup

```bash
# On your PostgreSQL server
createdb vpn_prod
createuser vpn_prod_user
ALTER USER vpn_prod_user PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE vpn_prod TO vpn_prod_user;

# Run migrations
alembic upgrade head
```

### 4. Application Server

Use Gunicorn + Uvicorn:

```bash
pip install gunicorn

gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  main:app
```

Or with systemd service file:

Create `/etc/systemd/system/vpn-api.service`:

```ini
[Unit]
Description=VPN Sales API
After=network.target postgresql.service

[Service]
Type=notify
User=apiuser
WorkingDirectory=/opt/vpn-api
Environment="PATH=/opt/vpn-api/venv/bin"
ExecStart=/opt/vpn-api/venv/bin/gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  main:app

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vpn-api
sudo systemctl start vpn-api
```

### 5. Reverse Proxy (Nginx)

Create `/etc/nginx/sites-available/vpn-api`:

```nginx
upstream vpn_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    client_max_body_size 20M;

    location / {
        proxy_pass http://vpn_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/vpn-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL Certificate (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d api.yourdomain.com
```

Update nginx to use SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 7. Database Backups

Create backup script `/opt/vpn-api/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/vpn-db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vpn_db_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -h localhost -U vpn_prod_user vpn_prod | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "vpn_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:
```bash
0 2 * * * /opt/vpn-api/backup.sh
```

### 8. Monitoring & Logging

Setup structured logging:

```python
# In main.py or separate logging config
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/vpn-api/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "formatter": "standard",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
})
```

### 9. Health Checks

Setup uptime monitoring:

```bash
# Add to crontab
*/5 * * * * curl -f http://127.0.0.1:8000/health || systemctl restart vpn-api
```

## Scaling

For high traffic:

1. **Multiple API instances** behind load balancer
2. **Redis caching** for frequently accessed data
3. **Database read replicas** for heavy queries
4. **CDN** for static assets
5. **Message queue** (Celery) for async tasks

## Troubleshooting

### Database connection errors
```bash
# Test connection
psql -h localhost -U vpn_prod_user -d vpn_prod

# Check migrations
alembic current
alembic history
```

### Port already in use
```bash
lsof -i :8000
kill -9 <PID>
```

### Permission errors
```bash
sudo chown -R apiuser:apiuser /opt/vpn-api
```

### View logs
```bash
sudo journalctl -u vpn-api -f
tail -f /var/log/vpn-api/app.log
```

## Maintenance

### Database maintenance
```bash
# Vacuum and analyze
psql -U vpn_prod_user -d vpn_prod -c "VACUUM ANALYZE;"

# Check table sizes
psql -U vpn_prod_user -d vpn_prod -c "SELECT schemaname, tablename, 
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
  FROM pg_tables ORDER BY 
  pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Update dependencies
```bash
pip list --outdated
pip install --upgrade package_name
```

### Rotate logs
```bash
# Add to /etc/logrotate.d/vpn-api
/var/log/vpn-api/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 apiuser apiuser
}
```

## Monitoring Checklist

- [ ] Application health endpoint responding
- [ ] Database connectivity
- [ ] Error rates < 1%
- [ ] Response times < 500ms
- [ ] Disk space available
- [ ] Backup completion
- [ ] SSL certificate validity
- [ ] Security logs reviewed
