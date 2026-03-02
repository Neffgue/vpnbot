# VPN Sales System - Infrastructure Documentation

Complete guide to the production-ready infrastructure setup.

## Overview

The VPN Sales System uses Docker Compose for containerized deployment with the following stack:

- **Frontend**: React admin panel with nginx
- **Backend**: Python/FastAPI with Uvicorn
- **Bot**: Telegram bot integration
- **Task Queue**: Celery with Redis and Beat scheduler
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Reverse Proxy**: Nginx with SSL termination
- **SSL/TLS**: Let's Encrypt via Certbot

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Internet Traffic                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼──────┐
                    │  Certbot   │
                    │ (SSL Certs)│
                    └────┬──────┘
                         │
                    ┌────▼──────┐
                    │   Nginx    │
                    │(Port 80/443)
                    └────┬──────┘
                    ┌────┴────────────────────┐
                    │                         │
            ┌───────▼────────┐      ┌────────▼────────┐
            │     Backend    │      │  Admin Panel    │
            │   (Port 8000)  │      │   (Port 3000)   │
            └───────┬────────┘      └────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼───┐   ┌───▼────┐ ┌───▼──┐
    │  Bot  │   │ Worker │ │ Beat │
    │       │   │ (Celery)   │
    └───────┘   └────────┘ └──────┘
        │           │
    ┌───┴───────────┴────────┐
    │                        │
 ┌──▼─────┐          ┌───────▼──┐
 │PostgreSQL          │  Redis   │
 │  (Port 5432)      │(Port 6379)
 └────────┘          └──────────┘
```

## File Structure

```
vpn-system/
├── docker-compose.yml              # Development environment
├── docker-compose.prod.yml         # Production environment
├── docker-compose.override.yml     # Development overrides
├── docker-compose.test.yml         # Test environment
├── docker-compose.scale.yml        # Horizontal scaling config
├── .env.example                    # Environment template
├── .dockerignore                   # Docker build exclusions
├── .gitignore                      # Git exclusions
├── Makefile                        # Development commands
├── INFRASTRUCTURE.md               # This file
├── DEPLOYMENT_CHECKLIST.md         # Deployment guide
├── README.md                       # Main documentation
│
├── nginx/
│   ├── nginx.conf                  # Main configuration
│   └── conf.d/
│       ├── app.conf                # Application routing
│       └── ssl.conf                # SSL configuration
│
├── scripts/
│   ├── deploy.sh                   # Deployment script
│   ├── setup_server.sh             # Initial setup
│   ├── add_server.sh               # Add VPN server
│   ├── backup.sh                   # Database backup
│   ├── restore_backup.sh           # Database restore
│   └── health_check.sh             # Health monitoring
│
├── backend/
│   ├── Dockerfile                  # Python image
│   ├── requirements.txt            # Dependencies
│   ├── main.py                     # FastAPI app
│   ├── config.py                   # Configuration
│   ├── database.py                 # Database setup
│   ├── alembic.ini                 # Migration config
│   ├── entrypoint.sh               # Container startup
│   ├── api/                        # API endpoints
│   ├── models/                     # Database models
│   ├── schemas/                    # Pydantic schemas
│   ├── services/                   # Business logic
│   └── repositories/               # Data access
│
├── bot/
│   ├── Dockerfile                  # Python image
│   ├── requirements.txt            # Dependencies
│   ├── main.py                     # Bot entry point
│   ├── config.py                   # Bot configuration
│   ├── keyboards/                  # Message keyboards
│   ├── handlers/                   # Message handlers
│   ├── middlewares/                # Request middlewares
│   └── utils/                      # Helper functions
│
├── worker/
│   ├── Dockerfile                  # Python image
│   ├── requirements.txt            # Dependencies
│   ├── celery_app.py               # Celery config
│   ├── beat_schedule.py            # Scheduler setup
│   └── tasks/                      # Background tasks
│
├── admin-panel/
│   ├── Dockerfile                  # Multi-stage Node/Nginx
│   ├── package.json                # Dependencies
│   ├── nginx.conf                  # Nginx config
│   ├── vite.config.js              # Build config
│   ├── tailwind.config.js          # Tailwind config
│   ├── public/                     # Static assets
│   └── src/                        # React components
│
└── .github/
    └── workflows/
        └── deploy.yml              # CI/CD pipeline
```

## Environment Configuration

### Development (docker-compose.yml)

```yaml
Services:
  - PostgreSQL 16-alpine (port 5432)
  - Redis 7-alpine (port 6379)
  - Backend (port 8000)
  - Bot
  - Worker + Beat
  - Admin Panel (port 3000)
  - Nginx (port 80)

Features:
  - Hot reload enabled
  - Debug mode on
  - No resource limits
  - Volumes for code
```

### Production (docker-compose.prod.yml)

```yaml
Services:
  - PostgreSQL 16-alpine (no port)
  - Redis 7-alpine with password (no port)
  - Backend (no port, only via nginx)
  - Bot (no port)
  - Worker + Beat (no port)
  - Admin Panel (no port, only via nginx)
  - Nginx (ports 80, 443)
  - Certbot (SSL automation)

Features:
  - restart: always
  - Resource limits & reservations
  - No direct port exposure
  - SSL/TLS termination
  - Health checks
```

### Scaling (docker-compose.scale.yml)

```yaml
Service Replicas:
  - Backend: 3 instances
  - Worker: 3 instances
  - Admin Panel: 2 instances
  - Nginx: 2 instances (load balanced)
  - Beat: 1 instance (singleton)
  - Bot: 1 instance
  - PostgreSQL: 1 instance
  - Redis: 1 instance

Configuration:
  - Deployment strategy
  - Update policies
  - Restart policies
  - Resource allocations
```

## Database Schema

### PostgreSQL (Version 16)

**Volumes:**
- `postgres_data:/var/lib/postgresql/data` - Persistent storage

**Tables** (managed by Alembic):
- users
- subscriptions
- payments
- servers
- referrals
- vpn_configs
- (application-specific tables)

**Backup:**
- Automated via `scripts/backup.sh`
- Location: `./backups/vpn_system_TIMESTAMP.sql.gz`
- Retention: Configurable (default 30 days)

### Redis (Version 7)

**Volumes:**
- `redis_data:/data` - Persistent storage

**Data:**
- Session store
- Task queue (Celery)
- Cache layer
- Rate limiting counters

**Backup:**
- Automated via `scripts/backup.sh`
- Location: `./backups/redis_TIMESTAMP.rdb`

## Network Architecture

### Docker Network

```yaml
Network: vpn_network
Type: bridge
Scope: local

Services on network:
  - All containers can communicate by service name
  - Example: backend:8000 resolves to backend container
```

### Nginx Routing

```
HTTP/HTTPS Traffic
    ↓
Nginx (80, 443)
    ├─→ /api/*          → Backend (8000)
    ├─→ /admin/*        → Admin Panel (3000)
    └─→ /               → Backend (webhook)
```

### Firewall Rules (Production)

```
Allowed Inbound:
  - 22/tcp    (SSH)
  - 80/tcp    (HTTP)
  - 443/tcp   (HTTPS)

Blocked:
  - 5432/tcp  (PostgreSQL)
  - 6379/tcp  (Redis)
  - 8000/tcp  (Backend)
  - 3000/tcp  (Admin Panel)
```

## Deployment Models

### Development

```bash
docker-compose up -d
# Uses docker-compose.yml + docker-compose.override.yml
# Ports exposed for debugging
# Hot reload enabled
# Database migrations auto-run
```

### Production (Single Server)

```bash
docker-compose -f docker-compose.prod.yml up -d
# Single instance of each service
# No direct port exposure
# SSL certificates via Certbot
# Systemd service for management
```

### Production (Scaled)

```bash
docker-compose -f docker-compose.prod.yml \
               -f docker-compose.scale.yml up -d
# Multiple replicas for backend, worker, nginx
# Load balancing
# High availability
# Auto-restart on failure
```

### Testing

```bash
docker-compose -f docker-compose.test.yml up
# Isolated database and redis
# Runs test suite
# No data persistence
```

## Resource Limits

### Development
No limits (uses host resources)

### Production

```yaml
PostgreSQL:
  CPU: 2 cores max, 1 core reserved
  Memory: 2GB max, 1GB reserved

Redis:
  CPU: 1 core max, 0.5 cores reserved
  Memory: 1GB max, 512MB reserved

Backend (each):
  CPU: 2 cores max, 1 core reserved
  Memory: 2GB max, 1GB reserved

Worker (each):
  CPU: 2 cores max, 1 core reserved
  Memory: 2GB max, 1GB reserved

Beat:
  CPU: 1 core max, 0.5 cores reserved
  Memory: 512MB max, 256MB reserved

Bot:
  CPU: 1 core max, 0.5 cores reserved
  Memory: 1GB max, 512MB reserved

Admin Panel (each):
  CPU: 1 core max, 0.5 cores reserved
  Memory: 512MB max, 256MB reserved

Nginx (each):
  CPU: 1 core max, 0.5 cores reserved
  Memory: 512MB max, 256MB reserved
```

## SSL/TLS Configuration

### Certificate Generation

1. **Initial Setup**
   ```bash
   certbot certonly --standalone \
     -d yourdomain.com \
     --email admin@yourdomain.com
   ```

2. **Automatic Renewal**
   - Certbot service in compose file
   - Renews 30 days before expiry
   - Certificates stored in `./nginx/certs/`

3. **Nginx Configuration**
   - Uncomment SSL section in `nginx/conf.d/ssl.conf`
   - Add domain to `app.conf`
   - Reload Nginx

### Security Headers

Added by Nginx:
- HSTS (HTTP Strict-Transport-Security)
- X-Frame-Options (clickjacking protection)
- X-Content-Type-Options (MIME sniffing)
- CSP (Content-Security-Policy)
- Referrer-Policy
- Permissions-Policy

## Rate Limiting

Configured in Nginx:

```nginx
/api/*: 10 req/s (burst 20)
Others: 100 req/s (burst 50)
```

Zone limits stored in Redis for distributed environments.

## Monitoring & Logging

### Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f <service>

# With timestamps
docker-compose logs -f --timestamps

# Last N lines
docker-compose logs --tail 100
```

### Health Checks

Services with health checks:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Backend: HTTP GET `/health`
- Admin Panel: HTTP GET `/`

### Performance Monitoring

```bash
# Docker stats
docker stats --no-stream

# System resources
free -h
df -h
top
```

### Application Metrics

Available in backend logs:
- Request latency
- Database query time
- Cache hit rate
- Error rates

## Backup & Recovery

### Automated Backups

```bash
bash scripts/backup.sh
```

Creates:
- `vpn_system_TIMESTAMP.sql.gz` - PostgreSQL dump
- `redis_TIMESTAMP.rdb` - Redis snapshot
- `vpn_system_TIMESTAMP.manifest` - Backup metadata

### Manual Restoration

```bash
bash scripts/restore_backup.sh ./backups/vpn_system_TIMESTAMP.sql.gz
```

Process:
1. Creates backup before restore
2. Drops existing database
3. Restores from backup
4. Runs migrations
5. Verifies data

### S3 Backup Upload

Configure in `.env`:
```bash
S3_BUCKET=my-backups
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Backups auto-upload when `aws-cli` installed.

## Disaster Recovery

### Recovery Time Objectives (RTO)

- **Service failure**: 2-5 minutes (auto-restart)
- **Database corruption**: 15 minutes (restore backup)
- **Complete server loss**: 1 hour (redeploy + restore)

### Recovery Point Objectives (RPO)

- **Current**: Last backup (hourly if daily backup)
- **Maximum data loss**: 24 hours

### Failover Procedure

1. Identify affected service
2. Check logs: `docker-compose logs -f <service>`
3. Restart service: `docker-compose restart <service>`
4. If persistent, restore from backup
5. Verify functionality
6. Alert team

## Performance Tuning

### PostgreSQL

```bash
# Optimize database
docker-compose exec postgres vacuumdb -U postgres vpn_system

# Analyze tables
docker-compose exec postgres analyzedb -U postgres vpn_system
```

### Redis

```bash
# Check memory
docker-compose exec redis redis-cli info memory

# Clear cache if needed
docker-compose exec redis redis-cli FLUSHDB
```

### Nginx

- Worker processes: auto (number of CPU cores)
- Worker connections: 1024
- Gzip compression enabled
- Caching enabled for static assets

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs <service>

# Verify dependencies
docker-compose ps

# Check resource limits
docker stats
```

### Database connection error

```bash
# Test connection
docker-compose exec backend psql $DATABASE_URL

# Check environment variables
grep DATABASE_URL .env

# Verify PostgreSQL is running
docker-compose exec postgres pg_isready
```

### Out of memory

```bash
# Check memory usage
free -h

# View container memory
docker stats

# Increase swap
sudo fallocate -l 4G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Disk full

```bash
# Check disk usage
df -h

# Clean Docker images
docker image prune -a

# Clean Docker volumes
docker volume prune

# Remove old backups
rm ./backups/vpn_system_*.sql.gz (keep recent ones)
```

## Maintenance

### Daily
- Monitor error logs
- Check service health
- Monitor disk space

### Weekly
- Review backup status
- Check certificate renewal
- Analyze performance trends

### Monthly
- Update dependencies
- Security patches
- Database maintenance

### Quarterly
- Disaster recovery drill
- Capacity planning
- Security audit

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
