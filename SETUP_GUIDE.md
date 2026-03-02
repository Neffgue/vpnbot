# VPN Sales System - Setup Guide

Complete production-ready setup for a VPN subscription management system with Celery workers and React admin panel.

## Table of Contents

1. [Celery Worker Setup](#celery-worker-setup)
2. [React Admin Panel Setup](#react-admin-panel-setup)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Deployment](#deployment)

---

## Celery Worker Setup

### Prerequisites

- Python 3.8+
- Redis server (broker and result backend)
- PostgreSQL database

### Installation

```bash
pip install celery[redis]==5.3.4
pip install redis==5.0.1
pip install sqlalchemy==2.0.23
pip install sqlalchemy[asyncio]==2.0.23
pip install httpx==0.25.2
pip install python-dotenv==1.0.0
pip install asyncpg==0.29.0
```

### Environment Variables

Create `.env` file:

```env
REDIS_BROKER_URL=redis://localhost:6379/0
REDIS_BACKEND_URL=redis://localhost:6379/1
DATABASE_URL=postgresql+asyncpg://user:password@localhost/vpn_db
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_id_here
```

### Running the Celery Worker

```bash
# Start Celery worker
celery -A worker.celery_app worker --loglevel=info --concurrency=4

# In a separate terminal, start Celery Beat scheduler
celery -A worker.celery_app beat --loglevel=info
```

Or with supervisor:

```ini
[program:celery_worker]
command=celery -A worker.celery_app worker --loglevel=info --concurrency=4
directory=/path/to/project
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:celery_beat]
command=celery -A worker.celery_app beat --loglevel=info
directory=/path/to/project
autostart=true
autorestart=true
startsecs=10
```

### Task Descriptions

#### 1. `check_expiring_subscriptions` (Every 1 minute)
- Queries database for subscriptions expiring in 24h, 12h, 1h, 0h
- Checks for subscriptions expired 3 hours ago
- Sends Telegram notifications to users
- Tracks notification status with `notified_*` columns

**Requirements on Subscription model:**
```python
notified_24h: bool = False
notified_12h: bool = False
notified_1h: bool = False
notified_0h: bool = False
notified_3h_after_expiry: bool = False
```

#### 2. `health_check_servers` (Every 30 seconds)
- Pings 3x-ui panel for each server
- Updates `server.is_active` field
- Sends admin alerts when servers go up/down

**Requirements on Server model:**
```python
panel_url: str
panel_username: str
panel_password: str
is_active: bool = True
last_health_check: datetime = None
```

#### 3. `sync_traffic_stats` (Every 5 minutes)
- Fetches inbound stats from 3x-ui panels
- Updates `subscription.traffic_used_gb` field
- Stores last sync timestamp

**Requirements on Subscription model:**
```python
traffic_used_gb: float = 0.0
last_traffic_sync: datetime = None
```

#### 4. `cleanup_expired_subscriptions` (Daily at 00:00 UTC)
- Finds all expired active subscriptions
- Removes inbounds from 3x-ui panels
- Deactivates subscriptions

**Requirements on Subscription model:**
```python
is_active: bool = True
deactivated_at: datetime = None
```

### Task Queue Configuration

Tasks are routed to different queues:

```bash
# Run worker for notifications only
celery -A worker.celery_app worker -Q notifications

# Run worker for health checks
celery -A worker.celery_app worker -Q health_check

# Run worker for subscriptions
celery -A worker.celery_app worker -Q subscriptions

# Run worker for all queues
celery -A worker.celery_app worker -Q celery,notifications,health_check,subscriptions
```

### Error Handling

All tasks include:
- Automatic retry on failure (max 3 retries)
- Exponential backoff with countdown
- Comprehensive logging
- Async database session management with proper event loop handling

---

## React Admin Panel Setup

### Prerequisites

- Node.js 16+
- npm or yarn

### Installation

```bash
cd admin-panel
npm install
```

### Environment Variables

Create `.env.local`:

```env
VITE_API_URL=http://localhost:8000/api
```

### Running Development Server

```bash
npm run dev
```

Server runs on `http://localhost:5173` with proxy to backend API.

### Building for Production

```bash
npm run build
```

Output in `dist/` directory - serve with any static file server.

### Features

#### Authentication
- Email + password login
- JWT token in localStorage
- Automatic token refresh
- Protected routes

#### Dashboard
- Real-time stats (users, subscriptions, revenue)
- Server status overview
- Recent activity log

#### Users Management
- Searchable/paginated user list
- User detail page with:
  - Subscription history
  - Payment history
  - Referral information
  - Add balance form
  - Ban/unban functionality

#### Subscriptions
- Table with active/expired filter
- Extend subscription functionality
- Traffic usage display
- Status tracking

#### Server Management
- CRUD operations
- Server fields:
  - Name, country, host, port
  - Panel URL, credentials
  - Inbound ID
  - Bypass RU checkbox
- Toggle active status
- Test connection

#### Payments
- Searchable list with status filter
- Approve/reject payments
- Payment details view
- Date range filtering

#### Settings
- Bot token configuration
- Webhook URL
- Withdrawal limits
- Referral percentage

#### Bot Messages
- Edit all bot response texts
- Rich text support (HTML)
- Key-value pair management

#### Broadcast
- Send message to all users
- Character counter
- Message preview
- Delivery confirmation

#### Plan Prices
- Editable price table
- Multiple subscription periods
- Multiple plans (Solo, Family, etc.)

### API Integration

All API calls use Axios with:
- JWT Bearer authentication
- Automatic token refresh
- Error handling
- Proper status codes

Example API calls:

```javascript
// Login
await authApi.login(email, password)

// Fetch users
const users = await usersApi.getUsers(page, limit, search)

// Add balance
await usersApi.addBalance(userId, amount)

// Update servers
await serversApi.updateServer(id, serverData)

// Broadcast message
await settingsApi.broadcast(message)
```

### Styling

- Tailwind CSS for utility-first styling
- Dark theme by default
- Responsive design
- Custom color scheme optimized for dark mode

### State Management

- **Zustand** for authentication state
- **TanStack Query** for API data fetching and caching
- Built-in error handling and loading states

---

## Database Models

Required SQLAlchemy models:

```python
# User model
class User(Base):
    id: int
    email: str
    telegram_id: int (optional)
    telegram_username: str (optional)
    balance: float = 0.0
    is_active: bool = True
    last_active_at: datetime
    created_at: datetime
    
# Subscription model
class Subscription(Base):
    id: int
    user_id: int (FK)
    plan_id: int (FK)
    server_id: int (FK)
    inbound_id: int
    traffic_used_gb: float = 0.0
    is_active: bool = True
    expires_at: datetime
    created_at: datetime
    deactivated_at: datetime (nullable)
    last_traffic_sync: datetime (nullable)
    notified_24h: bool = False
    notified_12h: bool = False
    notified_1h: bool = False
    notified_0h: bool = False
    notified_3h_after_expiry: bool = False

# Server model
class Server(Base):
    id: int
    name: str
    country: str
    host: str
    port: int = 443
    panel_url: str
    panel_username: str
    panel_password: str
    inbound_id: str
    bypass_ru: bool = False
    is_active: bool = True
    last_health_check: datetime (nullable)
    created_at: datetime

# Payment model
class Payment(Base):
    id: int
    user_id: int (FK)
    amount: float
    method: str
    status: str (pending/approved/rejected)
    created_at: datetime

# Plan model
class Plan(Base):
    id: int
    name: str
    duration_days: int
    price: float
    created_at: datetime
```

---

## API Endpoints

### Auth
```
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/profile
POST /api/auth/refresh
```

### Users
```
GET /api/users?page=1&limit=20&search=...
GET /api/users/:id
GET /api/users/:id/subscriptions
GET /api/users/:id/payments
GET /api/users/:id/referrals
POST /api/users/:id/ban
POST /api/users/:id/unban
POST /api/users/:id/add-balance
POST /api/users/:id/send-message
```

### Subscriptions
```
GET /api/subscriptions?page=1&status=all
GET /api/subscriptions/:id
POST /api/subscriptions
POST /api/subscriptions/:id/extend
POST /api/subscriptions/:id/cancel
POST /api/subscriptions/:id/reset-traffic
```

### Servers
```
GET /api/servers
GET /api/servers/:id
POST /api/servers
PUT /api/servers/:id
DELETE /api/servers/:id
POST /api/servers/:id/toggle-active
POST /api/servers/:id/test-connection
GET /api/servers/:id/stats
```

### Payments
```
GET /api/payments?page=1&status=all&date_from=...&date_to=...
GET /api/payments/:id
POST /api/payments/:id/approve
POST /api/payments/:id/reject
GET /api/payments/stats
```

### Stats
```
GET /api/stats/dashboard
GET /api/stats/users?date_from=...&date_to=...
GET /api/stats/subscriptions
GET /api/stats/revenue
GET /api/stats/servers
```

### Settings
```
GET /api/settings
PUT /api/settings
GET /api/settings/bot-texts
PUT /api/settings/bot-texts
GET /api/settings/plan-prices
PUT /api/settings/plan-prices
POST /api/settings/broadcast
```

---

## Deployment

### Docker Compose Example

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: vpn_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  celery_worker:
    build: .
    command: celery -A worker.celery_app worker --loglevel=info
    environment:
      REDIS_BROKER_URL: redis://redis:6379/0
      REDIS_BACKEND_URL: redis://redis:6379/1
      DATABASE_URL: postgresql+asyncpg://user:password@postgres/vpn_db
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_ADMIN_ID: ${TELEGRAM_ADMIN_ID}
    depends_on:
      - redis
      - postgres

  celery_beat:
    build: .
    command: celery -A worker.celery_app beat --loglevel=info
    environment:
      REDIS_BROKER_URL: redis://redis:6379/0
      REDIS_BACKEND_URL: redis://redis:6379/1
      DATABASE_URL: postgresql+asyncpg://user:password@postgres/vpn_db
    depends_on:
      - redis
      - postgres

  web:
    build:
      context: admin-panel
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  postgres_data:
```

### Nginx Configuration

```nginx
upstream api {
    server localhost:8000;
}

upstream admin {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://admin;
        proxy_set_header Host $host;
    }
}
```

### SSL/TLS Setup

```bash
# Using Let's Encrypt with Certbot
sudo certbot certonly --standalone -d your-domain.com
```

---

## Monitoring

### Celery Flower

Monitor Celery tasks in real-time:

```bash
pip install flower
celery -A worker.celery_app flower --port=5555
```

Access at `http://localhost:5555`

### Logging

All components log to stdout/files. Configure logging in production:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('celery.log'),
        logging.StreamHandler()
    ]
)
```

---

## Performance Tuning

### Celery Configuration

```python
# worker/celery_app.py
app.conf.update(
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    task_time_limit=30 * 60,  # Kill task after 30 mins
    task_soft_time_limit=25 * 60,  # Graceful shutdown at 25 mins
)
```

### Database Optimization

- Use connection pooling
- Add indexes on frequently queried columns
- Use async sessions for concurrent operations

### Redis Optimization

- Configure `maxmemory` policy
- Monitor memory usage
- Use persistence for reliability

---

## Troubleshooting

### Tasks not running

1. Check Redis connection
2. Verify database connection
3. Check Celery Beat is running
4. Monitor Celery worker logs

### Notification not sending

1. Verify Telegram bot token
2. Check user has `telegram_id` set
3. Review API rate limits

### Health checks failing

1. Verify panel credentials
2. Check server firewall
3. Test connectivity manually

### High memory usage

1. Reduce worker concurrency
2. Lower `task_time_limit`
3. Configure Redis eviction policy

---

## License

Proprietary - VPN Sales System
