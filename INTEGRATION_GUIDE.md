# Integration Guide

This guide explains how to integrate the VPN Sales Bot with your backend services.

## Table of Contents
1. [API Integration](#api-integration)
2. [Payment Integration](#payment-integration)
3. [Notification System](#notification-system)
4. [Database Schema](#database-schema)
5. [Testing](#testing)

## API Integration

### Required API Endpoints

The bot requires your backend to implement the following endpoints:

#### User Management

**Register User**
```
POST /api/users/register
Content-Type: application/json

{
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "referral_code": "ref_optional"
}

Response:
{
  "success": true,
  "user_id": 1,
  "telegram_id": 123456789
}
```

**Get User Info**
```
GET /api/users/{user_id}

Response:
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "is_banned": false
}
```

**Check Ban Status**
```
GET /api/users/{user_id}/ban-status

Response:
{
  "is_banned": false,
  "reason": ""
}
```

#### Subscriptions

**Get Active Subscription**
```
GET /api/users/{user_id}/subscription

Response:
{
  "id": 1,
  "plan_id": "family",
  "plan_name": "Семейный",
  "plan_type": "family",
  "expire_date": "2024-12-31T23:59:59Z",
  "traffic_remaining": 1099511627776,
  "device_limit": 5,
  "devices_count": 2
}
```

**Get Available Plans**
```
GET /api/subscriptions/plans

Response:
{
  "plans": [
    {
      "id": "solo",
      "name": "Соло",
      "description": "VPN для одного устройства",
      "price": 199.99,
      "features": ["1 устройство", "Безлимитный трафик"]
    },
    {
      "id": "family",
      "name": "Семейный",
      "description": "VPN для 5 устройств",
      "price": 399.99,
      "features": ["5 устройств", "Безлимитный трафик"]
    }
  ]
}
```

**Create Payment**
```
POST /api/users/{user_id}/create-payment
Content-Type: application/json

{
  "plan_id": "family",
  "period_days": 30,
  "payment_method": "combined"
}

Response:
{
  "success": true,
  "payment_id": "pay_123456",
  "yookassa_link": "https://yookassa.ru/payments/...",
  "invoice_payload": "vpn_sub_123456_30"
}
```

**Confirm Payment**
```
POST /api/users/{user_id}/confirm-payment
Content-Type: application/json

{
  "payment_id": "pay_123456"
}

Response:
{
  "success": true,
  "subscription_link": "vless://user@server.com:443?..."
}
```

#### Free Trial

**Activate Free Trial**
```
POST /api/users/{user_id}/free-trial

Response:
{
  "success": true,
  "subscription_link": "vless://trial@server.com:443?...",
  "expires_in_hours": 24
}
```

**Check Free Trial Status**
```
GET /api/users/{user_id}/free-trial-status

Response:
{
  "already_used": false,
  "available": true
}
```

#### Referral Program

**Get Referral Info**
```
GET /api/users/{user_id}/referral

Response:
{
  "referral_link": "https://t.me/bot?start=ref_USER_ID",
  "referrals_count": 5,
  "bonus_days": 10,
  "bonus_balance": 300.00
}
```

#### Device Management

**Get User Devices**
```
GET /api/users/{user_id}/devices

Response:
{
  "devices": [
    {
      "id": "device_1",
      "server": "US-1",
      "added_date": "2024-01-01T00:00:00Z",
      "config_key": "vless_config_..."
    }
  ]
}
```

**Add Device**
```
POST /api/users/{user_id}/devices
Content-Type: application/json

{
  "device_name": "iPhone"
}

Response:
{
  "success": true,
  "device_id": "device_123",
  "subscription_link": "vless://..."
}
```

**Delete Device**
```
DELETE /api/users/{user_id}/devices/{device_id}

Response:
{
  "success": true
}
```

#### Content & Settings

**Get Bot Texts**
```
GET /api/bot-texts/{key}?language=ru

Response:
{
  "text": "Welcome to VPN Bot!"
}
```

**Get Instructions**
```
GET /api/instructions

Response:
{
  "success": true,
  "instructions": [
    {
      "title": "Step 1",
      "content": "Description",
      "image_url": "https://..."
    }
  ]
}
```

#### Admin Operations

**Ban User**
```
POST /api/admin/users/{user_id}/ban
Authorization: Bearer API_KEY
Content-Type: application/json

{
  "reason": "Violation of terms"
}

Response:
{
  "success": true
}
```

**Unban User**
```
POST /api/admin/users/{user_id}/unban
Authorization: Bearer API_KEY

Response:
{
  "success": true
}
```

**Add Balance**
```
POST /api/admin/users/{user_id}/add-balance
Authorization: Bearer API_KEY
Content-Type: application/json

{
  "amount": 100.00,
  "reason": "Admin credit"
}

Response:
{
  "success": true
}
```

**Get Statistics**
```
GET /api/admin/stats
Authorization: Bearer API_KEY

Response:
{
  "total_users": 1250,
  "active_subscriptions": 890,
  "total_revenue": 150000.00,
  "monthly_revenue": 25000.00,
  "banned_users": 15,
  "free_trials_used": 340,
  "active_referrals": 120
}
```

**Send Broadcast**
```
POST /api/admin/broadcast
Authorization: Bearer API_KEY
Content-Type: application/json

{
  "message": "Message text",
  "user_ids": [123, 456]  // Optional, null for all users
}

Response:
{
  "success": true,
  "sent_count": 1000
}
```

## Payment Integration

### Telegram Stars

The bot uses `send_invoice` with empty provider token for Telegram Stars.

```python
prices = [LabeledPrice(label="VPN Subscription", amount=price_in_cents)]
await bot.send_invoice(
    chat_id=user_id,
    title="VPN Subscription",
    description="7 days access",
    payload="payload_data",
    provider_token="",  # Empty for Telegram Stars
    currency="XTR",
    prices=prices
)
```

Successful payment is confirmed via `pre_checkout_query` and `successful_payment` updates.

### YooKassa

The bot opens a payment link provided by your backend. The payment flow:

1. Bot calls `POST /create-payment` endpoint
2. Backend generates YooKassa payment link
3. Bot shows link to user
4. User opens link and completes payment
5. Backend calls bot webhook to confirm payment (optional)

## Notification System

### Sending Notifications from Backend

Your backend can send notifications to users via Redis/Celery:

```python
# From your backend task
from bot.handlers.notifications import process_notification_task

task_data = {
    "user_id": 123456,
    "type": "subscription_expiry_24h",
    "plan_name": "Семейный",
    "expire_date": "2024-01-15",
    "days_remaining": 1
}

await process_notification_task(bot, task_data)
```

### Notification Types

- `subscription_expiry_24h` - 24 hours before expiry
- `subscription_expiry_12h` - 12 hours before expiry
- `subscription_expiry_1h` - 1 hour before expiry
- `subscription_expired` - Subscription expired
- `subscription_expired_3h` - 3 hours after expiry
- `free_trial_expiry_24h` - Free trial expiring soon
- `referral_bonus` - New referral bonus
- `balance_added` - Balance added by admin
- `broadcast` - Admin broadcast message

### Setup Celery Beat Tasks

Example Celery configuration:

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('vpn_backend')

app.conf.beat_schedule = {
    'notify-expiry-24h': {
        'task': 'tasks.notify_subscription_expiry_24h',
        'schedule': crontab(minute=0, hour='*/1'),  # Every hour
    },
    'notify-expiry-12h': {
        'task': 'tasks.notify_subscription_expiry_12h',
        'schedule': crontab(minute=0, hour='*/1'),
    },
    'notify-expiry-1h': {
        'task': 'tasks.notify_subscription_expiry_1h',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

## Database Schema

Minimum required database tables:

### Users
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    is_banned BOOLEAN DEFAULT false,
    ban_reason TEXT,
    referral_code VARCHAR(50) UNIQUE,
    referred_by_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Subscriptions
```sql
CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    plan_id VARCHAR(50),
    plan_name VARCHAR(255),
    expire_date TIMESTAMP,
    traffic_remaining BIGINT,
    device_limit INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Devices
```sql
CREATE TABLE devices (
    id VARCHAR(50) PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    device_name VARCHAR(255),
    server VARCHAR(100),
    config_data TEXT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Payments
```sql
CREATE TABLE payments (
    id VARCHAR(100) PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    plan_id VARCHAR(50),
    period_days INT,
    amount DECIMAL(10, 2),
    currency VARCHAR(3),
    payment_method VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP
);
```

## Testing

### Using Mock API

For testing without a backend, use the mock client in `dev_config.py`:

```python
from dev_config import MockAPIClient
# Replace APIClient with MockAPIClient in handlers
```

### Test Scenarios

1. **User Registration**: `/start` command
2. **Free Trial**: Click "🎁 Бесплатный доступ"
3. **Payment Flow**: 
   - Click "💸 Оплатить тариф"
   - Select plan and period
   - Choose payment method
4. **Referral**: `/start ref_CODE` with referral code
5. **Admin**: `/admin` command (if user is in ADMIN_IDS)

### Testing Payments

**Telegram Stars**: 
- Test mode payments with test bots
- Use `@BotFather` for test environment

**YooKassa**:
- Use YooKassa test cards
- See: https://yookassa.ru/developers/testing

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure valid `TELEGRAM_BOT_TOKEN`
- [ ] Set real admin IDs in `ADMIN_IDS`
- [ ] Configure backend `API_BASE_URL` and `API_KEY`
- [ ] Setup Redis (production instance)
- [ ] Configure YooKassa credentials
- [ ] Setup HTTPS for webhooks
- [ ] Enable Celery beat for notifications
- [ ] Configure logging and monitoring
- [ ] Test all payment methods
- [ ] Test notifications system
- [ ] Load test with production data

## Troubleshooting

### Common Issues

**400 Bad Request from API**
- Check JSON format matches expected schema
- Verify required fields are present
- Check Content-Type header

**401 Unauthorized**
- Verify API_KEY is correct
- Check Authorization header format

**502 Bad Gateway**
- Verify API_BASE_URL is correct
- Check backend service is running
- Check network connectivity

**Bot not responding**
- Check logs for errors
- Verify Redis connection
- Check Telegram token validity

## Support

For issues or questions:
1. Check logs for error messages
2. Verify API endpoint responses
3. Test with `curl` or Postman
4. Review this integration guide
5. Contact support team
