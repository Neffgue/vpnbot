# REMNAWAVE-BEDOLAGA: Admin Panel to Bot Sync Architecture Analysis

## Executive Summary

The remnawave-bedolaga bot implements a **sophisticated multi-layer caching and invalidation system** to synchronize admin panel changes (settings, buttons, texts, tariffs, prices) with the running bot WITHOUT requiring a restart. The architecture follows these principles:

1. **In-Memory Class Caches** for critical UI elements (buttons, menu layouts)
2. **Redis Caching** for distributed/persisted data (user sessions, channel subscriptions)
3. **Database as Source of Truth** (PostgreSQL/SQLite)
4. **Explicit Cache Invalidation** on CRUD operations via Web API endpoints
5. **Lazy Loading** from DB on cache miss

---

## Part 1: Settings & Configuration Management

### Data Flow

```
Admin Panel (WebAPI) → BotConfigurationService → SystemSetting (DB)
                          ↓
                    settings object (singleton)
                          ↓
                      Used in handlers/services
```

### Key Files & Mechanisms

**1. System Settings Service** (`app/services/system_settings_service.py`)

- **Class**: `BotConfigurationService`
- **Singleton pattern**: Manages all bot configuration via `bot_configuration_service` instance
- **Data source**: Reads from `SystemSetting` table in database
- **Caching**: Python singleton + lazy evaluation via `settings` global object

**Redis Key Patterns**: None directly for settings (settings are in-memory singleton)

**Critical Methods**:
```python
async def get_definition(key: str) -> SettingDefinition
async def get_current_value(key: str) -> Any
async def set_value(db: AsyncSession, key: str, value: Any) -> None
async def reset_value(db: AsyncSession, key: str) -> None
```

**2. Web API Endpoint** (`app/webapi/routes/config.py`)

```
PUT /config/{key} → SettingUpdateRequest
    - Coerces value type (bool/int/float/str)
    - Validates against CHOICES if applicable
    - Calls: bot_configuration_service.set_value(db, key, value)
    - db.commit() persists to database
    
DELETE /config/{key}
    - Calls: bot_configuration_service.reset_value(db, key)
    - Removes override from SystemSetting table
```

**Issue**: The settings singleton object is loaded at startup. Changes persist to DB, but the in-memory `settings` object may not refresh immediately. This requires:
- Manual property reload or
- Application restart (PROBLEM IDENTIFIED)

---

## Part 2: Welcome Text Management

### Data Flow

```
Admin Panel (WebAPI) → WelcomeText CRUD → WelcomeText (DB Table)
                                              ↓
                                    Bot reads on /start
```

### Key Mechanisms

**1. CRUD Operations** (`app/database/crud/welcome_text.py`)

```python
async def get_active_welcome_text(db: AsyncSession) -> str | None
    # Queries: WHERE is_active=True AND is_enabled=True
    # Gets most recently updated text
    
async def get_welcome_text_for_user(db: AsyncSession, user) -> str
    # Replaces placeholders: {user_name}, {first_name}, {username}, {username_clean}
    
async def update_welcome_text(db, text, text_content, is_active, is_enabled)
    # Marks other texts as inactive, commits immediately
```

**2. Bot Handler** (`app/handlers/start.py`)

```python
async def handle_start(message: types.Message, state: FSMContext, db: AsyncSession):
    # Calls: get_welcome_text_for_user(db, user)
    # DIRECT DB READ - No caching layer
    # Result: Changes appear immediately on next /start
```

**3. Web API Endpoint** (`app/webapi/routes/welcome_texts.py`)

```
POST /welcome-texts → create_welcome_text(db, text_content, ...)
PATCH /welcome-texts/{id} → update_welcome_text(db, ...)
    - All operations commit immediately to DB
    - No cache invalidation (because no cache)
    
GET /welcome-texts → list_welcome_texts(db, ...)
    - Reads directly from DB each time
```

**Key Finding**: Welcome texts use **direct database reads** with no caching. Changes appear immediately because bot queries DB on every /start call.

---

## Part 3: Main Menu Buttons Management

### Data Flow

```
Admin Panel (WebAPI) → MainMenuButton CRUD → MainMenuButton (DB Table)
                                                   ↓
                           MainMenuButtonService (in-memory cache)
                                                   ↓
                            Bot handlers use cached data
```

### Key Mechanisms

**1. CRUD Layer** (`app/database/crud/main_menu_button.py`)

```python
async def get_main_menu_buttons(db, limit, offset) -> list[MainMenuButton]
    # ORDER BY display_order ASC, id ASC
    
async def create_main_menu_button(db, text, action_type, action_value, visibility, is_active, display_order)
    - db.add(button)
    - await db.commit()
    
async def update_main_menu_button(db, button, text=None, action_type=None, ...)
    - await db.commit()
    
async def reorder_main_menu_buttons(db, ordered_ids: Sequence[int])
    - Updates display_order for each button
    - await db.commit()
```

**2. Service Layer** (`app/services/main_menu_button_service.py`)

**Class**: `MainMenuButtonService`

**Caching Strategy**: In-Memory Class Cache with Lock

```python
class MainMenuButtonService:
    _cache: list[_MainMenuButtonData] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
        
    @classmethod
    async def _load_cache(cls, db: AsyncSession) -> list[_MainMenuButtonData]:
        if cls._cache is not None:
            return cls._cache  # Return cached data
        
        async with cls._lock:  # Ensure only one load at a time
            if cls._cache is not None:
                return cls._cache
            
            # Load from DB and parse into _MainMenuButtonData
            result = await db.execute(
                select(MainMenuButton).order_by(
                    MainMenuButton.display_order.asc(),
                    MainMenuButton.id.asc(),
                )
            )
            items = []
            for record in result.scalars().all():
                # Validate and parse
                items.append(_MainMenuButtonData(...))
            
            cls._cache = items
            return items
    
    @classmethod
    async def get_buttons_for_user(
        cls, db, is_admin, has_active_subscription, subscription_is_active
    ) -> list[InlineKeyboardButton]:
        data = await cls._load_cache(db)  # Hits cache or loads from DB
        
        # Filter by visibility (ADMINS/SUBSCRIBERS/ALL)
        # Check if referral program enabled
        # Build InlineKeyboardButton objects
```

**3. Web API Invalidation** (`app/webapi/routes/main_menu_buttons.py`)

```
POST /main-menu-buttons → create_main_menu_button(...)
    - await db.commit()
    - MainMenuButtonService.invalidate_cache()  # INVALIDATES!
    
PATCH /main-menu-buttons/{id} → update_main_menu_button(...)
    - await db.commit()
    - MainMenuButtonService.invalidate_cache()
    
DELETE /main-menu-buttons/{id} → delete_main_menu_button(...)
    - await db.commit()
    - MainMenuButtonService.invalidate_cache()
```

**Cache Invalidation Flow**:

```
1. Admin makes change in panel (e.g., updates button text)
2. HTTP request hits PATCH endpoint
3. Endpoint updates DB and commits
4. Endpoint calls MainMenuButtonService.invalidate_cache()
   - Sets _cache = None
5. Next bot user query for menu calls get_buttons_for_user()
6. Service detects cache is None, loads fresh from DB
7. Bot shows updated button to user
```

**Result**: Changes appear on next bot menu interaction (within seconds)

---

## Part 4: Tariff Prices & Dynamic Pricing

### Data Flow

```
Admin Panel (WebAPI) → Tariff/PeriodPrice CRUD → Tariff (DB Table)
                                                      ↓
                                            PERIOD_PRICES config
                                                      ↓
                                    pricing.py functions
```

### Key Mechanisms

**1. Tariff CRUD** (`app/database/crud/tariff.py`)

```python
async def get_all_tariffs(db, include_inactive=False, ...) -> list[Tariff]
    # SELECT * FROM tariff WHERE is_active=True
    # Eager loads: allowed_promo_groups
    
async def get_tariff_by_id(db, tariff_id, with_promo_groups=True) -> Tariff | None
    # Direct DB lookup with optional promo groups
```

**2. Price Configuration** (`app/config.py` - PERIOD_PRICES)

```python
PERIOD_PRICES = {
    14: 99,    # kopeks
    30: 199,
    60: 299,
    90: 399,
    180: 599,
    360: 899,
}
```

**Loading Strategy**:
- Defined in config at startup
- Overridable via SystemSetting table
- Function: `refresh_period_prices()` updates in-memory dict

**3. Pricing Handler** (`app/handlers/subscription/pricing.py`)

```python
async def _prepare_subscription_summary(db_user, data, texts):
    # Gets base price: PERIOD_PRICES.get(period_days, 0)
    
    # Gets traffic price: settings.get_traffic_price(traffic_gb)
    # Gets server price: await _get_countries_info()
    # Gets device price: settings.PRICE_PER_DEVICE
    
    # All prices are fresh from DB via settings object at query time
```

**4. Admin Update Flow**

**Cabinet API** (`app/cabinet/routes/admin_tariffs.py`):
```
PUT /cabinet/tariffs/{id} → Update tariff fields
    - Save to Tariff table
    - db.commit()
    - NO explicit cache invalidation (prices computed on demand)
```

**Result**: Tariff changes appear on next pricing calculation (no cache, always fresh from DB)

---

## Part 5: Menu Layout (Custom Keyboard Constructor)

### Data Flow

```
Admin Panel (WebAPI) → MenuLayout config → SystemSetting (JSON column)
                                                ↓
                           MenuLayoutService (in-memory cache)
                                                ↓
                    Bot builds keyboards from cached config
```

### Key Mechanisms

**1. Storage** (`app/services/menu_layout/service.py`)

**Constant**: `MENU_LAYOUT_CONFIG_KEY = 'MENU_LAYOUT_CONFIG'`

**Structure**:
```python
{
    'version': 1,
    'rows': [
        {
            'id': 'row_1',
            'buttons': ['btn_subscribe', 'btn_cabinet'],
            'conditions': {'user_status': 'all'},
            'max_per_row': 2,
        }
    ],
    'buttons': {
        'btn_subscribe': {
            'type': 'custom',
            'text': {'ru': 'Подписка', 'en': 'Subscribe'},
            'action': 'buy_subscription',
            'enabled': True,
            'visibility': 'all',
            'dynamic_text': False,
        }
    }
}
```

**2. Service Class** (`app/services/menu_layout/service.py`)

```python
class MenuLayoutService:
    _cache: dict[str, Any] | None = None
    _cache_updated_at: datetime | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
        cls._cache_updated_at = None
    
    @classmethod
    async def get_config(cls, db: AsyncSession) -> dict[str, Any]:
        if cls._cache is not None:
            return cls._cache  # Return cached config
        
        async with cls._lock:
            if cls._cache is not None:
                return cls._cache
            
            # Load from DB via upsert_system_setting
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == MENU_LAYOUT_CONFIG_KEY)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                cls._cache = json.loads(setting.value)
            else:
                cls._cache = copy.deepcopy(DEFAULT_MENU_CONFIG)
            
            return cls._cache
    
    @classmethod
    async def save_config(cls, db: AsyncSession, config: dict) -> None:
        await upsert_system_setting(
            db,
            key=MENU_LAYOUT_CONFIG_KEY,
            value=json.dumps(config),
        )
        await db.commit()
        cls.invalidate_cache()  # Clear cache after save
```

**3. Web API Endpoints** (`app/webapi/routes/menu_layout.py`)

```
PUT /menu-layout → MenuLayoutUpdateRequest
    - config = await MenuLayoutService.get_config(db)
    - config['rows'] = payload.rows
    - config['buttons'] = payload.buttons
    - await MenuLayoutService.save_config(db, config)
        → upsert_system_setting + commit + invalidate_cache()

PATCH /menu-layout/buttons/{button_id} → ButtonUpdateRequest
    - Modifies single button in config
    - Calls: save_config() → invalidates cache

POST /menu-layout/rows → AddRowRequest
    - Adds new row to config
    - Calls: save_config() → invalidates cache
```

**4. Bot Usage** (`app/keyboards/inline.py` and menu handlers)

```python
async def get_main_menu_keyboard_async(db, user, texts) -> InlineKeyboardMarkup:
    # Gets menu layout config
    config = await MenuLayoutService.get_config(db)
    
    # Builds buttons from config
    # Applies user conditions (admin, subscriber status, etc.)
    # Returns InlineKeyboardMarkup
```

**Cache Invalidation Flow**:

```
1. Admin modifies menu layout in panel
2. HTTP request hits PUT /menu-layout
3. Endpoint calls MenuLayoutService.save_config(db, updated_config)
4. save_config() calls:
   - upsert_system_setting(db, MENU_LAYOUT_CONFIG_KEY, json_config)
   - db.commit()
   - cls.invalidate_cache()  → _cache = None
5. Next menu request calls get_config(db)
6. Sees _cache is None, reloads from SystemSetting table
7. Bot shows updated menu to user
```

---

## Part 6: Cache Mechanisms - Detailed Analysis

### In-Memory Caches (Process-Level)

| Service | Cache Variable | TTL | Invalidation Trigger |
|---------|----------------|-----|----------------------|
| `MainMenuButtonService` | `_cache: list[_MainMenuButtonData]` | ∞ (until invalidation) | `invalidate_cache()` on CRUD |
| `MenuLayoutService` | `_cache: dict` | ∞ (until invalidation) | `invalidate_cache()` on save |
| `SystemSettings` | `settings` singleton | ∞ (until reload) | Manual refresh or restart |

### Redis Caches (Distributed)

**Cache Service** (`app/utils/cache.py`)

```python
class CacheService:
    async def connect(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def get(key: str) -> Any | None
    async def set(key: str, value: Any, expire: int | timedelta = None) -> bool
    async def delete(key: str) -> bool
    async def delete_pattern(pattern: str) -> int
```

**Key Patterns Used**:

```
user:{user_id}                    → User session data (TTL: 3600s)
session:{user_id}:{session_key}   → User FSM state (TTL: 1800s)
channel_sub:{telegram_id}:{channel_id} → Channel subscription cache (TTL: 600s)
required_channels:active          → Active required channels (TTL: 60s)
rate_limit:{user_id}:{action}     → Rate limit counter (TTL: window)
system:stats                      → System statistics (TTL: 300s)
remnawave:nodes                   → Node status list (TTL: 60s)
stats:daily:{date}                → Daily statistics (TTL: 86400s)
```

**Pattern: Channel Subscription Cache**

```python
class ChannelSubCache:
    SUB_TTL = 600  # 10 min
    CHANNELS_TTL = 60  # 1 min
    
    @staticmethod
    async def set_sub_status(telegram_id: int, channel_id: str, is_member: bool):
        key = cache_key('channel_sub', telegram_id, channel_id)
        await cache.set(key, 1 if is_member else 0, expire=600)
    
    @staticmethod
    async def invalidate_channels():
        await cache.delete('required_channels:active')
```

**When does Redis get invalidated?**
- Channel list changes: Manual invalidation call
- User subscription status: Automatic TTL expiry or manual delete
- No application-wide cache clear mechanism observed

---

## Part 7: Synchronization Between Bot and Admin Panel

### Current Implementation

**Direct Database Pattern**:
```
Admin changes data in panel
    ↓
Web API endpoint persists to database
    ↓
Invalidates in-memory service cache (if applicable)
    ↓
Bot queries database on next user interaction
    ↓
Fresh data is retrieved and displayed
```

### Sync Timing

| Data Type | Load Strategy | Sync Time | Note |
|-----------|---------------|-----------|------|
| Welcome Text | Direct DB read on `/start` | Immediate (next /start) | No cache |
| Menu Buttons | Service cache + DB | Next menu query (seconds) | Cache invalidated |
| Menu Layout | Service cache + DB | Next menu query (seconds) | Cache invalidated |
| Tariff Prices | Config + DB lookup | On pricing calculation | No caching |
| System Settings | Singleton in-memory | **REQUIRES RESTART** | ⚠️ Problem area |
| Channel Status | Redis + DB | 10 min (TTL) | Distributed cache |

### Problem Areas Identified

**1. System Settings NOT Invalidated**
   - Location: `app/services/system_settings_service.py`
   - Issue: `settings` object loaded at startup, no refresh mechanism
   - Solution Needed: Implement settings cache invalidation on PUT /config

**2. Distributed Deployment Issue**
   - In-memory caches are per-process
   - Multiple bot processes won't share `MainMenuButtonService._cache`
   - Solution: Move to Redis for distributed invalidation

**3. No Webhook-Based Invalidation**
   - Changes only invalidate cache if endpoints are called
   - No real-time push to bot instances
   - Solution: Implement Redis pub/sub for cross-instance invalidation

---

## Part 8: Subscription Pricing Calculation

### How Prices Are Fetched

**File**: `app/handlers/subscription/pricing.py`

```python
async def _prepare_subscription_summary(db_user, data, texts):
    # 1. Base period price from PERIOD_PRICES
    base_price_original = PERIOD_PRICES.get(period_days, 0)
    
    # 2. Traffic price (dynamic per config)
    traffic_price_per_month = settings.get_traffic_price(traffic_gb)
    
    # 3. Server/country prices (from DB)
    countries = await _get_available_countries(db_user.promo_group_id)
    for country in countries:
        server_price_per_month = country['price_kopeks']
    
    # 4. Device prices (from config)
    devices_price_per_month = additional_devices * settings.PRICE_PER_DEVICE
    
    # 5. Apply promo discounts from PromoGroup
    period_discount_percent = db_user.get_promo_discount('period', period_days)
```

**Price Sources**:
- `PERIOD_PRICES` (config dict, in-memory)
- `settings.get_traffic_price()` (config method)
- `settings.PRICE_PER_DEVICE` (config attribute)
- `PromoGroup.period_discounts` (database)
- `Country.price_kopeks` (database)

**Cache Strategy**: **NO CACHE** - All prices computed fresh on demand from config/DB

---

## Part 9: Code Patterns for Cache Invalidation

### Pattern 1: Class-Level In-Memory Cache (MainMenuButtonService)

```python
class MainMenuButtonService:
    _cache: list[_MainMenuButtonData] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
    
    @classmethod
    async def _load_cache(cls, db):
        if cls._cache is not None:
            return cls._cache
        async with cls._lock:
            if cls._cache is not None:
                return cls._cache
            # Load from DB
            cls._cache = items
            return items
```

**Invalidation Call**:
```python
# In endpoint handler
await crud.update_main_menu_button(db, button, **update_payload)
MainMenuButtonService.invalidate_cache()
return _serialize(button)
```

### Pattern 2: Singleton Service (BotConfigurationService)

```python
# Global instance
bot_configuration_service = BotConfigurationService()

# Get value (no caching)
value = bot_configuration_service.get_current_value(key)

# Set value (persists to DB)
await bot_configuration_service.set_value(db, key, value)
```

**Problem**: No mechanism to refresh in-memory settings after DB change

### Pattern 3: Direct DB Reads (WelcomeText)

```python
# On every /start
welcome_text = await get_active_welcome_text(db)

# No caching layer - always fresh
```

**Benefit**: Guaranteed consistency
**Drawback**: More DB queries

### Pattern 4: Redis Cache with TTL (ChannelSubCache)

```python
@staticmethod
async def set_sub_status(telegram_id: int, channel_id: str, is_member: bool):
    key = cache_key('channel_sub', telegram_id, channel_id)
    await cache.set(key, value, expire=600)  # 10 min TTL

# Cache expires automatically after 10 minutes
```

---

## Part 10: Complete Sync Flow Examples

### Example 1: Updating Menu Button Text

```
STEP 1: Admin Panel
  - Opens button editor
  - Changes text "Subscribe" → "Buy Now"
  - Clicks Save

STEP 2: Web API (PATCH /main-menu-buttons/{id})
  - Receives ButtonUpdateRequest with text="Buy Now"
  - Gets button from DB
  - Updates: button.text = "Buy Now"
  - Commits to database
  - Calls: MainMenuButtonService.invalidate_cache()
    → Sets _cache = None
  
STEP 3: Bot Cache State
  - _cache = None (invalidated)
  - Next user query triggers reload
  
STEP 4: User Interaction
  - User clicks /menu or callback
  - Handler calls: MainMenuButtonService.get_buttons_for_user(db, ...)
  - Service sees _cache is None
  - Async with lock: Reloads from DB
  - Returns buttons with new text "Buy Now"
  - User sees updated button
  
TIME: ~200-500ms from admin save to user sees change
```

### Example 2: Updating Price Settings

```
STEP 1: Admin Panel
  - Opens Settings → Subscription Prices
  - Changes PRICE_30_DAYS: 199 → 249 kopeks
  - Clicks Save

STEP 2: Web API (PUT /config/PRICE_30_DAYS)
  - Receives SettingUpdateRequest with value=249
  - Validates type (int)
  - Calls: bot_configuration_service.set_value(db, "PRICE_30_DAYS", 249)
    → Updates/inserts SystemSetting row
  - db.commit()
  ❌ NO cache invalidation called
  
STEP 3: Bot Settings State
  - PERIOD_PRICES dict in memory still has {30: 199}
  - settings.PRICE_30_DAYS still returns 199
  
STEP 4: User Tries to Buy
  - Pricing calculation reads PERIOD_PRICES.get(30) → 199
  - User still sees old price
  
⚠️ PROBLEM: Change not reflected until bot restart
```

### Example 3: Changing Welcome Text

```
STEP 1: Admin Panel
  - Opens Welcome Texts
  - Edits active text
  - Clicks Save

STEP 2: Web API (PATCH /welcome-texts/{id})
  - Receives WelcomeTextUpdateRequest
  - Gets welcome_text from DB by ID
  - Updates: welcome_text.text_content = new_text
  - Updates: welcome_text.is_active = True
  - Marks other texts as is_active = False
  - db.commit()
  - No cache to invalidate ✓
  
STEP 3: User Sends /start
  - Handler calls: get_welcome_text_for_user(db, user)
  - Queries DB: SELECT * FROM welcome_text WHERE is_active=True
  - Gets new text immediately
  - Replaces placeholders
  - Sends to user
  
TIME: Immediate on next /start (no caching delay)
```

---

## Part 11: Redis Key Names & Patterns

### Pattern Breakdown

```
cache_key(*parts) -> ':'.join(str(part) for part in parts)

Examples:
  cache_key('user', 123) → 'user:123'
  cache_key('session', 123, 'checkout') → 'session:123:checkout'
  cache_key('channel_sub', 456, 'channel_789') → 'channel_sub:456:channel_789'
```

### All Redis Keys Used

| Key Pattern | TTL | Purpose | Class |
|-------------|-----|---------|-------|
| `user:{user_id}` | 3600s | User cached data | `UserCache` |
| `session:{user_id}:{session_key}` | 1800s | FSM state | `UserCache` |
| `system:stats` | 300s | System statistics | `SystemCache` |
| `remnawave:nodes` | 60s | Node status | `SystemCache` |
| `stats:daily:{date}` | 86400s | Daily stats | `SystemCache` |
| `rate_limit:{user_id}:{action}` | window | Rate limit | `RateLimitCache` |
| `channel_sub:{user_id}:{channel_id}` | 600s | Channel sub status | `ChannelSubCache` |
| `required_channels:active` | 60s | Active channels list | `ChannelSubCache` |

---

## Part 12: Summary Table: Data Sync Mechanisms

| Component | Storage | Cache Type | Invalidation | Sync Time | Issues |
|-----------|---------|-----------|--------------|-----------|--------|
| Welcome Text | DB table | None | N/A | Immediate | ✓ Good |
| Menu Buttons | DB table | In-mem class | Endpoint call | ~0.5s | ✓ Good |
| Menu Layout | SystemSetting (JSON) | In-mem class | Endpoint call | ~0.5s | ✓ Good |
| Tariff Prices | Tariff table | None | N/A | Immediate | ✓ Good |
| System Settings | SystemSetting table | Singleton in-mem | ❌ NONE | **RESTART** | ⚠️ **BROKEN** |
| Channel Subs | Redis + DB | Redis + TTL | TTL expiry | 10 min | ⚠️ Delayed |
| User Sessions | Redis | Redis + TTL | TTL expiry | 30 min | ⚠️ Delayed |

---

## Part 13: Recommended Improvements for Current Project

### For System Settings (CRITICAL)

**Current State**: Settings changes require restart

**Solution**:
1. Add cache invalidation endpoint
2. Implement Redis cache for settings (with TTL of 1-5 min)
3. Subscribe to settings change events
4. Reload affected config sections

```python
class BotConfigurationService:
    _redis_cache_key = 'bot:config:'
    
    async def set_value(self, db, key, value):
        # Persist to DB
        await upsert_system_setting(db, key, value)
        # Invalidate Redis cache
        await cache.delete(f'{self._redis_cache_key}{key}')
        # Reload into singleton settings object
        self._reload_setting(key)
```

### For Distributed Deployments

**Problem**: Multiple bot processes don't share `_cache`

**Solution**: Use Redis pub/sub for cache invalidation broadcast

```python
class MainMenuButtonService:
    CACHE_INVALIDATION_CHANNEL = 'cache:menu_buttons:invalidate'
    
    @classmethod
    async def invalidate_cache(cls) -> None:
        cls._cache = None
        # Broadcast to all bot processes
        await redis_client.publish(
            cls.CACHE_INVALIDATION_CHANNEL,
            json.dumps({'timestamp': datetime.now().isoformat()})
        )
```

### For Real-Time Sync

**Problem**: Sync only happens on next user action

**Solution**: Send WebSocket notification to admin panel + bot instances

```python
# In endpoint after save
await MenuLayoutService.save_config(db, config)

# Notify all connected clients
await websocket_manager.broadcast({
    'type': 'menu_layout_updated',
    'updated_at': datetime.now().isoformat(),
})
```

---

## Conclusion

The remnawave-bedolaga bot implements a **solid sync architecture** based on:

✅ **What Works Well**:
- Explicit cache invalidation on CRUD endpoints
- Direct DB reads for frequently-changing data (welcome text, prices)
- In-memory caching with locks for UI elements (buttons, menu layout)
- Immediate sync on most admin changes (except settings)

⚠️ **What Needs Improvement**:
- System settings changes require restart
- No distributed cache invalidation (single-process issue)
- No real-time push notifications
- Channel subscription cache has 10-minute lag

The key principle: **Admin panel changes → Persist to DB → Invalidate cache → Bot reloads on next action**

