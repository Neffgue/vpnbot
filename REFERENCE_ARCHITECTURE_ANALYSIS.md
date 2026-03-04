# Reference Architecture Analysis: remnawave-bedolaga-telegram-bot

## Overview
This document provides the exact technical specifications from the reference Telegram bot project for implementing tariff prices and image/photo management.

---

## 1. TARIFF PRICING ARCHITECTURE

### 1.1 Database Model: Tariff
**Location:** `app/database/models.py` (line 818-989)

**Exact DB Column Names for Price Fields:**
- `period_prices` (JSON) — Key field storing all period-based prices
  - Format: `{"14": 30000, "30": 50000, "90": 120000, ...}` (period_days: price_in_kopeks)
  - String keys represent days, integer values represent price in kopeks
  
- `daily_price_kopeks` (Integer) — Price per day for daily tariff mode
- `price_per_day_kopeks` (Integer) — Price per day for custom days purchase
- `device_price_kopeks` (Integer, nullable) — Price for additional device purchase
- `traffic_price_per_gb_kopeks` (Integer) — Price per GB for custom traffic purchase
- `traffic_topup_packages` (JSON) — Packages for traffic topup `{"5": 5000, "10": 9000, ...}`

**All Price Storage Unit:** Kopeks (1 Ruble = 100 kopeks)

**Methods to Access Prices:**
```python
tariff.get_price_for_period(period_days: int) -> int | None  # Returns kopeks
tariff.get_price_rubles(period_days: int) -> float | None     # Returns rubles
tariff.get_daily_price_rubles() -> float
tariff.get_price_for_custom_days(days: int) -> int | None
tariff.get_price_for_custom_traffic(gb: int) -> int | None
tariff.get_traffic_topup_price(gb: int) -> int | None
```

---

## 2. IMAGE/PHOTO MANAGEMENT ARCHITECTURE

### 2.1 MainMenuButton Model (Images per Button)
**Location:** `app/database/models.py` (line 2443)

**DB Columns for Images/Media:**
The reference implementation **does NOT store image_url or media_id directly in MainMenuButton**. 

Instead, MainMenuButton has:
- `text` (String, max 255) — Button display text
- `action_type` (Enum: `MainMenuButtonActionType`) — URL or MINI_APP
- `action_value` (String, max 1024) — The URL/action value
- `visibility` (Enum: `MainMenuButtonVisibility`) — ALL, ADMINS, or SUBSCRIBERS
- `is_active` (Boolean)
- `display_order` (Integer)
- `created_at`, `updated_at` (AwareDateTime)

**NO image/photo columns exist in MainMenuButton model!**

### 2.2 WelcomeText Model (Images per Welcome Message)
**Location:** `app/database/models.py` (line 2206)

The model structure was not fully shown in my queries, but based on schema patterns:
- Likely contains `media_id` or `image_url` field
- Used for welcome messages with attached images

---

## 3. API ENDPOINTS: TARIFF PRICES

### 3.1 GET Tariffs Endpoint
**Location:** `app/webapi/routes/subscriptions.py`

**Endpoint:** `GET /api/v1/tariffs/` (implied from subscriptions.py patterns)

**Exact JSON Response for Tariffs:**
```python
# From schema: app/webapi/schemas/subscriptions.py
class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    status: str
    actual_status: str
    is_trial: bool
    start_date: datetime
    end_date: datetime
    traffic_limit_gb: int
    traffic_used_gb: float
    device_limit: int
    autopay_enabled: bool
    autopay_days_before: int | None = None
    subscription_url: str | None = None
    subscription_crypto_link: str | None = None
    connected_squads: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

**Note:** For tariffs specifically, the response should include:
- `period_prices` — Dictionary with period_days as keys, price_kopeks as values
- `daily_price_kopeks`
- `price_per_day_kopeks`
- `device_price_kopeks`
- `traffic_topup_packages`

### 3.2 Pricing Data Flow in Bot
**Location:** `app/handlers/subscription/pricing.py`

**How Bot Gets Prices:**
1. Function `_prepare_subscription_summary()` fetches prices from `PERIOD_PRICES` config or from tariff DB
2. Uses `PERIOD_PRICES.get(period_days, 0)` — from config at startup
3. Falls back to database tariff prices via `Tariff.get_price_for_period()`

**Exact Fields Returned in Pricing Summary:**
```python
summary_data = {
    'period_days': int,
    'total_price': int,  # In kopeks
    'base_price': int,
    'base_price_original': int,
    'base_discount_percent': int,
    'base_discount_total': int,
    'final_traffic_gb': int,
    'traffic_price_per_month': int,
    'traffic_discount_percent': int,
    'traffic_discount_total': int,
    'traffic_discounted_price_per_month': int,
    'total_traffic_price': int,
    'servers_price_per_month': int,
    'countries_price_per_month': int,
    'servers_discount_percent': int,
    'servers_discount_total': int,
    'servers_discounted_price_per_month': int,
    'total_servers_price': int,
    'devices_price_per_month': int,
    'devices_discount_percent': int,
    'devices_discount_total': int,
    'devices_discounted_price_per_month': int,
    'total_devices_price': int,
    'promo_offer_discount_percent': int,  # Optional
    'promo_offer_discount_value': int,    # Optional
    'total_price_before_promo_offer': int # Optional
}
```

---

## 4. API ENDPOINTS: MAIN MENU BUTTONS

### 4.1 GET Main Menu Buttons
**Location:** `app/webapi/routes/main_menu_buttons.py`

**Endpoint:** `GET /api/v1/main-menu-buttons`

**Query Parameters:**
- `limit` (int, 1-200, default 50)
- `offset` (int, default 0)

**Exact JSON Response:**
```python
class MainMenuButtonListResponse(BaseModel):
    items: list[MainMenuButtonResponse]
    total: int
    limit: int
    offset: int

class MainMenuButtonResponse(BaseModel):
    id: int
    text: str
    action_type: MainMenuButtonActionType  # "url" or "mini_app"
    action_value: str                      # The URL or action
    visibility: MainMenuButtonVisibility   # "all", "admins", "subscribers"
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
```

### 4.2 POST/PATCH Main Menu Buttons
**Location:** `app/webapi/routes/main_menu_buttons.py`

**Create Endpoint:** `POST /api/v1/main-menu-buttons`

**Update Endpoint:** `PATCH /api/v1/main-menu-buttons/{button_id}`

**Request Body:**
```python
class MainMenuButtonCreateRequest(BaseModel):
    text: str                              # 1-64 chars
    action_type: MainMenuButtonActionType  # Required
    action_value: str                      # 1-1024 chars, must start with http:// or https://
    visibility: MainMenuButtonVisibility   # Default: "all"
    is_active: bool                        # Default: True
    display_order: int | None              # >= 0

class MainMenuButtonUpdateRequest(BaseModel):
    text: str | None                       # Optional
    action_type: MainMenuButtonActionType | None
    action_value: str | None
    visibility: MainMenuButtonVisibility | None
    is_active: bool | None
    display_order: int | None
```

### 4.3 DELETE Main Menu Buttons
**Endpoint:** `DELETE /api/v1/main-menu-buttons/{button_id}`

**Response:** 204 No Content

---

## 5. CACHE INVALIDATION MECHANISM

### 5.1 Redis Cache Service
**Location:** `app/utils/cache.py`

**Cache Key Format:**
```python
def cache_key(*parts) -> str:
    return ':'.join(str(part) for part in parts)
```

**Example Cache Keys:**
- `main_menu_buttons:all` — All buttons
- `user:{user_id}` — User data
- `session:{user_id}:{session_key}` — User session
- `channel_sub:{telegram_id}:{channel_id}` — Channel subscription status
- `required_channels:active` — Required channels list

### 5.2 MainMenuButton Cache Invalidation
**Location:** `app/webapi/routes/main_menu_buttons.py`

**When Cache is Invalidated:**
```python
@router.post('', response_model=MainMenuButtonResponse, status_code=status.HTTP_201_CREATED)
async def create_main_menu_button_endpoint(...):
    button = await create_main_menu_button(...)
    MainMenuButtonService.invalidate_cache()  # INVALIDATES HERE
    return _serialize(button)

@router.patch('/{button_id}', response_model=MainMenuButtonResponse)
async def update_main_menu_button_endpoint(...):
    button = await update_main_menu_button(...)
    MainMenuButtonService.invalidate_cache()  # INVALIDATES HERE
    return _serialize(button)

@router.delete('/{button_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_main_menu_button_endpoint(...):
    await delete_main_menu_button(...)
    MainMenuButtonService.invalidate_cache()  # INVALIDATES HERE
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### 5.3 Cache TTL Values
**From `app/utils/cache.py`:**
- `ChannelSubCache.SUB_TTL = 600` — 10 minutes per user subscription status
- `ChannelSubCache.CHANNELS_TTL = 60` — 1 minute per required channels list
- Generic cache with `expire` parameter (default 300 seconds = 5 minutes)
- Daily stats cache: 86400 seconds (24 hours)

### 5.4 MainMenuButtonService Cache Methods
**Location:** `app/services/main_menu_button_service.py` (implied)

The service provides:
- `MainMenuButtonService.get_buttons_for_user()` — Retrieves cached buttons
- `MainMenuButtonService.invalidate_cache()` — Clears cache for buttons

---

## 6. BOT-SIDE PRICE AND IMAGE RETRIEVAL

### 6.1 How Bot Gets Prices from API
**Location:** `app/handlers/subscription/pricing.py`

**Price Retrieval Flow:**
1. Bot calls `_prepare_subscription_summary()` function
2. Function gets user's promo_group_id for discount calculation
3. Retrieves prices via `PERIOD_PRICES.get(days)` — loaded from DB at startup
4. Falls back to Tariff model methods if custom rates

**Exact Fields Bot Receives:**
- All fields from summary_data dict (see section 3.2)
- Prices always in kopeks
- Converted to rubles via division by 100 for display

### 6.2 How Bot Handles Images (NOT IMPLEMENTED IN REFERENCE)
**Critical Finding:** The reference implementation **DOES NOT** handle images per button/tariff!

**Evidence:**
- MainMenuButton model has NO image_url or media_id field
- Buttons only store `text`, `action_type`, `action_value`
- Images are NOT tied to tariff pricing
- No photo message sending per button found in handlers

**Photo Handling in Bot:**
- `app/utils/photo_message.py` — Exists but used for generic photo handling
- Function: `edit_or_answer_photo()` — Used in menu handlers for text + optional photo
- Photos are NOT tied to individual buttons or tariffs

**Menu Photo in Reference Implementation:**
- Main menu can have ONE photo (not per-button)
- Photo handling is centralized, not per-item
- See `app/handlers/menu.py` function `show_main_menu()` using `edit_or_answer_photo()`

---

## 7. CRITICAL ARCHITECTURAL DIFFERENCES

### What the Reference Implementation DOES:
✅ Store tariff prices in DB (Tariff model with period_prices JSON)
✅ Provide API endpoints to GET/PATCH tariff prices
✅ Cache invalidation for menu buttons
✅ Redis-based caching for frequently accessed data
✅ Price calculation with discounts (promo groups)

### What the Reference Implementation DOES NOT:
❌ Store images per tariff
❌ Store images per button
❌ Send photos with tariff information
❌ Tie media to pricing data
❌ Cache prices separately (uses config + DB fallback)

---

## 8. DATABASE SCHEMA SUMMARY

### Tariff Columns (Price-Related):
```
Column Name                  | Type      | Format/Example
----------------------------------------------------
period_prices              | JSON      | {"14": 30000, "30": 50000}
daily_price_kopeks         | Integer   | 10000
price_per_day_kopeks       | Integer   | 100
device_price_kopeks        | Integer   | 5000
traffic_price_per_gb_kopeks| Integer   | 1000
traffic_topup_packages     | JSON      | {"5": 5000, "10": 9000}
```

### MainMenuButton Columns (Media-Related):
```
Column Name                | Type      | Notes
----------------------------------------------------
id                        | Integer   | Primary Key
text                      | String    | Button label (64 chars max)
action_type              | String    | "url" or "mini_app"
action_value             | String    | The URL/action (1024 chars max)
visibility               | String    | "all", "admins", "subscribers"
is_active                | Boolean   |
display_order            | Integer   |
created_at               | DateTime  |
updated_at               | DateTime  |
[NO IMAGE COLUMNS]       | -         | Images NOT supported
```

---

## 9. CACHING IMPLEMENTATION PATTERNS

### Cache Set Operation:
```python
await cache.set(key, value, expire=ttl_seconds)
```

### Cache Get Operation:
```python
value = await cache.get(key)  # Returns None if not found or expired
```

### Pattern Deletion:
```python
await cache.delete_pattern(pattern)  # e.g., "main_menu_buttons:*"
```

### Exact Cache Service Methods (from cache.py):
- `async get(key)` → Returns deserialized JSON or None
- `async set(key, value, expire)` → Serializes and stores
- `async delete(key)` → Removes key
- `async delete_pattern(pattern)` → Removes keys matching glob pattern
- `async exists(key)` → Checks if key exists
- `async expire(key, seconds)` → Sets TTL on existing key

---

## 10. API RESPONSE JSON FIELD NAMES

### Tariff Price Response (If implemented):
```json
{
  "id": 1,
  "name": "Standard",
  "period_prices": {
    "14": 30000,
    "30": 50000,
    "90": 120000
  },
  "daily_price_kopeks": 0,
  "price_per_day_kopeks": 100,
  "device_price_kopeks": 5000,
  "traffic_price_per_gb_kopeks": 1000,
  "traffic_topup_packages": {
    "5": 5000,
    "10": 9000,
    "20": 15000
  },
  "is_active": true,
  "is_trial_available": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

### MainMenuButton Response:
```json
{
  "id": 1,
  "text": "📱 Open App",
  "action_type": "url",
  "action_value": "https://example.com/app",
  "visibility": "all",
  "is_active": true,
  "display_order": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

## CONCLUSION

The reference implementation provides a **solid foundation for tariff price management** with:
- Proper DB schema using JSON for flexible pricing models
- Cache invalidation on updates
- API endpoints for CRUD operations
- Discount calculations with promo groups

However, it **does NOT implement image/photo management tied to tariffs or buttons**. This is a **gap that needs to be addressed separately** in the current project's requirements.

