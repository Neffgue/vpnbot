# VPN Sales System API Documentation

Complete API reference for the VPN Sales System backend.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Get tokens via the `/auth/token` endpoint.

---

## Authentication Endpoints

### Register User

**Endpoint:** `POST /auth/register`

**Description:** Register a new user with Telegram ID.

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "referred_by": "referrer_user_id"  // optional
}
```

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "referral_code": "ABC123",
  "balance": "0.00",
  "is_banned": false,
  "is_admin": false,
  "free_trial_used": false,
  "created_at": "2024-01-01T00:00:00+00:00"
}
```

---

### Get Access Token

**Endpoint:** `POST /auth/token`

**Description:** Get JWT access and refresh tokens for a user.

**Query Parameters:**
- `telegram_id` (int, required): User's Telegram ID

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### Refresh Token

**Endpoint:** `POST /auth/refresh`

**Description:** Get a new access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## User Endpoints

### Get Current User Profile

**Endpoint:** `GET /users/me`

**Authentication:** Required

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "referral_code": "ABC123",
  "balance": "100.50",
  "is_banned": false,
  "is_admin": false,
  "free_trial_used": false,
  "created_at": "2024-01-01T00:00:00+00:00",
  "updated_at": "2024-01-02T10:30:00+00:00"
}
```

---

### Update User Profile

**Endpoint:** `PUT /users/me`

**Authentication:** Required

**Request Body:**
```json
{
  "username": "john_doe_new",
  "first_name": "John"
}
```

**Response:** Updated user object

---

### Get User by ID

**Endpoint:** `GET /users/{user_id}`

**Description:** Public endpoint - no authentication required.

**Response:** User object

---

### Get User by Referral Code

**Endpoint:** `GET /users/by-referral/{referral_code}`

**Description:** Public endpoint to get user by their referral code.

**Response:** User object

---

## Subscription Endpoints

### List User Subscriptions

**Endpoint:** `GET /subscriptions`

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "sub-001",
    "user_id": "user-001",
    "plan_name": "Solo",
    "device_limit": 1,
    "traffic_gb": 100,
    "expires_at": "2024-02-01T00:00:00+00:00",
    "is_active": true,
    "xui_client_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-01T00:00:00+00:00",
    "servers": [
      {
        "id": "srv-001",
        "name": "NL-Amsterdam-01",
        "country_emoji": "🇳🇱",
        "country_name": "Netherlands"
      }
    ]
  }
]
```

---

### Get Subscription

**Endpoint:** `GET /subscriptions/{subscription_id}`

**Authentication:** Required

**Response:** Subscription object

---

### Purchase Subscription

**Endpoint:** `POST /subscriptions/purchase`

**Authentication:** Required

**Request Body:**
```json
{
  "plan_name": "Solo",
  "period_days": 30
}
```

**Response:**
```json
{
  "payment_id": "pay-001",
  "amount": 299.99,
  "currency": "RUB",
  "provider": "telegram_stars"
}
```

---

### Extend Subscription

**Endpoint:** `POST /subscriptions/{subscription_id}/extend`

**Authentication:** Required

**Query Parameters:**
- `days` (int, required): Number of days to extend

**Response:** Updated subscription object

---

## Server Endpoints

### List Active Servers

**Endpoint:** `GET /servers`

**Description:** Public endpoint - no authentication required.

**Query Parameters:**
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=100): Results per page

**Response:**
```json
[
  {
    "id": "srv-001",
    "name": "NL-Amsterdam-01",
    "country_emoji": "🇳🇱",
    "country_name": "Netherlands",
    "host": "195.154.1.1",
    "port": 443,
    "is_active": true,
    "bypass_ru_whitelist": false,
    "order_index": 1,
    "created_at": "2024-01-01T00:00:00+00:00"
  }
]
```

---

### Get Server

**Endpoint:** `GET /servers/{server_id}`

**Description:** Public endpoint.

**Response:** Server object

---

### Get Servers by Country

**Endpoint:** `GET /servers/country/{country_name}`

**Description:** Public endpoint.

**Response:** Array of server objects

---

## Payment Endpoints

### Get Payment Details

**Endpoint:** `GET /payments/{payment_id}`

**Authentication:** Required

**Response:**
```json
{
  "id": "pay-001",
  "user_id": "user-001",
  "amount": "299.99",
  "currency": "RUB",
  "provider": "telegram_stars",
  "provider_payment_id": "tg_payment_123",
  "status": "completed",
  "plan_name": "Solo",
  "period_days": 30,
  "device_limit": 1,
  "created_at": "2024-01-01T00:00:00+00:00"
}
```

**Statuses:** `pending`, `completed`, `failed`, `refunded`

---

### YooKassa Webhook

**Endpoint:** `POST /payments/yookassa/webhook`

**Description:** Receive payment notifications from YooKassa.

**Request Body:** YooKassa webhook payload

**Response:**
```json
{
  "status": "ok"
}
```

---

### Telegram Stars Webhook

**Endpoint:** `POST /payments/telegram-stars/webhook`

**Description:** Receive payment notifications from Telegram Stars.

**Request Body:** Telegram Bot API update

**Response:**
```json
{
  "ok": true
}
```

---

## Referral Endpoints

### Get Referral Statistics

**Endpoint:** `GET /referrals/stats`

**Authentication:** Required

**Response:**
```json
{
  "total_referrals": 5,
  "paid_referrals": 3,
  "pending_referrals": 2,
  "total_bonus_days": 21
}
```

---

### Get Referral Code

**Endpoint:** `GET /referrals/code`

**Authentication:** Required

**Response:**
```json
{
  "referral_code": "ABC123",
  "referral_url": "https://yourapp.com/register?ref=ABC123"
}
```

---

## VPN Config Endpoint

### Get VPN Configuration

**Endpoint:** `GET /vpn/{uuid}`

**Description:** Public endpoint for Happ app. Returns subscription info and VLESS links.

**Parameters:**
- `uuid` (string, path): Subscription XUI client UUID

**Response:**
```json
{
  "telegram_id": 123456789,
  "traffic_remaining_gb": 85,
  "expires_at": "2024-02-01T00:00:00+00:00",
  "device_limit": 1,
  "plan_name": "Solo",
  "servers": [
    {
      "name": "🇳🇱 NL-Amsterdam-01",
      "link": "vless://550e8400-e29b-41d4-a716-446655440000@195.154.1.1:443?...",
      "country": "Netherlands"
    }
  ],
  "subscription_link": "data:text/plain;base64,dmxlc3M6Ly8..."
}
```

---

## Admin Endpoints

All admin endpoints require `is_admin=true` on the user.

### List Users

**Endpoint:** `GET /admin/users`

**Authentication:** Required (Admin)

**Query Parameters:**
- `skip` (int, default=0)
- `limit` (int, default=100)

**Response:** Array of user objects

---

### Search Users

**Endpoint:** `GET /admin/users/search`

**Authentication:** Required (Admin)

**Query Parameters:**
- `query` (string, required): Search by username, first_name, or telegram_id
- `skip` (int, default=0)
- `limit` (int, default=100)

**Response:** Array of user objects

---

### Ban/Unban User

**Endpoint:** `POST /admin/users/{user_id}/ban`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "user_id": "user-001",
  "is_banned": true
}
```

**Response:** Updated user object

---

### Update User Balance

**Endpoint:** `POST /admin/users/{user_id}/balance`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "user_id": "user-001",
  "amount": "50.00",
  "reason": "Manual credit for promotion"
}
```

**Response:** Updated user object

---

### Create Server

**Endpoint:** `POST /admin/servers`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "NL-Amsterdam-01",
  "country_emoji": "🇳🇱",
  "country_name": "Netherlands",
  "host": "195.154.1.1",
  "port": 443,
  "panel_url": "https://xui.example.com",
  "panel_username": "admin",
  "panel_password": "secure_password",
  "inbound_id": 1,
  "bypass_ru_whitelist": false,
  "order_index": 1
}
```

**Response:** Server object with panel credentials

---

### Update Server

**Endpoint:** `PUT /admin/servers/{server_id}`

**Authentication:** Required (Admin)

**Request Body:** Partial server data (optional fields)

**Response:** Updated server object

---

### Delete Server

**Endpoint:** `DELETE /admin/servers/{server_id}`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "detail": "Server deleted"
}
```

---

### List Plan Prices

**Endpoint:** `GET /admin/plans`

**Authentication:** Required (Admin)

**Response:**
```json
[
  {
    "id": "plan-001",
    "plan_name": "Solo",
    "period_days": 30,
    "price_rub": "299.99",
    "created_at": "2024-01-01T00:00:00+00:00"
  }
]
```

---

### Create/Update Plan Price

**Endpoint:** `POST /admin/plans`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "plan_name": "Solo",
  "period_days": 30,
  "price_rub": "299.99"
}
```

**Response:** Plan price object

---

### Delete Plan Price

**Endpoint:** `DELETE /admin/plans/{plan_id}`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "detail": "Plan deleted"
}
```

---

### List Bot Texts

**Endpoint:** `GET /admin/bot-texts`

**Authentication:** Required (Admin)

**Response:**
```json
[
  {
    "id": "text-001",
    "key": "welcome_message",
    "value": "Welcome to our VPN service! 🎉",
    "description": "Message shown when user starts the bot",
    "created_at": "2024-01-01T00:00:00+00:00",
    "updated_at": "2024-01-01T00:00:00+00:00"
  }
]
```

---

### Create/Update Bot Text

**Endpoint:** `POST /admin/bot-texts`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "key": "welcome_message",
  "value": "Welcome to our VPN service! 🎉",
  "description": "Message shown when user starts the bot"
}
```

**Response:** Bot text object

---

### Update Bot Text

**Endpoint:** `PUT /admin/bot-texts/{text_id}`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "value": "Updated message",
  "description": "Updated description"
}
```

**Response:** Updated bot text object

---

### Delete Bot Text

**Endpoint:** `DELETE /admin/bot-texts/{text_id}`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "detail": "Bot text deleted"
}
```

---

### Create Broadcast

**Endpoint:** `POST /admin/broadcasts`

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "message": "Special offer: 50% off all plans this week!"
}
```

**Response:** Broadcast object

---

### Get System Statistics

**Endpoint:** `GET /admin/stats`

**Authentication:** Required (Admin)

**Response:**
```json
{
  "total_users": 1250,
  "banned_users": 5,
  "active_subscriptions": 450,
  "total_revenue": "135000.00",
  "pending_payments": 12,
  "completed_payments": 800
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this resource"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

Currently not implemented, but recommended for production.

## API Versioning

Current version: `v1` (in URL prefix `/api/v1`)

Future versions will be available at `/api/v2`, etc.

## Webhook Signature Verification

For YooKassa webhooks, verify the signature in the `X-Yookassa-Signature` header.

For Telegram webhooks, verify the bot token.

## Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** (HTTPOnly cookies or secure storage)
3. **Refresh tokens** before they expire
4. **Handle rate limits** gracefully
5. **Validate input** on client side
6. **Use pagination** for large datasets
7. **Cache responses** when possible
8. **Monitor API** performance and errors

---

## Support

For API issues, contact: api-support@vpnsystem.com
