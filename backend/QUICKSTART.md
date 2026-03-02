# Quick Start Guide

Get the VPN Sales System API running in 5 minutes.

## Prerequisites

- Python 3.11+
- PostgreSQL 12+ (or Docker)
- Git

## Option 1: Local Development (with Docker)

### Fastest Setup (Recommended)

```bash
# 1. Clone repository
git clone <repo_url>
cd backend

# 2. Create .env file
cp .env.example .env

# 3. Start services with Docker Compose
docker-compose up -d

# 4. Check services are running
docker-compose ps

# 5. Access API
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
# Health check: http://localhost:8000/health
```

Done! The database is automatically initialized.

## Option 2: Local Development (Manual)

### Setup

```bash
# 1. Clone repository
git clone <repo_url>
cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env

# Edit .env if needed (defaults work for local dev)
# DATABASE_URL=postgresql+asyncpg://vpn_user:vpn_password@localhost:5432/vpn_db

# 5. Start PostgreSQL (if not already running)
# On macOS with Homebrew:
brew services start postgresql

# On Linux:
sudo service postgresql start

# On Windows: Use PostgreSQL installer or Docker

# 6. Run migrations
alembic upgrade head

# 7. Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs

## First API Call

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "John"
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "referral_code": "ABC123XYZ",
  "balance": "0.00",
  "is_banned": false,
  "is_admin": false,
  "free_trial_used": false,
  "created_at": "2024-01-01T00:00:00+00:00"
}
```

### 2. Get Authentication Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token?telegram_id=123456789
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Save the `access_token` - you'll use it for protected endpoints.

### 3. Get Current User (Protected)

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 4. List Servers (Public)

```bash
curl -X GET http://localhost:8000/api/v1/servers
```

### 5. Create a Server (Admin)

First, make the user an admin (via database):

```bash
psql -U vpn_user -d vpn_db
UPDATE users SET is_admin = true WHERE telegram_id = 123456789;
\q
```

Then create a server:

```bash
curl -X POST http://localhost:8000/api/v1/admin/servers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NL-Amsterdam-01",
    "country_emoji": "🇳🇱",
    "country_name": "Netherlands",
    "host": "195.154.1.1",
    "port": 443,
    "panel_url": "https://xui.example.com",
    "panel_username": "admin",
    "panel_password": "password123",
    "inbound_id": 1,
    "order_index": 1
  }'
```

### 6. Create Plan Pricing (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/admin/plans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Solo",
    "period_days": 30,
    "price_rub": "299.99"
  }'
```

### 7. Purchase Subscription

```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/purchase \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Solo",
    "period_days": 30
  }'
```

## Interactive Testing with Swagger UI

1. Open http://localhost:8000/docs in your browser
2. Register a user via the `/auth/register` endpoint
3. Get a token via the `/auth/token` endpoint
4. Click "Authorize" button and paste your token
5. Try protected endpoints
6. Explore all available endpoints

## Database Inspection

View data in the database:

```bash
# Connect to PostgreSQL
psql -U vpn_user -d vpn_db

# List tables
\dt

# View users
SELECT id, telegram_id, username, referral_code, is_admin FROM users;

# View subscriptions
SELECT id, user_id, plan_name, expires_at, is_active FROM subscriptions;

# View servers
SELECT name, host, country_name, is_active FROM servers;

# Disconnect
\q
```

## Environment Variables

Key environment variables in `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | postgresql+asyncpg://... | Database connection |
| `SECRET_KEY` | your-secret-key | JWT signing key |
| `DEBUG` | False | Debug mode |
| `BOT_TOKEN` | - | Telegram bot token |
| `YOOKASSA_SHOP_ID` | - | Payment provider ID |

## Common Tasks

### Reset Database

```bash
# Drop all tables
alembic downgrade base

# Recreate tables
alembic upgrade head
```

### View Logs

```bash
# In terminal where server is running, logs appear in real-time

# Or view application logs
tail -f /var/log/vpn-api/app.log  # If running as service
```

### Create Admin User

```bash
psql -U vpn_user -d vpn_db
UPDATE users SET is_admin = true WHERE telegram_id = YOUR_TELEGRAM_ID;
```

### Add Balance to User

Via API (admin only):
```bash
curl -X POST http://localhost:8000/api/v1/admin/users/{user_id}/balance \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-id-here",
    "amount": "100.00",
    "reason": "Manual credit"
  }'
```

### Ban User

```bash
curl -X POST http://localhost:8000/api/v1/admin/users/{user_id}/ban \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-id-here",
    "is_banned": true
  }'
```

## Testing the Payment System

The payment endpoints expect webhooks from payment providers. To test locally:

### Telegram Stars Test

```bash
curl -X POST http://localhost:8000/api/v1/payments/telegram-stars/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123,
    "successful_payment_checkout": {
      "telegram_payment_charge_id": "test-123",
      "provider_payment_charge_id": "test-provider-123"
    }
  }'
```

### YooKassa Test

```bash
curl -X POST http://localhost:8000/api/v1/payments/yookassa/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "notification",
    "event": "payment.succeeded",
    "data": {
      "object": {
        "id": "payment-id-123",
        "status": "succeeded",
        "metadata": {
          "payment_id": "your-payment-id"
        }
      }
    }
  }'
```

## Troubleshooting

### Port 8000 already in use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database connection refused
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Or start it
sudo service postgresql start

# Check connection string in .env
```

### ModuleNotFoundError
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or activate virtual environment
source venv/bin/activate
```

### Alembic migration errors
```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Reset to base
alembic downgrade base

# Reapply migrations
alembic upgrade head
```

## Next Steps

1. **Read the full documentation**
   - [API Documentation](./API_DOCUMENTATION.md)
   - [Deployment Guide](./DEPLOYMENT.md)
   - [Testing Guide](./TESTING.md)

2. **Set up payment providers**
   - Configure Telegram Bot API
   - Set up YooKassa account

3. **Customize bot texts**
   - Create bot text configurations via admin endpoints
   - Update messages for your brand

4. **Create pricing plans**
   - Add Solo and Family plans
   - Set prices for different periods

5. **Add VPN servers**
   - Configure 3x-ui panel credentials
   - Add servers to the system

6. **Implement bot**
   - Create Telegram bot using Bot API
   - Integrate with API for user operations

## Support

For issues or questions:
- Check [API Documentation](./API_DOCUMENTATION.md)
- Review [DEPLOYMENT.md](./DEPLOYMENT.md) for production setup
- Check logs for error messages
- See [TESTING.md](./TESTING.md) for testing examples

---

**Ready to deploy?** See [DEPLOYMENT.md](./DEPLOYMENT.md) for production setup instructions.
