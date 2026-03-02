# VPN Sales System Backend

Complete production-ready FastAPI backend for VPN sales platform with Telegram integration, payment processing, and 3x-ui panel management.

## Features

- **User Management**: Registration, authentication, profiles with JWT tokens
- **Subscription System**: Multiple plans (Solo, Family), flexible periods (7-365 days)
- **Payment Processing**: Telegram Stars and YooKassa integration with webhooks
- **Referral System**: Automatic bonus days for referrer when referred user purchases
- **VPN Configuration**: Public endpoint for Happ app with VLESS links
- **3x-ui Panel Integration**: Async client management (add, update, delete, stats)
- **Admin Dashboard**: User management, server CRUD, pricing, bot text configuration
- **Database**: PostgreSQL with async SQLAlchemy and Alembic migrations
- **Security**: JWT authentication, password hashing with bcrypt
- **Logging**: Structured logging throughout the application

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL with SQLAlchemy 2.0 async
- **Authentication**: JWT (python-jose)
- **HTTP Client**: httpx (async)
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Python**: 3.11+

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis (optional, for caching)

### Installation

1. Clone the repository
```bash
git clone <repo_url>
cd backend
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run database migrations
```bash
alembic upgrade head
```

6. Start the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Setup

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis cache
- API server (with auto-reload)

Access at `http://localhost:8000`

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
backend/
├── main.py                 # FastAPI app initialization
├── config.py              # Configuration management
├── database.py            # Database setup
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic schemas for validation
├── api/                   # API routes
│   ├── deps.py           # Dependency injection
│   └── v1/
│       ├── router.py     # Route aggregation
│       └── endpoints/    # Endpoint handlers
├── services/              # Business logic
├── repositories/          # Database access layer
├── utils/                 # Utilities (security, crypto, etc)
└── alembic/              # Database migrations
```

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vpn_db

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Bot
BOT_TOKEN=your-telegram-bot-token

# YooKassa
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_API_KEY=your-api-key

# Encryption
ENCRYPTION_KEY=your-fernet-key
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/token` - Get JWT tokens
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/{user_id}` - Get user by ID
- `GET /api/v1/users/by-referral/{code}` - Get user by referral code

### Subscriptions
- `GET /api/v1/subscriptions` - List user subscriptions
- `GET /api/v1/subscriptions/{id}` - Get subscription
- `POST /api/v1/subscriptions/purchase` - Purchase subscription
- `POST /api/v1/subscriptions/{id}/extend` - Extend subscription

### Servers
- `GET /api/v1/servers` - List active servers
- `GET /api/v1/servers/{id}` - Get server details
- `GET /api/v1/servers/country/{name}` - Get servers by country

### Payments
- `GET /api/v1/payments/{id}` - Get payment details
- `POST /api/v1/payments/yookassa/webhook` - YooKassa webhook
- `POST /api/v1/payments/telegram-stars/webhook` - Telegram Stars webhook

### Referrals
- `GET /api/v1/referrals/stats` - Get referral stats
- `GET /api/v1/referrals/code` - Get referral code

### VPN Config
- `GET /api/v1/vpn/{uuid}` - Get VPN config for Happ app (public)

### Admin
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/users/search` - Search users
- `POST /api/v1/admin/users/{id}/ban` - Ban/unban user
- `POST /api/v1/admin/users/{id}/balance` - Update user balance
- `POST /api/v1/admin/servers` - Create server
- `PUT /api/v1/admin/servers/{id}` - Update server
- `DELETE /api/v1/admin/servers/{id}` - Delete server
- `GET /api/v1/admin/plans` - List plan prices
- `POST /api/v1/admin/plans` - Create/update plan
- `DELETE /api/v1/admin/plans/{id}` - Delete plan
- `GET /api/v1/admin/bot-texts` - List bot texts
- `POST /api/v1/admin/bot-texts` - Create/update bot text
- `PUT /api/v1/admin/bot-texts/{id}` - Update bot text
- `DELETE /api/v1/admin/bot-texts/{id}` - Delete bot text
- `POST /api/v1/admin/broadcasts` - Create broadcast
- `GET /api/v1/admin/stats` - Get system statistics

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Downgrade one migration:
```bash
alembic downgrade -1
```

## Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Admin endpoints additionally require `is_admin=true` on the user.

## Payment Processing

### YooKassa
1. User initiates purchase
2. API creates Payment record with status=pending
3. User completes payment on YooKassa
4. YooKassa sends webhook to `/api/v1/payments/yookassa/webhook`
5. API marks payment as completed, creates subscription
6. Referral bonuses are processed if applicable

### Telegram Stars
Similar flow with Telegram Bot API integration.

## 3x-ui Panel Integration

The `XUIService` manages client lifecycle:
- Login and session management
- Add client with traffic limits and expiry
- Update client configuration
- Delete client
- Get client statistics

## Logging

Logs are configured in `main.py` and use Python's standard logging module. Configure log level via `DEBUG` environment variable.

## Development

### Code Style
```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

### Testing
```bash
pytest tests/ -v
```

## Production Deployment

1. Set `DEBUG=False`
2. Use strong `SECRET_KEY`
3. Configure database with proper credentials
4. Set up environment variables securely
5. Use HTTPS/TLS
6. Configure CORS properly
7. Set up proper logging
8. Use a production ASGI server (Gunicorn + Uvicorn)
9. Set up database backups
10. Monitor application health

## License

Proprietary - VPN Sales System
