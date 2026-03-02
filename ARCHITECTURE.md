# VPN Sales Bot - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      TELEGRAM USER                              │
│                    (Telegram Client)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    Telegram Bot API
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT (aiogram)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Dispatcher & Event Router                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │         Middleware Stack (Processing Layer)             │   │
│  ├─ Throttling Middleware (Rate Limiting)                 │   │
│  └─ Auth Middleware (Registration & Ban Check)            │   │
│                             │                                   │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │              Handler Routers (Logic Layer)              │   │
│  ├─ start.py           (Main menu)                         │   │
│  ├─ free_trial.py      (Trial activation)                  │   │
│  ├─ payment.py         (Payment flow)                      │   │
│  ├─ subscription.py    (Subscription management)           │   │
│  ├─ referral.py        (Referral program)                  │   │
│  ├─ cabinet.py         (Personal cabinet & devices)        │   │
│  ├─ admin.py           (Admin operations)                  │   │
│  ├─ instructions.py    (Connection instructions)           │   │
│  ├─ channel.py         (Channel link)                      │   │
│  ├─ support.py         (Support link)                      │   │
│  └─ notifications.py   (Notification system)               │   │
│                                                              │   │
│  ┌──────────────────────────┬──────────────────────────────┐   │
│  │      FSM State Management (State Layer)                 │   │
│  ├─ payment_states.py   (Payment & device states)          │   │
│  └─ admin_states.py     (Admin operation states)           │   │
│                          │                                   │   │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │       Keyboard Builders (UI Layer)                  │   │
│  ├─ main_menu.py        (7-option main menu)           │   │
│  ├─ payment_kb.py       (Payment flow keyboards)        │   │
│  ├─ subscription_kb.py  (Cabinet keyboards)             │   │
│  ├─ admin_kb.py         (Admin keyboards)               │   │
│  └─ inline_kb.py        (Utility keyboards)             │   │
│                                                           │   │
│  ┌──────────────────────┬────────────────────────────┐   │
│  │   API Client & Utilities (Integration Layer)      │   │
│  ├─ api_client.py  (35+ async API endpoints)         │   │
│  └─ formatters.py  (Text formatting utilities)       │   │
│                    │                                  │   │
└────────────────────┼──────────────────────────────────┘   │
                     │
     ┌───────────────┼───────────────┬──────────────┐
     │               │               │              │
     ▼               ▼               ▼              ▼
  Backend API    Redis FSM       Telegram      Celery/
  (Django/        Storage        Payments      Redis
   FastAPI)      (Sessions)      (Stars,       Tasks
                                  YooKassa)
```

## Data Flow Diagrams

### Free Trial Flow

```
User clicks "🎁 Бесплатный доступ"
    │
    ▼
free_trial handler
    │
    ├─ Check if already used (API)
    │   │
    │   ├─ Already used → Show error
    │   │
    │   └─ Not used → Continue
    │
    ├─ Activate trial (API)
    │
    └─ Show subscription link
        │
        └─ User opens link in Happ app
```

### Payment Flow

```
User clicks "💸 Оплатить тариф"
    │
    ▼
payment handler → Get plans (API)
    │
    ▼
User selects plan → Set state: waiting_plan_selection
    │
    ▼
User selects period (7d-12m) → Set state: waiting_period_selection
    │
    ▼
Create payment (API) → Get price & link
    │
    ▼
User selects payment method
    │
    ├─ Telegram Stars → send_invoice
    │   │
    │   └─ User pays → Confirm payment (API)
    │
    └─ YooKassa → Send link
        │
        └─ User pays → Backend webhook confirms
    │
    ▼
Show subscription link (VLESS config)
    │
    └─ User opens in Happ app
```

### Referral Registration

```
User opens link: /start ref_CODE
    │
    ▼
start handler
    │
    ├─ Extract referral code
    │
    ├─ Register user with ref code (API)
    │
    └─ Show main menu
        │
        └─ Later: User can view in "👥 Партнёрка"
```

### Personal Cabinet Flow

```
User clicks "👤 Личный кабинет"
    │
    ▼
cabinet handler
    │
    ├─ Get subscription (API)
    │
    ├─ Get user info (API)
    │
    └─ Display:
        ├─ Subscription status
        ├─ Plan info
        ├─ Expiration date
        ├─ Device count/limit
        └─ Manage devices button
    │
    ▼
User clicks "📱 Управление устройствами"
    │
    ├─ Get devices (API)
    │
    ├─ Show device list with delete buttons
    │
    └─ Show "Add device" button
        │
        ├─ User selects device type
        │
        ├─ Add device (API)
        │
        └─ Show config link
```

### Admin Operations

```
Admin clicks /admin
    │
    ▼
Check if admin (ADMIN_IDS)
    │
    ├─ Not admin → Deny access
    │
    └─ Admin → Show menu
        │
        ├─ Statistics → Get stats (API)
        │
        ├─ Ban user → Get ID → Get reason → Ban (API)
        │
        ├─ Add balance → Get ID → Get amount → Get reason → Add (API)
        │
        └─ Broadcast → Get message → Confirm → Send (API)
```

## Component Relationships

```
┌────────────────────────────────────────────┐
│           Configuration (config.py)        │
│  ├─ Telegram settings                      │
│  ├─ API settings                           │
│  ├─ Payment settings                       │
│  └─ Redis settings                         │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Loader (loader.py)                 │
│  ├─ Bot initialization                     │
│  ├─ Dispatcher setup                       │
│  └─ Redis FSM storage                      │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│         Main (main.py)                     │
│  ├─ Register middlewares                   │
│  ├─ Register handlers                      │
│  └─ Start polling                          │
└────────────┬───────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┐
    │                 │              │
    ▼                 ▼              ▼
Middlewares       Handlers        Keyboards
    │                 │              │
    ├─ throttling    ├─ start       ├─ main_menu
    └─ auth          ├─ free_trial  ├─ payment_kb
                     ├─ payment     ├─ subscription_kb
                     ├─ cabinet     ├─ admin_kb
                     ├─ admin       └─ inline_kb
                     ├─ referral
                     ├─ support
                     ├─ channel
                     ├─ instructions
                     └─ notifications
```

## State Machine Diagram

### Payment State Machine

```
START
    │
    ▼
waiting_plan_selection
    │
    ├─ User selects plan
    │
    ▼
waiting_period_selection
    │
    ├─ User selects period
    │
    ▼
waiting_payment_method
    │
    ├─ User selects: Stars or YooKassa
    │
    ▼
waiting_payment_completion
    │
    ├─ Payment confirmed
    │
    ▼
CLEAR (Payment done)
```

### Admin State Machine

```
START
    │
    ▼
waiting_admin_action (choose action)
    │
    ├─ Ban: waiting_ban_user_id → waiting_ban_reason → CLEAR
    ├─ Unban: waiting_ban_user_id → CLEAR
    ├─ Balance: waiting_add_balance_user_id → waiting_add_balance_amount → waiting_add_balance_reason → CLEAR
    └─ Broadcast: waiting_broadcast_message → waiting_broadcast_confirm → CLEAR
```

## Database Schema (Backend)

```
┌─────────────┐         ┌──────────────┐
│   USERS     │         │ SUBSCRIPTIONS│
├─────────────┤         ├──────────────┤
│ id          │◄────────│ user_id      │
│ telegram_id │         │ plan_id      │
│ username    │         │ expire_date  │
│ first_name  │         │ traffic_left │
│ is_banned   │         │ device_limit │
│ ban_reason  │         │ created_at   │
│ referral_by │         │ updated_at   │
│ created_at  │         └──────────────┘
│ updated_at  │
└─────────────┘         ┌──────────────┐
       │                │   DEVICES    │
       │                ├──────────────┤
       └────────────────│ user_id      │
                        │ server       │
                        │ config_data  │
                        │ added_date   │
                        └──────────────┘

       ┌─────────────────┐
       │    PAYMENTS     │
       ├─────────────────┤
       │ id              │
       │ user_id         │
       │ plan_id         │
       │ period_days     │
       │ amount          │
       │ status          │
       │ created_at      │
       │ paid_at         │
       └─────────────────┘
```

## API Integration Layer

```
┌──────────────────────────────────────┐
│         API Client (api_client.py)   │
│                                       │
│  Async httpx with connection pool    │
│                                       │
├────────────────────────────────────┤
│  User Endpoints (3)                │
│  ├─ register_user()                │
│  ├─ get_user()                     │
│  └─ check_ban()                    │
├────────────────────────────────────┤
│  Subscription Endpoints (4)        │
│  ├─ get_subscription()             │
│  ├─ get_subscription_plans()       │
│  ├─ create_payment_link()          │
│  └─ confirm_payment()              │
├────────────────────────────────────┤
│  Free Trial Endpoints (2)          │
│  ├─ activate_free_trial()          │
│  └─ check_free_trial_used()        │
├────────────────────────────────────┤
│  Device Endpoints (3)              │
│  ├─ get_user_devices()            │
│  ├─ add_device()                  │
│  └─ delete_device()               │
├────────────────────────────────────┤
│  Content Endpoints (2)             │
│  ├─ get_bot_text()                │
│  └─ get_instructions()            │
├────────────────────────────────────┤
│  Admin Endpoints (5)               │
│  ├─ ban_user()                    │
│  ├─ unban_user()                  │
│  ├─ add_balance()                 │
│  ├─ get_stats()                   │
│  └─ send_broadcast()              │
└────────────────────────────────────┘
         │
         ▼
    Backend API
```

## Notification Pipeline

```
Celery/Redis Queue
    │
    ├─ Scheduled task (24h before expiry)
    ├─ Scheduled task (12h before expiry)
    ├─ Scheduled task (1h before expiry)
    └─ Event-based task (subscription expired)
    │
    ▼
process_notification_task()
    │
    ├─ Extract notification data
    │
    ├─ Build message text
    │
    └─ Send via bot.send_message()
        │
        └─ User receives notification
```

## Security Layers

```
┌──────────────────────────┐
│   Incoming Update        │
│  (Message/CallbackQuery) │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Throttling Middleware   │
│  (Rate limit check)      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Auth Middleware         │
│  ├─ Auto-register user   │
│  ├─ Check ban status     │
│  └─ Validate user        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Handler Execution       │
│  ├─ Verify admin access  │
│  ├─ Check user state     │
│  └─ Process request      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  API Call (if needed)    │
│  ├─ Use API key          │
│  └─ HTTPS (production)   │
└─────────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────┐
│      Docker Container (bot)        │
│  ┌───────────────────────────────┐ │
│  │   Python 3.11 + aiogram       │ │
│  │   ├─ Bot code                 │ │
│  │   ├─ Handlers & keyboards     │ │
│  │   └─ Async event loop         │ │
│  └───────────────────────────────┘ │
└────────────────┬───────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐ ┌──────────┐ ┌──────────┐
│Redis   │ │ Backend  │ │ Telegram │
│FSM     │ │   API    │ │  Servers │
│Storage │ │(Django/  │ │ (Polling)│
│        │ │ FastAPI) │ │          │
└────────┘ └──────────┘ └──────────┘

Optional in production:
├─ Sentry (error tracking)
├─ Prometheus (metrics)
├─ ELK Stack (logging)
└─ CloudWatch (monitoring)
```

## Scaling Architecture

```
┌─────────────────────────────────────┐
│      Load Balancer (optional)       │
│   (for multiple bot instances)      │
└────────┬────────────┬───────────────┘
         │            │
         ▼            ▼
    ┌────────┐   ┌────────┐
    │Bot #1  │   │Bot #2  │
    │        │   │        │
    │Polling │   │Polling │
    └────┬───┘   └────┬───┘
         │            │
         └─────┬──────┘
               │
               ▼
        ┌──────────────┐
        │Shared Redis  │
        │(FSM Storage) │
        └──────────────┘
               │
               ▼
        ┌──────────────┐
        │ Backend API  │
        │(Database)    │
        └──────────────┘
```

## File Structure

```
bot/
├── __init__.py
├── main.py                 [Entry point]
├── config.py               [Configuration]
├── loader.py               [Bot setup]
│
├── handlers/
│   ├── __init__.py
│   ├── start.py            [Main menu]
│   ├── free_trial.py       [24h trial]
│   ├── payment.py          [Payment flow]
│   ├── subscription.py     [Subscription]
│   ├── referral.py         [Referral]
│   ├── cabinet.py          [Cabinet + devices]
│   ├── admin.py            [Admin panel]
│   ├── support.py          [Support]
│   ├── channel.py          [Channel]
│   ├── instructions.py     [Instructions]
│   └── notifications.py    [Notifications]
│
├── keyboards/
│   ├── __init__.py
│   ├── main_menu.py
│   ├── payment_kb.py
│   ├── subscription_kb.py
│   ├── admin_kb.py
│   └── inline_kb.py
│
├── states/
│   ├── __init__.py
│   ├── payment_states.py
│   └── admin_states.py
│
├── middlewares/
│   ├── __init__.py
│   ├── auth.py
│   └── throttling.py
│
└── utils/
    ├── __init__.py
    ├── api_client.py       [35+ endpoints]
    └── formatters.py       [Text formatting]
```

## Performance Considerations

```
User Request
    │
    ├─ Throttling check (O(1)) ✓ Fast
    │
    ├─ Auth check (API call) ⚠️ May be slow
    │   └─ Cached in Redis (recommended)
    │
    ├─ Handler execution
    │   ├─ State lookup (Redis O(1)) ✓ Fast
    │   ├─ API calls (network dependent) ⚠️
    │   └─ Keyboard generation (O(n)) ✓ Fast
    │
    └─ Response sent to user
```

## Error Handling Flow

```
Error Occurs
    │
    ├─ Catch in try-except
    │
    ├─ Log error with context
    │
    ├─ Check error type
    │   ├─ API error → Show user message
    │   ├─ Validation → Show input error
    │   └─ Unexpected → Show generic error
    │
    ├─ Send alert to user (if applicable)
    │
    └─ Continue normal operation
```

---

This architecture provides:
- ✅ **Modularity**: Clear separation of concerns
- ✅ **Scalability**: Distributed FSM storage, stateless handlers
- ✅ **Security**: Multiple validation layers
- ✅ **Performance**: Async throughout, connection pooling
- ✅ **Maintainability**: Clear structure, comprehensive documentation
