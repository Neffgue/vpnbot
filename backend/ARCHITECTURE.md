# Architecture & System Design

## Overview

VPN Sales System is a production-ready FastAPI backend for managing VPN subscriptions, payments, and user management with Telegram integration.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Happ App    │  │ Telegram Bot │  │  Admin Web Panel     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼──────────────────┼─────────────────────┼──────────────┘
          │                  │                     │
          └──────────────────┼─────────────────────┘
                             │ HTTP/REST
          ┌──────────────────▼──────────────────┐
          │     FastAPI Application (Port 8000) │
          │  ┌────────────────────────────────┐ │
          │  │   API Routes & Endpoints       │ │
          │  │  - Authentication              │ │
          │  │  - User Management             │ │
          │  │  - Subscriptions               │ │
          │  │  - Payments & Webhooks         │ │
          │  │  - VPN Configuration           │ │
          │  │  - Admin Operations            │ │
          │  └────────────────────────────────┘ │
          │                                      │
          │  ┌────────────────────────────────┐ │
          │  │   Business Logic Layer         │ │
          │  │  - Services (User, Payment)    │ │
          │  │  - XUI Panel Integration       │ │
          │  │  - Payment Processing          │ │
          │  │  - Referral System             │ │
          │  └────────────────────────────────┘ │
          │                                      │
          │  ┌────────────────────────────────┐ │
          │  │   Data Access Layer            │ │
          │  │  - Repositories                │ │
          │  │  - Database Queries            │ │
          │  └────────────────────────────────┘ │
          └──────────────────┬───────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐
│   PostgreSQL DB  │  │  3x-ui Panels   │  │  Payment API │
│  - Tables        │  │  - Inbounds     │  │  - YooKassa  │
│  - Migrations    │  │  - Clients      │  │  - Telegram  │
└──────────────────┘  └─────────────────┘  └──────────────┘
```

## Layered Architecture

### 1. API Layer (`api/v1/endpoints/`)

**Responsibility:** HTTP request handling, input validation, response formatting

**Components:**
- `auth.py` - Authentication endpoints
- `users.py` - User management
- `subscriptions.py` - Subscription operations
- `servers.py` - Server listing
- `payments.py` - Payment processing and webhooks
- `referrals.py` - Referral system
- `admin.py` - Administrative operations
- `vpn_config.py` - VPN configuration for Happ app

**Key Features:**
- JWT-based authentication
- Input validation with Pydantic schemas
- Error handling and HTTP status codes
- Pagination support

### 2. Service Layer (`services/`)

**Responsibility:** Business logic, orchestration, external API calls

**Components:**
- `user_service.py` - User operations (create, update, ban)
- `subscription_service.py` - Subscription lifecycle management
- `server_service.py` - Server CRUD operations
- `payment_service.py` - Payment tracking and processing
- `referral_service.py` - Referral bonus management
- `xui_service.py` - 3x-ui panel client management
- `notification_service.py` - Telegram notifications
- `payment_service.py` - Plan pricing queries

**Key Features:**
- Async/await for I/O operations
- Error logging
- Business rule enforcement
- External service integration

### 3. Repository Layer (`repositories/`)

**Responsibility:** Database abstraction, query building, persistence

**Components:**
- `base.py` - Generic repository operations
- `user_repo.py` - User queries
- `subscription_repo.py` - Subscription queries
- `server_repo.py` - Server queries
- `payment_repo.py` - Payment queries

**Key Features:**
- Async SQLAlchemy queries
- Query optimization with eager loading
- Index usage
- Transaction management

### 4. Data Layer (`models/`)

**Responsibility:** Database schema definition

**Models:**
- `user.py` - User accounts
- `subscription.py` - User VPN subscriptions
- `server.py` - VPN servers
- `payment.py` - Payment transactions
- `referral.py` - Referral relationships
- `config.py` - Configuration tables (prices, bot texts, broadcasts)

**Key Features:**
- SQLAlchemy ORM models
- Relationship definitions
- Index specifications
- Cascade delete rules

## Data Flow

### User Registration Flow

```
Client Request
    │
    ▼
POST /auth/register
    │
    ▼
Input Validation (Pydantic)
    │
    ▼
UserService.create_user()
    │
    ├─ Generate referral code
    ├─ Check if user exists
    └─ UserRepository.create()
        │
        ▼
    Database INSERT
        │
        ▼
Response with User object
```

### Payment Processing Flow

```
Payment Initiated
    │
    ▼
POST /subscriptions/purchase
    │
    ▼
PaymentService.create_payment() [PENDING]
    │
    ▼
Response with payment_id to client
    │
    ▼
User completes payment at provider
    │
    ▼
Provider sends webhook
    │
    ▼
POST /payments/yookassa/webhook (or telegram-stars)
    │
    ▼
_process_payment_success()
    │
    ├─ Mark payment as COMPLETED
    │
    ├─ SubscriptionService.create_subscription()
    │
    ├─ Check for pending referral
    │
    └─ ReferralService.mark_referral_paid()
        └─ Extend referrer's subscription
```

### VPN Access Flow

```
User (Happ App)
    │
    ▼
GET /api/v1/vpn/{uuid}
    │
    ▼
Verify subscription active & not expired
    │
    ├─ Get subscription from DB
    ├─ Get user info
    └─ Get servers and generate VLESS links
        │
        ▼
Return config JSON with subscription link
    │
    ▼
Happ App decodes and shows servers
```

## Database Schema

### Core Tables

```
users
├─ id (UUID, PK)
├─ telegram_id (BIGINT, UNIQUE)
├─ referral_code (VARCHAR, UNIQUE)
├─ referred_by (FK to users)
├─ balance (DECIMAL)
├─ is_banned (BOOLEAN)
└─ timestamps

subscriptions
├─ id (UUID, PK)
├─ user_id (FK to users)
├─ xui_client_uuid (UUID, UNIQUE)
├─ plan_name (VARCHAR)
├─ device_limit (INT)
├─ traffic_gb (INT)
├─ expires_at (DATETIME)
└─ is_active (BOOLEAN)

servers
├─ id (UUID, PK)
├─ name (VARCHAR, UNIQUE)
├─ country_name (VARCHAR)
├─ host (VARCHAR)
├─ port (INT)
├─ panel_url (VARCHAR)
└─ panel credentials

subscription_server_association (M2M)
├─ subscription_id (FK)
└─ server_id (FK)

payments
├─ id (UUID, PK)
├─ user_id (FK to users)
├─ provider_payment_id (VARCHAR, UNIQUE)
├─ status (VARCHAR) - pending/completed/failed
├─ amount (DECIMAL)
└─ provider (VARCHAR)

referrals
├─ id (UUID, PK)
├─ referrer_id (FK to users)
├─ referred_id (FK to users, UNIQUE)
├─ bonus_days (INT)
└─ paid_at (DATETIME)

plan_prices
├─ plan_name (VARCHAR)
├─ period_days (INT)
└─ price_rub (DECIMAL)

bot_texts
├─ key (VARCHAR, UNIQUE)
└─ value (VARCHAR)
```

### Indexes

```
users:
  - ix_telegram_id (UNIQUE)
  - ix_referral_code (UNIQUE)

subscriptions:
  - ix_user_id
  - ix_xui_client_uuid (UNIQUE)
  - ix_expires_at (for expiry checks)
  - ix_is_active

payments:
  - ix_user_id
  - ix_provider_payment_id (UNIQUE)
  - ix_status (for pending payments)

servers:
  - ix_name (UNIQUE)
  - ix_is_active (for listing)
```

## Authentication & Authorization

### JWT Token Structure

```
Access Token (15 minutes):
{
  "sub": "user-id",
  "exp": "timestamp",
  "iat": "timestamp"
}

Refresh Token (7 days):
{
  "sub": "user-id",
  "exp": "timestamp",
  "type": "refresh"
}
```

### Authorization Levels

```
Public Endpoints:
- /auth/register
- /auth/token
- /servers
- /vpn/{uuid}

Authenticated Endpoints:
- /users/me
- /subscriptions
- /referrals

Admin Endpoints:
- /admin/* (requires is_admin=true)
```

## External Integrations

### 3x-ui Panel Integration

```python
XUIService
├─ login() - Get session cookie
├─ add_client() - Create VPN client
├─ update_client() - Modify limits/expiry
├─ delete_client() - Remove client
└─ get_client_stats() - Check usage
```

**Flow:**
1. User purchases subscription
2. SubscriptionService creates subscription with UUID
3. XUIService.add_client() adds client to panel
4. Client can connect to VPN using UUID

### Payment Provider Integration

**YooKassa:**
```
User initiates payment
    ↓
API creates Payment (pending)
    ↓
User redirected to YooKassa
    ↓
YooKassa webhook sent
    ↓
Webhook handler marks payment completed
    ↓
Subscription created
```

**Telegram Stars:**
```
User initiates payment via Bot
    ↓
Bot sends pre_checkout_query
    ↓
API creates Payment
    ↓
User confirms in Telegram
    ↓
Telegram sends successful_payment update
    ↓
API creates subscription
```

## Scalability Considerations

### Current Architecture (Single Instance)

- Single FastAPI process
- PostgreSQL with connection pooling
- Synchronous webhooks
- In-memory session storage

### Scaling to Multiple Instances

```
Load Balancer (Nginx/HAProxy)
    ↓
┌───────────────┬───────────────┬───────────────┐
│ API Instance 1│ API Instance 2│ API Instance 3│
└───────┬───────┴───────┬───────┴───────┬───────┘
        │               │               │
        └───────────────┼───────────────┘
                        ↓
                PostgreSQL (Primary)
                    ↓
            PostgreSQL (Replicas)
```

**Implementation:**
- Use Gunicorn with multiple workers
- Connection pooling (SQLAlchemy)
- Redis for caching and sessions
- Message queue for async tasks (Celery)

### Performance Optimization

1. **Database:**
   - Proper indexes
   - Query optimization
   - Connection pooling
   - Read replicas

2. **API:**
   - Response caching
   - Pagination
   - Lazy loading
   - Compression

3. **Background Tasks:**
   - Async notifications
   - Subscription expiry checks
   - Payment reconciliation

## Security Architecture

### Input Validation

```
Pydantic Schemas
    ↓
Type checking
Constraint validation
    ↓
Sanitization
```

### Authentication

```
JWT Token
    ↓
Verify signature
Check expiration
Get user from DB
Check banned status
```

### Authorization

```
Check user ownership
Check admin status
Enforce business rules
```

### Data Protection

```
Passwords: bcrypt hashing
Sensitive data: Fernet encryption
Secrets: Environment variables
API Keys: Secure storage
```

## Error Handling Strategy

### Error Layers

```
API Layer:
  - Input validation errors → 400 Bad Request
  - Authentication errors → 401 Unauthorized
  - Authorization errors → 403 Forbidden
  - Not found errors → 404 Not Found

Service Layer:
  - Business logic errors → 422 Unprocessable
  - External API errors → logged, retry or fail

Repository Layer:
  - Database errors → logged, retry or fail
  - Connection errors → logged, circuit breaker

Logging:
  - All errors logged with context
  - Stack traces in DEBUG mode
```

## Deployment Architecture

### Development

```
Local Machine
    ↓
Docker Compose
├─ PostgreSQL
├─ Redis
└─ FastAPI (with hot reload)
```

### Production

```
Reverse Proxy (Nginx)
    ↓
Load Balancer
    ↓
┌─────────────┬─────────────┬─────────────┐
│ Gunicorn    │ Gunicorn    │ Gunicorn    │
│ (4 workers) │ (4 workers) │ (4 workers) │
└──────┬──────┴──────┬──────┴──────┬──────┘
       │             │             │
       └─────────────┼─────────────┘
                     ↓
         PostgreSQL (Primary)
                     ↓
         PostgreSQL (Standby)
                     ↓
              Backup Storage
```

## Monitoring & Observability

### Health Checks

```
GET /health
    ↓
Check database connection
Check API status
Return uptime metrics
```

### Logging

```
Application logs:
  - INFO: Major events
  - ERROR: Failures
  - DEBUG: Detailed info

Structured logging:
  - Timestamp
  - Level
  - Module
  - Message
  - Context/stack trace
```

### Metrics

```
API metrics:
  - Request count
  - Response time
  - Error rate
  - Status codes

Database metrics:
  - Query time
  - Connection pool usage
  - Slow queries

Business metrics:
  - User count
  - Active subscriptions
  - Payment success rate
  - Revenue
```

## Testing Strategy

### Unit Tests

```
Services:
  - Business logic
  - Error handling

Repositories:
  - Query correctness
  - Edge cases
```

### Integration Tests

```
API endpoints:
  - Request/response
  - Authentication
  - Authorization
  - Database interactions
```

### Load Tests

```
Performance:
  - Response time under load
  - Concurrent user handling
  - Database bottlenecks
```

## API Versioning

```
Current: /api/v1/

Future versions:
  /api/v2/ - Breaking changes
  /api/v3/ - New major features
```

**Strategy:**
- Maintain backward compatibility in v1
- Deprecation notices for planned changes
- Separate major versions for breaking changes

## Future Enhancements

### Planned Features

1. **Caching Layer**
   - Redis for frequent queries
   - Cache invalidation strategy

2. **Async Task Processing**
   - Celery for background jobs
   - Scheduled tasks (expiry notifications)

3. **Advanced Analytics**
   - User behavior tracking
   - Revenue analytics
   - Churn analysis

4. **Multi-Currency Support**
   - Currency conversion
   - Regional pricing

5. **Advanced Referral System**
   - Multi-tier referrals
   - Referral commissions

6. **Mobile API**
   - Native app endpoints
   - Optimization for mobile

7. **Monitoring & Analytics**
   - Real-time dashboards
   - Performance metrics

---

This architecture provides a solid foundation for a scalable, maintainable VPN sales platform.
