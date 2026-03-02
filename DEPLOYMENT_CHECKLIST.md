# VPN Sales System - Deployment Checklist

Complete checklist for deploying the VPN Sales System to production.

## Pre-Deployment

### Infrastructure
- [ ] Server provisioned (Ubuntu 22.04, 4GB+ RAM, 20GB+ storage)
- [ ] Domain name registered and DNS configured
- [ ] SSH access verified
- [ ] Firewall rules configured (ports 22, 80, 443 open)
- [ ] Server hardening completed

### Configuration
- [ ] `.env` file created from `.env.example`
- [ ] All required environment variables filled:
  - [ ] `POSTGRES_PASSWORD` - strong password
  - [ ] `REDIS_PASSWORD` - strong password
  - [ ] `BOT_TOKEN` - Telegram bot token
  - [ ] `JWT_SECRET_KEY` - long random string
  - [ ] `YOOKASSA_SHOP_ID` - payment gateway ID
  - [ ] `YOOKASSA_SECRET_KEY` - payment gateway secret
  - [ ] `WEBHOOK_URL` - correct domain
  - [ ] `WEBHOOK_SECRET` - strong secret
  - [ ] `ADMIN_USERNAME` - admin account
  - [ ] `ADMIN_PASSWORD` - strong password
  - [ ] `DOMAIN_NAME` - production domain
  - [ ] `LETSENCRYPT_EMAIL` - valid email for SSL

### Code Review
- [ ] Code reviewed and tested locally
- [ ] All tests passing: `make test`
- [ ] No secrets in code or git history
- [ ] `.gitignore` properly configured
- [ ] Docker images built successfully

## Initial Server Setup

- [ ] SSH into production server
- [ ] Run setup script:
  ```bash
  sudo bash scripts/setup_server.sh
  ```
- [ ] Verify Docker installation
- [ ] Verify Docker Compose installation
- [ ] Repository cloned to `/opt/vpn-system`
- [ ] `.env` file configured
- [ ] SSL certificates created with Certbot

## Deployment

### Pre-deployment Checks
- [ ] Database backup created: `bash scripts/backup.sh`
- [ ] Current services running correctly
- [ ] No ongoing transactions or operations
- [ ] Team notified of deployment window

### Deployment Steps
- [ ] Pull latest code: `git pull origin main`
- [ ] Verify changes: `git log --oneline -5`
- [ ] Run deployment: `bash scripts/deploy.sh`
- [ ] Monitor deployment logs
- [ ] All services started successfully
- [ ] No errors in application logs

### Post-Deployment Verification

#### Health Checks
- [ ] Backend health: `curl http://localhost:8000/health`
- [ ] Admin panel accessible: `http://localhost:3000/admin`
- [ ] PostgreSQL responding
- [ ] Redis responding
- [ ] Nginx proxying correctly

#### Functional Tests
- [ ] Admin login works
- [ ] Dashboard loads
- [ ] Database queries work
- [ ] Bot receives updates
- [ ] Payments process correctly
- [ ] Email notifications sent

#### Performance Checks
- [ ] Response times acceptable
- [ ] CPU usage reasonable
- [ ] Memory usage stable
- [ ] Disk space available
- [ ] No error messages in logs

#### Security Checks
- [ ] HTTPS working with valid certificate
- [ ] HTTP redirects to HTTPS
- [ ] Security headers present
- [ ] No sensitive data in logs
- [ ] Rate limiting active

## Post-Deployment

### Monitoring Setup
- [ ] Health check script configured: `scripts/health_check.sh`
- [ ] Cron job for health checks added
- [ ] Log rotation configured
- [ ] Backup schedule verified

### Documentation
- [ ] Deployment details logged
- [ ] Configuration documented
- [ ] Access credentials stored securely
- [ ] Runbook updated
- [ ] Team notified of changes

### Backup Verification
- [ ] Database backup successful
- [ ] Backup stored in safe location
- [ ] Backup restore procedure tested
- [ ] S3 upload verified (if configured)

### Monitoring & Alerts
- [ ] Application metrics monitored
- [ ] Alert thresholds configured
- [ ] Uptime monitoring enabled
- [ ] Error rate monitoring active
- [ ] Performance metrics tracked

## Rollback Plan

If issues occur after deployment:

1. **Immediate Rollback** (if critical)
   ```bash
   git checkout previous_commit
   bash scripts/deploy.sh
   ```

2. **Database Rollback** (if data issues)
   ```bash
   bash scripts/restore_backup.sh path/to/backup.sql.gz
   ```

3. **Service Restart** (if service hangs)
   ```bash
   docker-compose -f docker-compose.prod.yml restart <service>
   ```

4. **Complete Reset** (if severe)
   - Restore from last known good backup
   - Redeploy from previous git tag
   - Run migrations if needed

## Maintenance Schedule

### Daily
- [ ] Monitor error logs
- [ ] Check service health
- [ ] Monitor resource usage

### Weekly
- [ ] Review backup status
- [ ] Check certificate renewal progress
- [ ] Analyze performance metrics

### Monthly
- [ ] Update dependencies
- [ ] Security patches
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Review and rotate logs

### Quarterly
- [ ] Full disaster recovery test
- [ ] Capacity planning review
- [ ] Security audit

## Emergency Contacts

- **Admin**: [Name] - [Phone/Email]
- **DevOps**: [Name] - [Phone/Email]
- **Support**: [Name] - [Phone/Email]

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f <service>

# Restart service
docker-compose -f docker-compose.prod.yml restart <service>

# Database shell
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d vpn_system

# Redis CLI
docker-compose -f docker-compose.prod.yml exec redis redis-cli

# Create backup
bash scripts/backup.sh

# Health check
bash scripts/health_check.sh

# Deploy update
bash scripts/deploy.sh

# View Docker stats
docker stats --no-stream
```

## Documentation Links

- [Main README](./README.md)
- [Setup Guide](./SETUP_GUIDE.md)
- [API Documentation](./backend/README.md)
- [Admin Panel Guide](./ADMIN_PANEL_GUIDE.md)

---

**Last Updated**: [Date]
**Deployed By**: [Name]
**Deployment Approved By**: [Name]
