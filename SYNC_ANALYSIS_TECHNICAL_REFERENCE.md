# VPN Bot Sync Issues - Technical Reference

## Complete File-by-File Analysis

### BOT CODE (Hardcoded Data Sources)

#### 1. bot/handlers/payment.py - Subscription Prices

**Status:** 🔴 CRITICAL - All prices hardcoded

**Hardcoded Data (lines 56-67):**
```python
PLAN_PRICES = {
    "solo": {
        "name": "👤 Минимальный (1 устройство)",
        "devices": 1,
        "prices": {7: 90, 30: 150, 90: 400, 180: 760, 365: 1450},
    },
    "family": {
        "name": "👨‍👩‍👧‍👦 Семейный (5 устройств)",
        "devices": 5,
        "prices": {7: 150, 30: 250, 90: 650, 180: 1200, 365: 2300},
    },
}
```

**Where Used:**
- Line 73: `_get_period_keyboard_with_prices(plan_key)` - reads `PLAN_PRICES[plan_key]["prices"]`
- Line 101: `select_plan()` - reads `PLAN_PRICES.get(plan_key, ...)`
- Line 139-140: `select_period()` - looks up `plan_prices.get(period_days, ...)`
- Line 42-43, 280-286: Plan buttons hardcoded as "👤 Соло - 1 устройство" / "👨‍👩‍👧‍👦 Семейный - 5 устройств"

**Problem:** Bot never fetches from `/subscriptions/plans/public` API. Uses only hardcoded PLAN_PRICES dict.

**Fix Needed:**
1. Remove hardcoded dict
2. Create `async get_plans_from_api(client: APIClient)` function
3. Call this function from all handlers that need plan data
4. Create backend endpoint: `GET /subscriptions/plans/public`

**Blocking Issue:** No backend endpoint exists to fetch plans

---

#### 2. bot/keyboards/main_menu.py - Menu Buttons

**Status:** 🔴 CRITICAL - Hardcoded fallback, missing public endpoint

**Hardcoded Data (lines 8-43):**
```python
def _build_default_buttons(show_free_trial: bool = True) -> list:
    buttons = []
    row1 = []
    if show_free_trial:
        row1.append(InlineKeyboardButton(text="🎁 Бесплатный доступ", callback_data="free_trial"))
    row1.append(InlineKeyboardButton(text="💸 Оплатить тариф", callback_data="buy_subscription"))
    buttons.append(row1)
    buttons.append([
        InlineKeyboardButton(text="👤 Личный кабинет", callback_data="cabinet"),
        InlineKeyboardButton(text="🎁 Получить бесплатно", callback_data="get_free"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔗 Реферальная система", callback_data="partner"),
        InlineKeyboardButton(text="⚙️ Инструкция по подключению", callback_data="instructions"),
    ])
    buttons.append([
        InlineKeyboardButton(text="👨‍💻 Поддержка", callback_data="support"),
        InlineKeyboardButton(text="📢 Наш канал", callback_data="channel"),
    ])
    return buttons
```

**Where Used:**
- Line 52: `get_main_menu()` - static fallback (OK for this)
- Line 90: `get_dynamic_main_menu()` - fallback when API returns empty
- Line 136: `back_to_menu()` - fallback when dynamic fetch fails

**Problem:** Line 55-96 `get_dynamic_main_menu()` tries to fetch from `/bot-buttons/public` (line 62), but:
- Endpoint doesn't exist
- Exception caught silently
- Falls back to hardcoded buttons

**Flow:**
```
get_dynamic_main_menu() called
  → client.get_bot_buttons() (line 62)
    → try /bot-buttons/public (APIClient line 234)
      → ENDPOINT DOESN'T EXIST
    → exception caught, return [] (line 241-242)
  → if not buttons_data return get_main_menu() (line 64)
    → returns hardcoded buttons from _build_default_buttons()
```

**Fix Needed:**
1. Create backend endpoint: `GET /bot-buttons/public`
2. Return button list from database (or defaults)
3. Cache with Redis key `"bot:buttons"`
4. Invalidate on admin PUT/POST/DELETE `/admin/bot-buttons`

**Blocking Issue:** Public endpoint missing

---

#### 3. bot/handlers/start.py - Welcome Text & Image

**Status:** 🟡 PARTIALLY WORKING - Fallback endpoints work but shouldn't be used

**Code (lines 52-75):**
```python
async def _get_welcome_data(client: APIClient):
    welcome_text = None
    welcome_photo = None
    try:
        texts = await client.get_all_bot_texts()  # Line 57
        welcome_text = texts.get("welcome")
    except Exception:
        pass
    try:
        settings = await client.get_bot_settings()  # Line 62
        raw = settings.get("welcome_image") or settings.get("welcome_photo") or ""
        welcome_photo = _resolve_media(raw)
    except Exception:
        pass
    if not welcome_text:
        fallback = get_fallback_texts()
        welcome_text = fallback.get("welcome", "👋 Добро пожаловать!")
    if not welcome_photo:
        env_photo = config.telegram.welcome_photo or None
        if env_photo:
            welcome_photo = _resolve_media(env_photo) or env_photo
    return welcome_text, welcome_photo
```

**APIClient Behavior (lines 209-227):**
```python
async def get_all_bot_texts(self, language: str = "ru") -> Dict[str, Any]:
    try:
        return await self.get("/bot-texts/public")  # Line 212 - TRY PUBLIC
    except Exception:
        try:
            return await self.get("/admin/bot-texts")  # Line 215 - FALLBACK TO ADMIN
        except Exception:
            return {}

async def get_bot_settings(self) -> Dict[str, Any]:
    try:
        return await self.get("/bot-settings/public")  # Line 222 - TRY PUBLIC
    except Exception:
        try:
            return await self.get("/admin/settings")  # Line 225 - FALLBACK TO ADMIN
        except Exception:
            return {}
```

**Problem:**
- Tries public endpoints first (good design)
- Falls back to admin endpoints which require authentication
- But APIClient can reach admin endpoints if it has API key
- This is a security issue (exposing admin endpoints to bot)
- Public endpoints should exist instead

**Fix Needed:**
1. Create backend endpoints: `GET /bot-texts/public` and `GET /bot-settings/public`
2. Remove fallback to `/admin/` endpoints from APIClient

**Current Status:** Works but not ideal (uses admin endpoints)

---

#### 4. bot/keyboards/subscription_kb.py - Subscription Buttons

**Status:** 🟡 HARDCODED but acceptable for internal UI

**Hardcoded Data (lines 6-73):**
- Line 10: "📱 Мои устройства"
- Line 11: "⬅️ Назад"
- Line 21: "♻️ Продлить"
- Line 22: "➕ Добавить устройство"
- Line 26: "💳 Купить подписку"
- Line 29: "🏠 На главную"
- Lines 58-67: Device types (Android, iPhone, Windows, macOS, Linux, TV)

**Assessment:** These are internal UI buttons, not customer-facing text. Hardcoding is acceptable.

---

#### 5. bot/keyboards/inline_kb.py - Helper Buttons

**Status:** 🟡 HARDCODED but acceptable

**Hardcoded Data (lines 5-103):**
- Line 12: "❌ Отменить"
- Line 29: "⬅️ Назад"
- Line 46: "✅ Подтвердить"
- Line 62-82: Link button with back button

**Assessment:** Standard UI helper buttons. Not customer-facing messaging. Hardcoding acceptable.

---

### BACKEND CODE (API Endpoints & Database)

#### 6. backend/api/v1/endpoints/admin.py - System Configuration

**Status:** 🟡 MISSING PUBLIC ENDPOINTS

**What Exists (Admin-only):**
- `GET /admin/bot-texts` (line 305) - requires admin auth
- `GET /admin/bot-buttons` (line 384) - requires admin auth
- `GET /admin/settings` (line 540) - requires admin auth
- PUT endpoints for each of above
- DELETE endpoints for each of above

**What's Missing (for bot access):**
- ❌ `GET /bot-buttons/public` - not found anywhere
- ❌ `GET /bot-texts/public` - not found anywhere
- ❌ `GET /bot-settings/public` - not found anywhere
- ❌ `GET /subscriptions/plans/public` - not found anywhere

**Cache Invalidation Function (lines 45-69):**
```python
async def _invalidate_bot_cache(*keys: str) -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import aioredis
        redis = await aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        try:
            if keys:
                await redis.delete(*keys)
            else:
                await redis.delete("bot:buttons", "bot:texts", "bot:settings", "bot:plans")
        finally:
            await redis.close()
    except Exception as e:
        logger.warning(f"Cache invalidation skipped (Redis unavailable?): {e}")
```

**Status:** ✅ Works, but no public endpoints exist to use the cached data

**Called from:**
- Line 349: `upsert_bot_text_by_key()` - invalidates "bot:texts"
- Line 372: `delete_bot_text_by_key()` - invalidates "bot:texts"
- Line 453: `create_bot_button()` - invalidates "bot:buttons"
- Line 484: `update_bot_button()` - invalidates "bot:buttons"
- Line 512: `patch_bot_button()` - invalidates "bot:buttons"
- Line 530: `delete_bot_button()` - invalidates "bot:buttons"
- Line 577: `save_bot_settings()` - invalidates "bot:settings"

**Problem:** Cache is invalidated but public endpoints don't exist to serve cached data

---

#### 7. backend/api/v1/endpoints/admin.py - Database Session Management

**Status:** 🟡 FRAGILE - Missing try-finally blocks

**Problem Examples:**

**Bad (lines 104-147):**
```python
async def update_system_settings(data: SystemSettingsUpdate, ...):
    try:
        stmt = select(BotText).where(BotText.key == SYSTEM_SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        existing = json.loads(row.value) if row else {}
        update_dict = data.model_dump(exclude_unset=True)
        existing.update(update_dict)
        value = json.dumps(existing, ensure_ascii=False)
        if row:
            row.value = value
        else:
            row = BotText(id=str(uuid4()), key=SYSTEM_SETTINGS_KEY, value=value, ...)
            db.add(row)
        await db.commit()  # ← If fails, session in error state
        # ...
        return SystemSettingsResponse(...)
    except Exception as e:
        logger.error(f"Error saving system settings: {e}")
        await db.rollback()  # ← Cleanup only in except
        raise HTTPException(status_code=500, detail="Failed to save system settings")
    # ← No finally block!
```

**Better Pattern:**
```python
try:
    await db.commit()
except Exception as e:
    await db.rollback()
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=500, detail="Database error")
finally:
    # Session closed automatically by dependency, but explicit is better
    pass
```

**Endpoints with fragile error handling:**
- Lines 104-147: `update_system_settings()`
- Lines 327-355: `upsert_bot_text_by_key()`
- Lines 415-454: `create_bot_button()`
- Lines 457-485: `update_bot_button()`
- Lines 488-514: `patch_bot_button()`
- Lines 517-531: `delete_bot_button()`
- Lines 558-582: `save_bot_settings()`

**Impact:** If commit fails, session left in error state. Subsequent requests might hang waiting for connection.

---

#### 8. backend/database.py - Connection Pool

**Status:** 🔴 CRITICAL - NullPool causes connection exhaustion

**Problem Code (line 24):**
```python
_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    poolclass=NullPool,  # ← PROBLEM: No connection reuse
)
```

**How NullPool Works:**
- Every request: create new connection
- Every request: close connection after use
- No connection pooling/reuse
- Under load (broadcast to 1000 users):
  - 1000 connection create/destroy cycles
  - Database receives 1000 simultaneous open requests
  - Eventually hits max_connections limit
  - Returns "too many connections" error
  - Result: ERR_CONNECTION_RESET

**Recommended Fix:**
```python
from sqlalchemy.pool import QueuePool

_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    poolclass=QueuePool,
    pool_size=20,           # Keep 20 connections ready
    max_overflow=10,        # Allow 10 more under load
    pool_recycle=3600,      # Recycle connections every hour
)
```

---

### WORKER CODE (Background Tasks)

#### 9. worker/tasks/notifications.py - Notification Templates

**Status:** 🔴 CRITICAL - All text hardcoded, never fetches from DB

**Hardcoded Notification Templates (lines 103-208):**

**24h before expiry (lines 104-111):**
```python
(
    24, '24h', 'notified_24h',
    '⏰ <b>Ваша VPN-подписка истекает через 24 часа</b>\n\n'
    'Не забудьте продлить подписку, чтобы не потерять доступ к VPN.\n\n'
    '📱 Тариф: {plan}\n'
    '⏳ Истекает: {expires}\n\n'
    '👇 Продлите подписку прямо сейчас:'
),
```

**12h before expiry (lines 112-119):** Similar hardcoded text

**1h before expiry (lines 120-127):** Similar hardcoded text

**At expiry (lines 128-134):** Similar hardcoded text

**3h after expiry (lines 202-208):** Similar hardcoded text

**Problem:**
- Lines 139-175: Loop through notification configs
- Lines 161-164: Format template with `subscription.plan_name` and `expires`
- **NEVER checks database or API for updated text**
- All messages are identical every time
- No way to change message without redeploying worker

**Where Texts Hardcoded:**
```python
message = message_template.format(
    plan=subscription.plan_name,
    expires=expires_str,
)
message += f'\n<a href="{bot_link}">Перейти в бот</a>'
```

**Database Connection (lines 13-18):**
```python
DATABASE_URL = os.getenv(...)
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**Problem:** Creates separate DB engine instead of using backend's database module. Doesn't fetch notification templates.

**Fix Needed:**
1. Create `/admin/notification-templates` API endpoints to store/edit notification texts
2. OR store notification texts in `BotText` table with keys like `"notif_24h"`, `"notif_12h"`, etc.
3. Task fetches templates from API/database before sending
4. Fall back to hardcoded only if API/database unavailable

---

### API CLIENT (Bot → Backend Communication)

#### 10. bot/utils/api_client.py - Subscription Plans

**Status:** 🔴 MISSING - No method to fetch subscription plans

**What Exists:**
- Line 126-138: `get_subscription_plans()` - fetches from `/subscriptions/plans`
- **But this endpoint might not exist or might return different format**

**Code:**
```python
async def get_subscription_plans(self) -> list:
    """Get available subscription plans"""
    try:
        result = await self.get("/subscriptions/plans")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("plans", result.get("items", []))
        return []
    except Exception:
        return []
```

**Problem:** 
- Tries `/subscriptions/plans` endpoint
- Returns empty list on exception
- Bot never uses this method (instead uses hardcoded PLAN_PRICES dict)
- No public endpoint mentioned, likely requires auth if it exists

**Missing Methods:**
- No method to fetch bot buttons directly
- No method to fetch bot texts directly
- No method to fetch bot settings directly

**Needed:**
```python
async def get_bot_buttons(self) -> list:
    """Get main menu buttons from /bot-buttons/public endpoint"""
    try:
        result = await self.get("/bot-buttons/public")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("buttons", [])
        return []
    except Exception:
        return []
```

---

## SYNC FAILURE FLOW DIAGRAMS

### Scenario: Admin Changes Button Text

```
ADMIN PANEL
│
├─ User clicks "Edit Button"
├─ Changes text: "💸 Оплатить" → "💳 Купить VPN"
├─ Clicks Save
│
└─→ API PUT /admin/bot-buttons/{id}
    │
    ├─ Backend: update BotText in database ✓ (line 482)
    ├─ Backend: call _invalidate_bot_cache("bot:buttons") ✓ (line 484)
    │   ├─ Connects to Redis
    │   ├─ Deletes key "bot:buttons" from cache ✓
    │   └─ Connection closed
    │
    └─ Backend: return success response to admin ✓

USER (BOT)
│
├─ User sends /start command
├─ Bot calls get_dynamic_main_menu() (line 128)
│
└─→ get_dynamic_main_menu() calls:
    └─ client.get_bot_buttons() (line 62)
       │
       └─→ APIClient.get()/bot-buttons/public
           │
           ├─ Bot has no authentication
           ├─ Endpoint doesn't exist (404)
           │
           └─ Exception caught, returns [] (line 241-242)
   
   Back in get_dynamic_main_menu():
   └─ if not buttons_data (is empty list, so True)
      └─ return get_main_menu() (line 90)
         └─ return hardcoded buttons from _build_default_buttons()
            └─ User sees OLD TEXT: "💸 Оплатить тариф"

RESULT: Admin changes button, user still sees old button ❌
```

### Scenario: Admin Changes Subscription Price

```
ADMIN PANEL
│
├─ User clicks "Edit Plan"
├─ Changes Solo 30-day price: 150 → 200
├─ Clicks Save
│
└─→ API PUT /admin/plans/solo
    │
    ├─ Backend: update PlanPrice in database ✓
    ├─ Backend: return success ✓
    │
    └─ (Note: No cache invalidation for /subscriptions/plans/public)

USER (BOT) - SUBSCRIBING
│
├─ User clicks "Оплатить тариф" (callback: buy_subscription)
├─ Bot handler: select_plan() (line 93)
│   └─ Reads: PLAN_PRICES["solo"]["prices"][30] = 150 (HARDCODED)
│   └─ Shows button: "1 месяц — 150 рублей"
│
├─ User thinks: "Cheap! Only 150 rubles"
├─ User clicks period_30
│
├─ Bot handler: select_period() (line 127)
│   └─ Reads: PLAN_PRICES["solo"]["prices"][30] = 150 (HARDCODED)
│   └─ Stores in state: price=150
│
├─ User selects payment method
├─ Payment is processed
│
└─→ Backend receives payment request
    ├─ Checks database: Solo 30-day = 200 (from admin update)
    ├─ User paid: ? (depends on payment flow)
    └─ MISMATCH: Bot showed 150, backend has 200

RESULT: User sees old price, gets charged new price ❌
        Billing dispute, refund needed
```

---

## REDIS CACHE KEYS (Defined but Unused)

**Keys that are invalidated (lines 60-65 in admin.py):**
- `"bot:buttons"` - should cache menu buttons
- `"bot:texts"` - should cache bot text messages
- `"bot:settings"` - should cache bot settings
- `"bot:plans"` - should cache subscription plans

**Status:** 🔴 Cache is invalidated but public endpoints don't exist to read from it

---

## MISSING BACKEND ENDPOINTS (Required to Fix Sync)

### 1. GET /bot-buttons/public
```
Purpose: Return menu buttons without authentication
Response: [
  {"text": "🎁 Бесплатный доступ", "callback_data": "free_trial", "row": 0, ...},
  {"text": "💸 Оплатить тариф", "callback_data": "buy_subscription", "row": 0, ...},
  ...
]
Cache key: "bot:buttons"
Invalidate on: PUT /admin/bot-buttons/{id}, POST /admin/bot-buttons, DELETE /admin/bot-buttons/{id}
```

### 2. GET /bot-texts/public
```
Purpose: Return bot message texts without authentication
Response: {
  "welcome": "👋 Привет! Я VPN бот...",
  "support_text": "📩 Свяжитесь с поддержкой...",
  ...
}
Cache key: "bot:texts"
Invalidate on: PUT /admin/bot-texts/{key}, DELETE /admin/bot-texts/{key}
```

### 3. GET /bot-settings/public
```
Purpose: Return bot settings without authentication
Response: {
  "welcome_image": "/static/uploads/welcome.jpg",
  "support_username": "@support",
  ...
}
Cache key: "bot:settings"
Invalidate on: PUT /admin/settings
```

### 4. GET /subscriptions/plans/public
```
Purpose: Return subscription plans and prices without authentication
Response: [
  {
    "id": "solo",
    "name": "Минимальный (1 устройство)",
    "devices": 1,
    "prices": {7: 90, 30: 150, 90: 400, 180: 760, 365: 1450}
  },
  {
    "id": "family",
    "name": "Семейный (5 устройств)",
    "devices": 5,
    "prices": {7: 150, 30: 250, 90: 650, 180: 1200, 365: 2300}
  }
]
Cache key: "bot:plans"
Invalidate on: PUT /admin/plans/{id}
```

### 5. GET /notifications/templates/public (optional)
```
Purpose: Return notification message templates without authentication
Response: {
  "24h": "⏰ Ваша VPN-подписка истекает через 24 часа...",
  "12h": "⏰ Ваша VPN-подписка истекает через 12 часов...",
  ...
}
Cache key: "bot:notification_templates"
Invalidate on: PUT /admin/notification-templates/{key}
```

---

## SUMMARY TABLE: What's Broken and Why

| Component | Issue | Root Cause | Fix Complexity |
|-----------|-------|-----------|-----------------|
| Subscription Prices | Bot uses hardcoded dict | No API endpoint to fetch plans | Medium (need endpoint + bot refactor) |
| Menu Buttons | Bot falls back to hardcoded | Public endpoint missing | Medium (need endpoint + caching) |
| Plan Names | Bot hardcodes 2 plans | Public endpoint missing | Medium (same as prices) |
| Welcome Text | Works via admin fallback | Uses admin endpoint (should use public) | Low (create public endpoint) |
| Welcome Image | Works via admin fallback | Uses admin endpoint (should use public) | Low (create public endpoint) |
| Notification Text | Can't change without redeploying | Hardcoded in task code | Medium (create template endpoints) |
| Server Crashes on Broadcast | NullPool exhaustion | Pool misconfiguration | Low (1-line fix) |
| Session Hangs | No error recovery | Missing try-finally | Low (add error handling) |

