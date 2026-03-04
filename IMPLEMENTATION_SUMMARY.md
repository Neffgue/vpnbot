# VPN Bot Project - Implementation Summary

## Project Overview
This is a comprehensive Telegram VPN bot with web admin panel and backend API. The system manages user subscriptions, payments, device management, and broadcasts through a unified architecture.

---

## 1. PAYMENT SYSTEMS INTEGRATED

### Payment Methods Supported
- **Telegram Stars** (`pay_stars` callback)
  - Using native Telegram invoice system (XTR currency)
  - Integrated in `bot/handlers/payment.py` (lines 169-225)
  - Handles `pre_checkout_query` and `successful_payment` updates
  
- **YooKassa** (`pay_yookassa` callback)
  - Card payments (Visa/Mastercard/Мир)
  - СБП (System for Payments Between Banks)
  - Яндекс.Касса
  - Apple Pay, Google Pay
  - Integrated in `bot/handlers/payment.py` (lines 227-273)
  - Webhook endpoint: `POST /api/v1/payments/yookassa/webhook`

### Payment Flow Architecture
```
User selects "Buy Subscription" 
  → Plan Selection (Solo/Family)
  → Period Selection (7/30/90/180/365 days)
  → Payment Method Selection
  → Payment Processing (Stars or YooKassa)
  → Subscription Activation
```

### Backend Payment Processing
- **PaymentService** (`backend/services/payment_service.py`)
  - `create_payment()`: Create payment record with UUID
  - `mark_completed()`: Update status to "completed"
  - `mark_failed()`: Update status to "failed"
  - `get_user_payments()`: List user's payment history
  - `get_plan_price()`: Fetch pricing from DB
  
- **Payment Model** (`backend/models/payment.py`)
  - Fields: id, user_id, amount, currency, provider, provider_payment_id, status, plan_name, period_days, device_limit
  - Status values: pending, completed, failed, refunded
  - Timestamps: created_at, updated_at

### Admin Payment Management
- **API Endpoints** (`backend/api/v1/endpoints/admin.py`, lines 883-909)
  - `GET /api/v1/admin/payments` - List all payments with filtering
  - `GET /api/v1/admin/payments/{payment_id}` - Single payment details
  - `GET /api/v1/admin/users/{user_id}/payments` - User's payment history

---

## 2. SUBSCRIPTION MANAGEMENT

### Subscription Model
- **Subscription Model** (`backend/models/subscription.py`)
  - Fields: id, user_id, plan_name, period_days, device_limit, traffic_gb, expires_at, is_active
  - Notification flags: notified_24h, notified_12h, notified_1h, notified_0h, notified_3h_after_expiry
  - XUI Client UUID for VPN connection tracking
  - Many-to-many relationship with Servers

### Subscription Service
- **SubscriptionService** (`backend/services/subscription_service.py`)
  - `create_subscription()`: Create new subscription with all active servers
  - `get_active_user_subscription()`: Get current active subscription
  - `extend_subscription()`: Add days to existing subscription
  - `deactivate_subscription()`: Mark subscription as inactive
  - `get_expiring_subscriptions()`: Find subscriptions expiring within X hours
  - `count_active_subscriptions()`: Dashboard metric

### Subscription Lifecycle
1. **Creation**: Upon successful payment
2. **Active Period**: Until expires_at timestamp (with timezone handling)
3. **Expiry Notifications**: Triggered at 24h, 12h, 1h, 0h, and 3h after expiry
4. **Renewal**: User can extend through payment flow

### Bot Subscription Handlers
- **Handler** (`bot/handlers/subscription.py`)
  - `renew_subscription` (F.data == "renew_subscription"): Initiate renewal flow
  - `cancel_action` (F.data == "cancel"): Cancel and return to menu
  - Simple state management with FSM context

### Admin Subscription Management
- **API Endpoints** (`backend/api/v1/endpoints/admin.py`, lines 934-1001)
  - `GET /api/v1/admin/subscriptions` - List all subscriptions
  - `POST /api/v1/admin/subscriptions/{sub_id}/extend` - Add days (admin override)
  - `POST /api/v1/admin/subscriptions/{sub_id}/cancel` - Cancel subscription

---

## 3. ADMIN PANEL FEATURES

### Core Admin Endpoints

#### System Settings
- `GET /api/v1/admin/system-settings` - Retrieve bot token, webhook URL, admin credentials
- `PUT /api/v1/admin/system-settings` - Update system-level settings (persistent in DB)

#### Dashboard Statistics
- `GET /api/v1/admin/stats` - Returns:
  - total_users, active_subscriptions
  - revenue_today, revenue_month
  - active_servers, pending_payments
  - recent_activity (last 5 payments)
  - servers list

#### Bot Texts Management
- `GET /api/v1/admin/bot-texts` - Get all bot messages as dictionary
- `PUT /api/v1/admin/bot-texts/{key}` - Upsert single text
- `DELETE /api/v1/admin/bot-texts/{key}` - Delete text
- **Default texts**: welcome, free_trial_success, subscription_required, referral_header, etc.

#### Bot Buttons Management
- `GET /api/v1/admin/bot-buttons` - List all menu buttons
- `POST /api/v1/admin/bot-buttons` - Create new button
- `PUT /api/v1/admin/bot-buttons/{btn_id}` - Full update
- `PATCH /api/v1/admin/bot-buttons/{btn_id}` - Partial update (preserve other fields)
- `DELETE /api/v1/admin/bot-buttons/{btn_id}` - Delete button
- **Button structure**: text, callback_data, url, row, image_url

#### Bot Settings
- `GET /api/v1/admin/settings` - Get bot settings JSON
- `PUT /api/v1/admin/settings` - Save bot settings (support contact, channel URL, etc.)

#### Media Upload
- `POST /api/v1/admin/upload-image` - Upload image for bot use
  - Max 5MB, supports jpg/png/gif/webp
  - Returns full URL: `/static/uploads/{filename}`

#### Broadcasting
- **Text Broadcast**
  - `POST /api/v1/admin/broadcast` - Send text message to target users
  - Synchronous, sends via Telegram Bot API directly
  
- **Image Broadcast** (Asynchronous)
  - `POST /api/v1/admin/broadcast-image` (status 202 Accepted)
  - Accepts image + optional caption
  - Targets: "all", "active", "expired", "trial"
  - Uses BackgroundTasks for non-blocking execution
  - Respects Telegram rate limiting (30 msgs/sec with 0.04s delay)

#### User Management
- `GET /api/v1/admin/users` - List users with pagination
- `GET /api/v1/admin/users/{user_id}` - Get user details
- `GET /api/v1/admin/users/{user_id}/subscriptions` - User's subscriptions
- `GET /api/v1/admin/users/{user_id}/payments` - User's payments
- `GET /api/v1/admin/users/{user_id}/referrals` - User's referral earnings
- `POST /api/v1/admin/users/{user_id}/ban` - Ban user (with reason)
- `POST /api/v1/admin/users/{user_id}/unban` - Unban user
- `POST /api/v1/admin/users/{user_id}/add-days` - Add subscription days (admin override)

#### Plan Prices
- `GET /api/v1/admin/plans` - List all pricing plans
- `PUT /api/v1/admin/plans/{id}` - Update plan price

#### Instruction Steps (per device type)
- Get instruction steps for Windows/macOS/Android/iOS
- Upload images for each instruction step
- Image management for setup guides

### Cache Invalidation
- `_invalidate_bot_cache()` function in admin.py
  - Called after any data modification (PUT/POST/DELETE)
  - Invalidates Redis cache keys: "bot:buttons", "bot:texts", "bot:settings", "bot:plans"
  - Gracefully handles Redis unavailability with warnings

### Admin Authentication
- Uses `get_admin_user` dependency
- API key-based authentication
- All admin endpoints protected

---

## 4. BOT HANDLERS LIST

### Handler Files Structure
Location: `bot/handlers/` directory

| Handler | Purpose | Key Functions |
|---------|---------|---------------|
| **payment.py** | Payment flow orchestration | buy_subscription, select_plan, select_period, pay_with_stars, pay_with_yookassa |
| **subscription.py** | Subscription management | renew_subscription, cancel_action |
| **admin.py** | Admin commands | admin_command, ban_user, add_balance, broadcast, price management |
| **cabinet.py** | User personal cabinet | Show subscription status, manage devices |
| **channel.py** | Channel subscription check | Verify required channel membership |
| **free_trial.py** | Free trial activation | Activate 24-hour trial, check usage |
| **instructions.py** | Setup guides | Display device-specific instructions with images |
| **notifications.py** | Expiry reminders | Handle notification logic |
| **referral.py** | Referral program | Show referral code, track earnings |
| **start.py** | Bot startup | Initial greeting, user registration |
| **support.py** | Support contact | Show support information |

### Payment Handler Details (`bot/handlers/payment.py`, 393 lines)
- **Hardcoded Prices** (lines 55-67):
  ```python
  PLAN_PRICES = {
      "solo": {"name": "👤 Минимальный", "devices": 1, "prices": {7: 90, 30: 150, 90: 400, 180: 760, 365: 1450}},
      "family": {"name": "👨‍👩‍👧‍👦 Семейный", "devices": 5, "prices": {7: 150, 30: 250, 90: 650, 180: 1200, 365: 2300}},
  }
  ```
- **States Used**: PaymentStates (waiting_plan_selection, waiting_period_selection, waiting_payment_method)
- **Key Handlers**:
  - `buy_subscription_handler`: Show plans (Solo/Family)
  - `select_plan`: Show periods with prices
  - `select_period`: Show payment methods
  - `pay_with_stars`: Send Telegram invoice
  - `pay_with_yookassa`: Provide YooKassa link
  - Navigation handlers: back_to_plans, back_to_payment, back_to_periods

### Admin Handler Details (`bot/handlers/admin.py`, 948 lines)
- **Upload Directory**: `/home/neffgue313/vpnbot/static/uploads`
- **Core Features**:
  - User listing and banning/unbanning
  - Balance management (add funds with reason)
  - Broadcasting (text, photo, photo+caption)
  - Price management (select plan → enter new price)
  - Button image uploads
  - Instruction step image uploads (per device type)

---

## 5. KEYBOARD TYPES

### Keyboards Location: `bot/keyboards/` directory

#### Main Menu Keyboards
- **main_menu.py**
  - `get_main_menu()`: Standard user menu
  - `get_main_menu_with_admin()`: Admin variant with admin panel option

#### Payment Keyboards (`bot/keyboards/payment_kb.py`)
| Function | Purpose |
|----------|---------|
| `get_plan_keyboard()` | Dynamic plan selection (2 buttons/row) |
| `get_period_keyboard()` | Period selection (7/30/90/180/365 days) |
| `get_payment_method_keyboard()` | Telegram Stars vs YooKassa |
| `get_payment_confirmation_keyboard()` | Confirm payment with amount |
| `get_subscription_link_keyboard()` | Display subscription link with buttons |

#### Subscription Keyboards (`bot/keyboards/subscription_kb.py`)
| Function | Purpose |
|----------|---------|
| `get_cabinet_keyboard()` | Personal cabinet main menu (Devices + Back) |
| `get_subscription_keyboard()` | Show subscription status (Renew/Buy + Back) |
| `get_device_keyboard()` | List devices with delete buttons |
| `get_add_device_keyboard()` | Device type selection (Android, iOS, Windows, macOS, Linux, Android TV) |
| `get_device_confirmation_keyboard()` | Confirm device addition |

#### Admin Keyboards (`bot/keyboards/admin_kb.py`)
- `get_admin_menu()`: Admin panel main menu
- `get_admin_confirm_keyboard()`: Confirm/Cancel buttons
- `get_admin_back_keyboard()`: Back to admin menu

#### Other Keyboards
- **inline_kb.py**: Generic inline buttons
- **admin_kb.py**: Admin-specific layouts

---

## 6. WORKER/CELERY TASKS

### Celery Configuration
Location: `worker/` directory

#### Beat Schedule (`worker/beat_schedule.py`)
- Periodic tasks scheduled with celery-beat
- Task timing configuration for recurring jobs

#### Celery App (`worker/celery_app.py`)
- Celery instance initialization
- Redis/RabbitMQ broker configuration
- Task discovery setup

#### Notification Tasks (`worker/tasks/notifications.py`, 231 lines)

**Main Task**: `check_expiring_subscriptions()` (shared_task)
- Runs periodically to check for expiring subscriptions
- Checks at: 24h, 12h, 1h, 0h before expiry
- Also checks 3h after expiry for recovery reminder

**Notification Configuration**:
```python
notification_configs = [
    (24, '24h', 'notified_24h', '⏰ <b>Ваша VPN-подписка истекает через 24 часа</b>...'),
    (12, '12h', 'notified_12h', '⏰ <b>Ваша VPN-подписка истекает через 12 часов</b>...'),
    (1, '1h', 'notified_1h', '🔴 <b>Ваша VPN-подписка истекает через 1 час</b>...'),
    (0, '0h', 'notified_0h', '🚨 <b>Ваша VPN-подписка истекла!</b>...'),
]
```

**Helper Class**: `SubscriptionNotificationTask`
- `get_subscriptions_expiring_in()`: Query subscriptions by expiry window
- `mark_notification_sent()`: Update notification flags
- `send_telegram_message()`: Send via Telegram Bot API using httpx

**Features**:
- Timezone handling (МСК/UTC conversion)
- Rate limiting aware (respects Telegram API limits)
- Async/await pattern with asyncio
- Error logging and retry logic

#### Other Tasks
- **subscription_manager.py**: Subscription lifecycle management
- **health_check.py**: System health monitoring

---

## 7. BACKEND SERVICES

### Services Location: `backend/services/` directory

| Service | Purpose | Key Methods |
|---------|---------|------------|
| **subscription_service.py** | Manage subscriptions | create, extend, deactivate, get_expiring, count_active |
| **payment_service.py** | Handle payments | create, mark_completed, mark_failed, get_plan_price |
| **user_service.py** | User management | create, get, update, ban, search, get_all |
| **server_service.py** | VPN servers | CRUD operations, status checks |
| **referral_service.py** | Referral tracking | Track referrals, calculate bonuses |
| **notification_service.py** | Notifications | Send alerts (Telegram, email) |
| **xui_service.py** | XUI API calls | Create/delete VPN clients in XUI |
| **xui_service_mock.py** | XUI mocking | Test mode without real XUI |

### Key Service Patterns
- Async/await with SQLAlchemy AsyncSession
- Repository pattern for data access
- Single responsibility principle
- Logging at key operation points

---

## 8. DATA MODELS

### Models Location: `backend/models/` directory

#### User Model (`user.py`, 50 lines)
```python
Fields:
  - id (UUID, primary key)
  - telegram_id (BigInteger, unique)
  - username, first_name, email
  - referral_code (unique, 10 chars)
  - referred_by (FK to users.id)
  - balance (Decimal)
  - is_banned, is_admin, free_trial_used (Boolean flags)
  - created_at, updated_at (DateTime with timezone)
  
Relationships:
  - subscriptions (one-to-many)
  - payments (one-to-many)
  - referrals_given (one-to-many)
  - referrals_received (one-to-many)
```

#### Subscription Model (`subscription.py`, 66 lines)
```python
Fields:
  - id (UUID)
  - user_id (FK to users.id)
  - plan_name (string: Solo, Family, Trial)
  - period_days, device_limit, traffic_gb (integers)
  - expires_at (DateTime, indexed)
  - is_active (Boolean, indexed)
  - xui_client_uuid (UUID for VPN client)
  - Notification flags: notified_24h, notified_12h, notified_1h, notified_0h, notified_3h_after_expiry
  - created_at, updated_at

Relationships:
  - user (many-to-one)
  - servers (many-to-many via subscription_server_association)
```

#### Payment Model (`payment.py`, 31 lines)
```python
Fields:
  - id (UUID)
  - user_id (FK)
  - amount (Numeric 12,2)
  - currency (string: RUB)
  - provider (string: telegram_stars, yookassa)
  - provider_payment_id (unique, indexed)
  - status (string: pending, completed, failed, refunded)
  - plan_name, period_days, device_limit
  - created_at, updated_at

Relationships:
  - user (many-to-one)
```

#### Config Models (`config.py`)
- **PlanPrice**: Plan pricing information
- **BotText**: Key-value store for bot texts and settings
- **Broadcast**: Broadcast message records

#### Referral Model (`referral.py`)
- Track referral relationships
- Store bonus days and payment status

#### Server Model (`server.py`)
- VPN server information
- Connection details and status

---

## 9. BOT STATES

### FSM States Location: `bot/states/` directory

#### Payment States (`payment_states.py`)
```python
PaymentStates:
  - waiting_plan_selection
  - waiting_period_selection
  - waiting_payment_confirmation
  - waiting_payment_method
  - waiting_payment_completion

SubscriptionStates:
  - waiting_subscription_action
  - waiting_renewal

DeviceStates:
  - waiting_device_type
  - waiting_device_confirmation
  - waiting_device_deletion

EmailStates:
  - waiting_email
```

#### Admin States (`admin_states.py`)
```python
AdminStates:
  - waiting_ban_user_id
  - waiting_ban_reason
  - waiting_add_balance_user_id
  - waiting_add_balance_amount
  - waiting_add_balance_reason
  - waiting_broadcast_message
  - waiting_broadcast_confirm
  - waiting_price_amount
  - waiting_btn_image_photo
  - waiting_instr_step_photo
```

---

## 10. ARCHITECTURE PATTERNS & DESIGN

### Key Architectural Decisions

1. **Async/Await Throughout**
   - FastAPI async endpoints
   - SQLAlchemy AsyncSession
   - Aiogram async handlers
   - Celery async tasks

2. **Repository Pattern**
   - Data access abstraction
   - Located in `backend/repositories/`
   - Base repository with CRUD operations
   - Specific repositories for each model

3. **Service Layer**
   - Business logic isolation
   - Dependencies injected via constructor
   - Logging at operation level
   - Transaction handling

4. **FSM State Management**
   - Aiogram FSM context for bot flows
   - Clear state transitions
   - Admin states for interactive commands

5. **Configuration Management**
   - `backend/config.py` for settings
   - Environment variables with defaults
   - Bot config via `bot/config.py`

6. **Cache Invalidation**
   - Redis cache for bot data
   - Cache invalidation on admin updates
   - Graceful degradation if Redis unavailable

7. **Background Tasks**
   - Celery for periodic notification checks
   - FastAPI BackgroundTasks for broadcasts
   - Non-blocking image distribution

### Database Schema
- PostgreSQL (async driver: asyncpg)
- Alembic migrations in `backend/alembic/`
- Migrations: initial schema, email to users, notification fields

### Authentication & Security
- API key authentication for admin endpoints
- `get_admin_user` dependency in `backend/api/deps.py`
- User context injection for authorization

---

## CURRENT IMPLEMENTATION STATUS

### ✅ Fully Implemented
- Basic payment flow (Telegram Stars, YooKassa)
- User management and subscription lifecycle
- Admin panel with CRUD operations
- Bot handlers for all main flows
- Notification system (Celery task)
- Image upload and broadcast system
- Referral program structure
- Free trial system
- Device management framework

### ⚠️ Partially/Needs Refinement
- Hardcoded prices in payment handler (should be dynamic from DB)
- Image static file serving (Docker volume issues mentioned in AGENTS.md)
- Exception handling (needs global error handlers per AGENTS.md)
- Database transaction safety (needs explicit rollback handling)
- Bot cache invalidation (Redis optional dependency)

### 🔧 Architectural Debt (per AGENTS.md)
1. 500 errors during CRUD operations (need global exception handlers)
2. Connection reset on large broadcasts (solved with 202 Accepted pattern)
3. Bot-DB synchronization (need dynamic data fetching)
4. Hardcoded configurations in bot (need DB-driven generation)
5. Static file serving issues (need Docker volumes fix)

---

## SUMMARY STATISTICS

- **Total API Endpoints**: 50+ (admin, auth, payments, subscriptions, users, servers)
- **Handler Functions**: 11 separate handler modules in bot
- **Database Models**: 6 core models (User, Subscription, Payment, Server, Referral, Config)
- **Celery Tasks**: 3+ background job types
- **Keyboard Types**: 7 different keyboard layouts
- **FSM States**: 20+ state definitions
- **Admin Features**: System settings, stats, texts, buttons, broadcasts, user mgmt, pricing
- **Payment Methods**: 2 integrated (Telegram Stars, YooKassa)
- **Subscription Plans**: 2 tiers (Solo 1-device, Family 5-device)
- **Period Options**: 5 (7, 30, 90, 180, 365 days)
