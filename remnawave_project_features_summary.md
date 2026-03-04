# Remnawave Bedolaga Telegram Bot - Complete Features Summary

## 🎯 Project Overview
A **full-featured VPN subscription management bot** for Telegram that integrates with the Remnawave VPN panel. Handles automated user registration, subscription sales, payments, analytics, and admin operations. Built with FastAPI, AsyncIO, PostgreSQL, and Redis.

---

## 1. 💳 Payment Systems & Providers

### Integrated Payment Providers (14 total)

| Provider | Type | Status |
|----------|------|--------|
| **Telegram Stars** | Native | ✅ Fully integrated |
| **Tribute** | Crypto/Fiat | ✅ Fully integrated |
| **CryptoBot** | Crypto | ✅ Fully integrated |
| **Heleket** | Fiat (RU) | ✅ Fully integrated |
| **YooKassa** | СБП + Cards | ✅ Fully integrated |
| **MulenPay** | СБП + Cards | ✅ Fully integrated |
| **Platega** | Cards + СБП | ✅ Fully integrated |
| **WATA** | Payments | ✅ Fully integrated |
| **Freekassa** | NSPK СБП + Cards | ✅ Fully integrated |
| **CloudPayments** | Cards + СБП | ✅ Fully integrated |
| **Pal24** | Payment Gateway | ✅ Fully integrated |
| **Kassa AI** | Payment Gateway | ✅ Fully integrated |
| **Cryptobot** | Crypto | ✅ Fully integrated |
| **PayPalych** | СБП + Cards | ✅ (via integration) |

### Payment Processing Features
- **WebHook verification** for all major providers
- **Payment status tracking** (pending → confirmed → completed)
- **Balance top-up** system with auto-purchase capability
- **Trial activation charge** (optional paid trial)
- **Payment verification service** for reconciliation
- **Payment logger & monitoring**
- **Automatic subscription purchase** after balance top-up
- **Email receipts** for payments
- **Multiple currency support** with conversion utilities

**Key Services:**
- `payment_service.py` - Core payment orchestration
- `payment_verification_service.py` - Async payment verification
- `payment_method_config_service.py` - Payment method display config
- Individual provider services (yookassa_service.py, cryptobot_service.py, etc.)

---

## 2. 📱 Subscription Management

### Subscription Types & Features
- **Paid subscriptions** - Recurring or one-time
- **Trial subscriptions** - Free trial with optional activation charge
- **Auto-renewal** - Automatic subscription extension via balance
- **Manual renewal** - User-initiated extension
- **Subscription conversion** - Trial → Paid conversion tracking
- **Subscription events** - Lifecycle event tracking

### Subscription Configuration
- **Duration options** - 14 days to 1 year (configurable)
- **Traffic limits** - 5GB to unlimited (fixed or user-selected)
- **Device limits** - 1 to unlimited devices
- **Device tracking** - HWID-based device management
- **Server/Squad selection** - Mandatory or optional server choice
- **Multi-server support** - User can select multiple server squads

### Tariff System
- **Fixed tariffs** - Pre-configured pricing tiers
- **Dynamic pricing** - Configurable prices per period/traffic combo
- **Promo group filtering** - Tariffs visible only to specific user groups
- **Payment method filtering** - Show tariffs based on available payment methods
- **Trial access periods** - Temporary subscription access without charge

### Traffic Management
- **Traffic purchase** - Standalone traffic add-ons
- **Traffic monitoring** - Real-time usage tracking (fast + daily checks)
- **Traffic limits** - Hard stop or soft warning
- **Traffic reset strategies** - No reset, daily, weekly, monthly
- **Traffic notifications** - Alert on threshold breach
- **Lifetime traffic tracking**

### Subscription Notifications
- **Expiration warnings** - 3 days, 1 day before expiry
- **Expired notifications** - Immediate notification
- **Daily debit notifications** - For daily-billed subscriptions
- **Traffic warning notifications**
- **Renewal success notifications**
- **Multi-channel delivery** - Telegram, Email, WebSocket (Cabinet)

**Key Services:**
- `subscription_service.py` - Core subscription logic
- `subscription_purchase_service.py` - Purchase flow orchestration
- `subscription_auto_purchase_service.py` - Auto-renewal from balance
- `subscription_renewal_service.py` - Renewal pricing & processing
- `subscription_checkout_service.py` - Cart/draft persistence
- `traffic_monitoring_service.py` - Real-time & daily checks
- `trial_activation_service.py` - Trial management with optional charge

---

## 3. ⚙️ Admin Features (Web Cabinet Routes)

### Admin Panel Capabilities (47+ routes)

#### **User Management**
- `admin_users.py` - CRUD user operations, bulk actions
- `admin_traffic.py` - Monitor, adjust user traffic
- User blocking/blacklisting
- User message broadcasting

#### **Subscription Admin**
- `admin_subscriptions.py` - View/edit user subscriptions
- `admin_tariffs.py` - Create/edit tariff plans
- `admin_trials.py` - Trial settings, activation history
- `admin_channels.py` - Required channel setup

#### **Payment & Financial**
- `admin_payments.py` - Payment history, manual adjustments
- `admin_payment_methods.py` - Enable/disable/configure providers
- `admin_withdrawals.py` - Partner withdrawal requests
- Transaction ledger
- Sales statistics & revenue tracking

#### **Content & Communications**
- `admin_broadcasts.py` - Send messages to user groups (Telegram/Email)
- `admin_pinned_messages.py` - Sticky messages in menu
- `admin_welcome_text.py` - Customize welcome messages
- `admin_email_templates.py` - Email template customization
- `admin_policies.py` - Terms of service, privacy policy, rules

#### **Gamification & Marketing**
- `admin_contests.py` + `admin_daily_contests.py` - Contest creation & management
- `admin_wheel.py` - Fortune wheel configuration & prizes
- `admin_polls.py` - Poll creation & distribution
- `admin_campaigns.py` - Advertising campaign bonus management
- `admin_promo_offers.py` - Discount offer templates
- `admin_promocodes.py` - Promo code generation & management
- `admin_promo_groups.py` - User group targeting

#### **Remnawave Integration**
- `admin_remnawave.py` - Panel sync, server management
- `admin_servers.py` - Server squad configuration
- `admin_traffic.py` - Traffic monitoring & alerts

#### **System & Security**
- `admin_stats.py` - Revenue, user growth, engagement metrics
- `admin_sales_stats.py` - Detailed sales analytics
- `admin_audit_log.py` - Admin action logging
- `admin_roles.py` - RBAC (Role-Based Access Control)
- `admin_blacklist.py` / `admin_blocked_users.py` - User blocking
- `admin_bulk_ban.py` - Mass user banning
- `admin_ban_system.py` - Integration with BedolagaBan system

#### **System Configuration**
- `admin_settings.py` - Global bot settings
- `admin_maintenance.py` - Maintenance mode toggle
- `admin_updates.py` - Bot version management
- `admin_button_styles.py` - Custom button styling
- `admin_apps.py` - App configuration
- `admin_tickets.py` - Support ticket management

#### **Analytics & Monitoring**
- `admin_monitoring.py` - System health checks
- `admin_reports.py` - Custom reports
- System logs with rotation

#### **Partner System**
- `admin_partners.py` - Partner management
- `admin_withdrawals.py` - Withdrawal request handling

### RBAC (Role-Based Access Control)
- `admin_roles.py` - Define custom admin roles
- `access_policy.py` - Fine-grained permissions
- Audit logging for admin actions

---

## 4. 🎮 Bot UX Features (User-Facing)

### Referral Program
- **Direct referral links** - Unique referral code per user
- **Commission structure** - Configurable referral bonus %
- **Multi-tier earnings** - Bonus on referral purchases
- **Withdrawal system** - Convert earnings to balance or bank account
- **Referral contests** - Special bonus periods with leaderboards
- **QR codes** - Generate referral QR codes
- **Referral diagnostics** - Debug referral attribution
- **Email-only user support** - Referrals for cabinet-only users

**Key Services:**
- `referral_service.py` - Referral earning & attribution
- `referral_withdrawal_service.py` - Withdraw referral balance
- `referral_contest_service.py` - Contest mechanics

### Contests & Games
- **Daily contests** - Simple daily games
- **Referral contests** - Leaderboard-based contests with prizes
- **Contest attempts** - Track user participation
- **Customizable rules** - Configure contest mechanics
- **Admin scheduling** - Control contest periods
- **Prize distribution** - Auto-award prizes to winners

**Key Services:**
- `contest_rotation_service.py` - Auto-rotate contests
- `attempt_service.py` - Track user attempts
- `games.py` - Game mechanics (lottery, slots, etc.)

### Wheel of Fortune
- **Fortune wheel spins** - Chance to win prizes
- **Prize configuration** - Admin-defined prize pool
- **Payment methods** - Spin via Stars or subscription days
- **Probability system** - Weighted prize selection
- **Prize types** - Balance, subscription days, promo codes
- **Spin animations** - Telegram animation support
- **Statistics** - Track spins and wins

**Key Services:**
- `wheel_service.py` - Core wheel mechanics

### Promo System
- **Promo codes** - Discount codes (% or fixed amount)
- **Promo groups** - User segment targeting
- **Promo offers** - Template-based discount offers
- **Discount offers** - Automatic upsell offers
- **Base discounts** - Per-group baseline discounts
- **Promo code logs** - Usage tracking
- **Rate limiting** - Prevent code spam

**Key Services:**
- `promocode_service.py` - Code validation & redemption
- `promo_offer_service.py` - Offer management & application
- `promo_group_assignment.py` - User group assignment

### Polls & Surveys
- **Multi-question polls** - Complex survey support
- **Multiple choice answers**
- **User responses tracking**
- **Poll rewards** - Optional reward for participation
- **Result viewing** - Admin dashboard for responses
- **Batch sending** - Send to user groups

**Key Services:**
- `poll_service.py` - Poll creation & delivery

### Pinned Messages
- **Sticky messages** - Display in menu persistently
- **Admin-configurable** - Update content anytime
- **Media support** - Include images
- **Button support** - Action buttons in pinned message

**Key Services:**
- `pinned_message_service.py`

### Required Channels
- **Subscription check** - Verify user joined required channel
- **Per-feature requirements** - Different channels per feature
- **Leave notifications** - Monitor if user leaves
- **Grace periods** - Configurable delay before enforcement
- **Action on leave** - Suspend subscription or notify

**Key Services:**
- `channel_subscription_service.py` - Verification & caching

### Support Tickets (Support/Help)
- **Create tickets** - User initiates support request
- **Ticket management** - Admin view/respond
- **Message threading** - Multi-message conversations
- **Admin notifications** - Webhook alerts on new tickets
- **Status tracking** - Open, closed, resolved
- **Email notifications** - Support team alerts

**Key Services:**
- `ticket_notifications.py` - Admin notifications

### User Messages
- **Broadcast messages** - Send to filtered user groups
- **Email broadcasts** - Also send via email
- **Progress tracking** - Monitor broadcast status
- **Pause/resume** - Control broadcast execution
- **Recipient filtering** - By user status, subscription, region

**Key Services:**
- `broadcast_service.py` - Message distribution

### Menu & Navigation
- **Dynamic menu layout** - Customizable button layout
- **Menu history** - Track user navigation
- **Button stats** - Usage analytics per button
- **Mini-app integration** - WebApp buttons
- **Main menu button** - Custom main menu button

**Key Services:**
- `menu_layout_service.py` - Menu structure management

### Notifications System
- **Multi-channel delivery** - Telegram, Email, WebSocket
- **Notification types** - Custom event triggers
- **User preferences** - Control notification receipt
- **Delivery logging** - Track sent notifications
- **Admin notifications** - Webhook alerts for admin events

**Key Services:**
- `notification_delivery_service.py` - Unified delivery
- `admin_notification_service.py` - Admin alerts

---

## 5. 🖥️ Cabinet / Web Mini-App Features

### User Cabinet Features (48+ routes)

#### **Authentication**
- `auth.py` - JWT-based auth + refresh tokens
- `oauth.py` - OAuth provider integration
- Email verification
- Password reset flow
- Session management
- Cookie-based admin auth (from Remnawave panel)

#### **Subscription Management**
- `subscription.py` - View active subscriptions
- Purchase new subscriptions
- Renew subscriptions
- Change subscription settings
- Auto-pay configuration
- Subscription history

#### **Balance & Top-Up**
- `balance.py` - Display current balance
- Top-up balance via payment methods
- Transaction history
- Auto-purchase on balance top-up

#### **User Profile**
- `info.py` - View profile, settings
- `branding.py` - Custom branding
- Language selection
- Account settings

#### **Content Access**
- `tickets.py` - Support tickets
- `polls.py` - Participate in polls
- `contests.py` - Contest participation
- `wheel.py` - Fortune wheel spins
- `promo.py` - Promo code redemption
- `promocode.py` - Bulk promo code generation

#### **Referral System**
- `referral.py` - Referral link & stats
- `partner_application.py` - Apply for partnership
- Earnings tracking
- Withdrawal requests
- `withdrawal.py` - Manage withdrawals

#### **Admin Routes (Cabinet Admin Panel)**
- 40+ admin routes for full system configuration
- Real-time WebSocket for live updates
- Media upload & management
- Server management
- Payment method config
- System settings

#### **API Features**
- `tickets.py` - Ticket creation/update
- `notifications.py` - Notification preferences
- `websocket.py` - Real-time updates
- `media.py` - Media upload/download
- `admin_apps.py` - Application management

**Key Architecture:**
- JWT + Refresh token flow
- FastAPI async routes
- WebSocket for real-time updates
- Email templates for notifications
- Multi-language support (ru, en, uk, fa, zh)

---

## 6. 🔔 Notification System

### Notification Events (Built-in triggers)

| Event | Channels | Details |
|-------|----------|---------|
| **Trial activated** | Telegram, Email, WebSocket | User claims free trial |
| **Subscription purchased** | Telegram, Email, WebSocket | New paid subscription |
| **Trial → Paid conversion** | Telegram, Email, WebSocket | Trial expired, converted to paid |
| **Subscription renewed** | Telegram, Email, WebSocket | Auto or manual renewal |
| **Subscription expiring soon** | Telegram, Email, WebSocket | 3 days, 1 day warnings |
| **Subscription expired** | Telegram, Email, WebSocket | Subscription end-of-life |
| **Balance topped up** | Telegram, Email, WebSocket | Payment confirmed |
| **Daily subscription debit** | Telegram, Email, WebSocket | Daily subscription charge |
| **Referral bonus earned** | Telegram, Email, WebSocket | Referral purchase detected |
| **Traffic limit warning** | Telegram, Email, WebSocket | 80% of traffic used |
| **Traffic exceeded** | Telegram, Email, WebSocket | Hard limit reached |
| **Maintenance mode on/off** | Telegram (admin) | System maintenance alerts |
| **Bot updated** | Telegram (admin) | Version change notifications |
| **New ticket created** | Email (support team) | Support request alert |
| **Ban system alert** | Email (admin) | User ban detection |

### Delivery Channels
1. **Telegram** - Direct message to user's bot chat
2. **Email** - HTML/plain text via SMTP
3. **WebSocket** - Real-time cabinet notification
4. **Admin topics** - Internal admin notifications via Telegram

**Key Services:**
- `notification_delivery_service.py` - Core delivery
- `admin_notification_service.py` - Admin alerts
- `notification_settings_service.py` - User preferences
- Email templates (customizable)

---

## 7. 🌐 External Integrations

### Remnawave VPN Panel API
- **User sync** - Create/update panel users
- **Subscription sync** - Sync VPN credentials to users
- **Server/Squad sync** - Automatic server list updates
- **Traffic monitoring** - Pull real-time traffic stats
- **Auto-sync** - Scheduled background sync
- **Webhook support** - Listen to panel events

**Key Services:**
- `remnawave_api.py` - Client library
- `remnawave_service.py` - Core integration logic
- `remnawave_sync_service.py` - Background sync worker
- `remnawave_webhook_service.py` - Webhook receiver

**Capabilities:**
- Create user accounts
- Assign servers
- Update traffic limits
- Monitor active sessions
- Handle user status changes
- Support API v2 & v3

### BedolagaBan System
- **Ban detection** - Monitor banned users
- **Sync with panel** - Reflect bans in bot
- **Admin notifications** - Alert on new bans
- **User blocking** - Prevent access

**Key Services:**
- `ban_system_api.py` - Client library
- `ban_notification_service.py` - Notification handling

### Nalogo (Russian Tax System)
- **Income reporting** - Required for RU businesses
- **Receipt generation** - Auto-create tax receipts
- **Queue service** - Manage async submissions
- **Payment tracking** - Link payments to tax records

**Key Services:**
- `nalogo_service.py` - API integration
- `nalogo_queue_service.py` - Async queue management

### Third-Party Payment Webhooks
- YooKassa webhook handler
- WATA webhook handler
- CloudPayments handler
- All webhook handlers with signature verification

---

## 8. 📊 Database Models (45+ entities)

### Core User Models
- **User** - Main user entity (Telegram ID or email-only)
- **Subscription** - Active/inactive subscriptions
- **SubscriptionServer** - Many-to-many: subscription ↔ server assignment
- **Transaction** - Balance transactions ledger
- **UserRole** - Admin role assignment
- **UserChannelSubscription** - Channel membership verification

### Payment Models
- **YooKassaPayment, CryptoBotPayment, HeleketPayment** ... (10 payment provider tables)
- Each tracks provider-specific transaction IDs and metadata
- Supports webhook reconciliation

### Subscription & Pricing
- **Tariff** - Subscription plans
- **PromoGroup** - User targeting groups
- **UserPromoGroup** - Many-to-many: user ↔ group membership
- **SubscriptionConversion** - Trial → paid conversions
- **SubscriptionEvent** - Event audit log
- **TrafficPurchase** - Standalone traffic purchases
- **SubscriptionTemporaryAccess** - Temporary access grants

### Marketing & Monetization
- **PromoCode** - Discount codes (% or fixed)
- **PromoCodeUse** - Usage tracking
- **DiscountOffer** - Dynamic discount templates
- **PromoOfferTemplate** - Reusable offer templates
- **PromoOfferLog** - Offer application history
- **AdvertisingCampaign** - Affiliate campaign config
- **AdvertisingCampaignRegistration** - Campaign attribution

### Referral System
- **ReferralEarning** - Referral bonus ledger
- **ReferralContest** - Contest periods
- **ReferralContestEvent** - Contest activity
- **WithdrawalRequest** - Referral withdrawal requests
- **PartnerApplication** - Partner signup applications

### Contests & Games
- **Poll, PollQuestion, PollOption, PollResponse, PollAnswer** - Poll entities
- **ContestTemplate** - Contest configuration
- **ContestRound** - Contest periods
- **ContestAttempt** - User participation
- **WheelConfig** - Wheel of fortune setup
- **WheelPrize** - Prize definitions
- **WheelSpin** - Spin history

### Content & Communications
- **BroadcastHistory** - Broadcast execution log
- **PinnedMessage** - Menu pinned messages
- **UserMessage** - User direct messages
- **WelcomeText** - Custom welcome templates
- **Ticket, TicketMessage** - Support tickets
- **TicketNotification** - Ticket admin alerts
- **SentNotification** - Notification delivery log

### Server & Infrastructure
- **ServerSquad** - Server group configurations
- **Squad** - Backup squads
- **MainMenuButton** - Custom menu buttons
- **MenuLayoutHistory** - Menu change audit
- **ButtonClickLog** - Analytics
- **PaymentMethodConfig** - Payment provider settings

### System & Admin
- **SystemSetting** - Global settings
- **AdminRole** - RBAC roles
- **AccessPolicy** - Permission matrix
- **AdminAuditLog** - Admin action log
- **MonitoringLog** - System health log
- **Webhook** - Registered webhooks
- **WebhookDelivery** - Webhook delivery log
- **WebApiToken** - API token management
- **RequiredChannel** - Channel subscription requirements
- **CabinetRefreshToken** - Cabinet session tokens

### Configuration & Policies
- **ServiceRule** - Business rules
- **PrivacyPolicy** - Terms of service
- **PublicOffer** - Public offer details
- **FaqSetting, FaqPage** - FAQ management

---

## 9. 🌍 Localization Support

### Supported Languages
1. **Russian** (`ru.json`, `ru.yml`) - Full support
2. **English** (`en.json`, `en.yml`) - Full support
3. **Ukrainian** (`ua.json`) - Partial support
4. **Persian/Farsi** (`fa.json`) - Partial support
5. **Chinese (Simplified)** (`zh.json`) - Partial support

### Localization Features
- Language selection per user
- Dynamic text loading from JSON
- Template variables (prices, names, dates)
- Timezone-aware formatting
- Currency formatting (RUB default, others convertible)
- Date/time localization

**Key Services:**
- `loader.py` - Load and manage language files
- `texts.py` - Text access interface

---

## 10. 🎯 Standout / Advanced Features

### Smart Features
1. **Device Limit Resolution** - Automatically select device based on HWID
2. **Cache Invalidation** - Invalidate menu/prices on config changes
3. **Cart Persistence** - Save subscription cart when balance insufficient
4. **Auto-purchase** - Automatically buy saved cart after top-up
5. **Traffic Delta** - Fast check monitors traffic delta, not absolute
6. **Email-only Users** - Support users without Telegram ID
7. **Disposable Email Detection** - Block temporary email services

### Admin Tools
- **Bulk ban system** - Mass user banning
- **Backup/restore** - Auto backups with webhook recovery
- **System monitoring** - Health checks & alerts
- **Maintenance mode** - Graceful system downtime
- **User sync from panel** - Manual or automatic (scheduled)
- **Log rotation** - Auto-archive old logs

### Security & Compliance
- **RBAC (Role-Based Access Control)** - Fine-grained permissions
- **Audit logging** - Admin action tracking
- **API token management** - Rate limiting & expiration
- **Cookie-based admin auth** - Integrate with Remnawave panel
- **Email verification** - Cabinet registration protection
- **Password hashing** - Secure password storage
- **JWT tokens** - Stateless authentication

### Monitoring & Analytics
- **Revenue tracking** - Daily/monthly totals
- **User growth metrics** - Registration trends
- **Payment success rates** - Provider-specific conversion
- **Traffic usage patterns** - User behavior analysis
- **Button click analytics** - Menu engagement
- **Referral leaderboards** - Top earners
- **Support ticket metrics** - Response times

### Infrastructure
- **Docker Compose** - Multi-container deployment
- **Redis caching** - Fast lookup, session storage
- **PostgreSQL** - Robust relational DB
- **Alembic migrations** - Schema version control
- **Asyncio + FastAPI** - High-performance async stack
- **Structured logging** - Structured log output (JSON)
- **Webhook server** - Embedded HTTP server for webhooks

### Deployment Options
- **Polling mode** - Long-polling (dev/testing)
- **Webhook mode** - Production-grade webhooks
- **Reverse proxy support** - Nginx/Caddy integration
- **SSL/TLS** - HTTPS support
- **Health checks** - Liveness/readiness endpoints

---

## 11. 📁 Project Structure Highlights

```
remnawave-bedolaga-telegram-bot-main/
├── app/
│   ├── cabinet/                    # Web cabinet routes & auth
│   │   ├── routes/                 # 48+ API endpoints
│   │   ├── auth/                   # JWT, OAuth, email verification
│   │   ├── schemas/                # Request/response models
│   │   └── services/               # Business logic
│   ├── database/
│   │   ├── models.py               # 45+ SQLAlchemy ORM models
│   │   ├── crud/                   # CRUD operations (~50 files)
│   │   └── migrations/             # Alembic schema versions
│   ├── handlers/                   # Telegram bot handlers
│   │   ├── balance/                # Payment UI handlers (14 providers)
│   │   ├── subscription/           # Purchase, renewal, traffic
│   │   ├── admin/                  # Admin command handlers (40+ files)
│   │   └── ...
│   ├── services/                   # Business logic layer (80+ files)
│   │   ├── payment/                # Payment processing
│   │   ├── contests/               # Game mechanics
│   │   ├── menu_layout/            # Menu management
│   │   └── ...
│   ├── external/                   # Third-party API clients
│   │   ├── remnawave_api.py        # VPN panel integration
│   │   ├── ban_system_api.py       # Ban monitoring
│   │   └── payment webhooks
│   ├── webapi/                     # FastAPI web server
│   │   ├── routes/                 # Web API endpoints (40+ files)
│   │   └── schemas/                # API models
│   ├── localization/               # Multi-language support
│   ├── middlewares/                # Request/response middlewares (10+ files)
│   ├── keyboards/                  # Telegram keyboard builders
│   ├── utils/                      # Utilities & helpers (20+ files)
│   └── config.py                   # Settings & env vars
├── migrations/                     # Database migrations
├── tests/                          # Unit & integration tests
├── docker-compose.yml              # Container orchestration
└── requirements.txt                # Python dependencies
```

---

## 12. 🔧 Key Technologies & Dependencies

### Backend Stack
- **Python 3.13+** - Latest stable
- **FastAPI** - Web framework
- **Aiogram** - Telegram bot library
- **SQLAlchemy** - ORM
- **AsyncIO** - Async runtime
- **PostgreSQL** - Database
- **Redis** - Cache & sessions
- **Pydantic** - Data validation

### Additional Libraries
- **aiohttp** - Async HTTP client
- **structlog** - Structured logging
- **aiosmtplib** - Async email
- **python-jose** - JWT handling
- **bcrypt** - Password hashing
- **alembic** - DB migrations

---

## Summary

This is a **production-grade, enterprise-ready VPN bot** with:
- ✅ 14 payment providers
- ✅ Full subscription lifecycle management
- ✅ Advanced admin panel (40+ features)
- ✅ Comprehensive user-facing features (referrals, contests, wheel, polls)
- ✅ Web cabinet mini-app with auth
- ✅ Multi-language support (5 languages)
- ✅ Remnawave panel integration
- ✅ RBAC & audit logging
- ✅ Email system
- ✅ Webhook infrastructure
- ✅ Redis caching
- ✅ Async architecture
- ✅ 45+ database models
- ✅ 80+ business logic services
- ✅ Docker-ready deployment
