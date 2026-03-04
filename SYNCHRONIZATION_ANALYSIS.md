# RemnaWave Bot ↔ Admin-Panel Synchronization - CODE-LEVEL ANALYSIS

## EXECUTIVE SUMMARY

The reference project uses a **hybrid caching strategy**:
- **In-Memory Python caches** for MainMenuButton and MenuLayout (no TTL, manual invalidation)
- **Redis caches** for user data and transient data (TTL-based)
- **DB-only** for Welcome Text and Tariffs (no caching, always fresh)
- **Startup memory** for System Settings (NO invalidation - requires bot restart!)

**Key Finding:** Cache invalidation is **INCONSISTENT**. Main menu buttons properly invalidate, but system settings do NOT.

---

## 1. CACHE IMPLEMENTATION PATTERNS

### Cache Service (`app/utils/cache.py`)

**Redis Connection:**
```python
class CacheService:
    redis_client: redis.Redis | None
    _connected: bool
    
    async def connect()  # On startup
    async def disconnect()  # On shutdown
```

**Helper function:**
```python
def cache_key(*parts) -> str:
    return ':'.join(str(part) for part in parts)
    # Example: cache_key('user', 123, 'data') → 'user:123:data'
```

**Cache Classes:**
- `UserCache` - User data (3600s), sessions (1800s)
- `SystemCache` - Stats (300s), nodes (60s)
- `ChannelSubCache` - Subscriptions (600s for user, 60s for channel list)
- `RateLimitCache` - Rate limiting with configurable window

**Graceful Degradation:**
```python
if not self._connected:
    return None  # Cache miss if Redis down
```

---

## 2. WELCOME TEXT SYNCHRONIZATION

### Database Model
```python
class WelcomeText(Base):
    text_content: str
    is_active: bool  # Only ONE active at a time
    is_enabled: bool  # Global on/off toggle
    created_by: int (FK User)
```

### CRUD Operations - NO CACHING
```python
async def get_active_welcome_text(db) -> str | None:
    # SELECT from welcome_texts WHERE is_active=True AND is_enabled=True
    # Returns: .text_content only
    
async def get_current_welcome_text_settings(db) -> dict:
    # Returns: {text, is_enabled, id}
    
async def set_welcome_text(db, text_content: str, admin_id: int) -> bool:
    # Deactivates ALL existing texts
    # Creates new WelcomeText(is_active=True)
```

### Bot Usage
```python
# handlers/start.py, handlers/menu.py
welcome_text = await get_active_welcome_text(db)
final_text = replace_placeholders(welcome_text, user)
await message.answer(final_text)
```

### Admin API - NO CACHE INVALIDATION
```python
# webapi/routes/welcome_texts.py
@router.post('')
async def create_welcome_text_endpoint(payload, db):
    created = await create_welcome_text(db, ...)
    # NO CACHE INVALIDATION - direct DB write
    return _serialize(created)
```

**Status:** ✅ SYNCED (DB-only, no cache layer to invalidate)

---

## 3. MAIN MENU BUTTONS SYNCHRONIZATION

### Database Model
```python
class MainMenuButton(Base):
    text: str
    action_type: enum (URL | MINI_APP)
    action_value: str  # The URL or app link
    visibility: enum (ALL | ADMINS | SUBSCRIBERS)
    is_active: bool
    display_order: int
```

### In-Memory Cache Service
```python
class MainMenuButtonService:
    _cache: list[_MainMenuButtonData] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    async def _load_cache(cls, db):
        if cls._cache is not None:
            return cls._cache  # Fast return
        
        async with cls._lock:
            # Load from DB
            stmt = select(MainMenuButton).order_by(
                MainMenuButton.display_order.asc(),
                MainMenuButton.id.asc()
            )
            result = await db.execute(stmt)
            
            # Build _MainMenuButtonData dataclass list
            items = []
            for record in result.scalars().all():
                items.append(_MainMenuButtonData(
                    text=record.text.strip(),
                    action_type=MainMenuButtonActionType(record.action_type),
                    action_value=record.action_value.strip(),
                    visibility=MainMenuButtonVisibility(record.visibility),
                    is_active=bool(record.is_active),
                    display_order=int(record.display_order)
                ))
            
            cls._cache = items
            return items
    
    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
    
    @classmethod
    async def get_buttons_for_user(cls, db, *, is_admin, has_active_subscription):
        data = await cls._load_cache(db)
        
        buttons = []
        for item in data:
            # Filter 1: is_active
            if not item.is_active:
                continue
            
            # Filter 2: visibility checks
            if item.visibility == Visibility.ADMINS and not is_admin:
                continue
            if item.visibility == Visibility.SUBSCRIBERS and not has_active_subscription:
                continue
            
            # Filter 3: referral program check
            if not settings.is_referral_program_enabled():
                if 'partner' in item.text.lower() or 'referr' in item.text.lower():
                    continue
            
            # Build button
            button = cls._build_button(item)
            if button:
                buttons.append(button)
        
        return buttons
    
    @staticmethod
    def _build_button(item):
        if item.action_type == MainMenuButtonActionType.URL:
            return InlineKeyboardButton(text=item.text, url=item.action_value)
        
        if item.action_type == MainMenuButtonActionType.MINI_APP:
            return InlineKeyboardButton(
                text=item.text,
                web_app=types.WebAppInfo(url=item.action_value)
            )
        
        return None
```

### Admin API with Cache Invalidation ✓
```python
# webapi/routes/main_menu_buttons.py
@router.post('')
async def create_main_menu_button_endpoint(payload, db):
    button = await create_main_menu_button(db, ...)
    MainMenuButtonService.invalidate_cache()  # ✓ CORRECT
    return _serialize(button)

@router.patch('/{button_id}')
async def update_main_menu_button_endpoint(button_id, payload, db):
    button = await update_main_menu_button(db, button, **updates)
    MainMenuButtonService.invalidate_cache()  # ✓ CORRECT
    return _serialize(button)

@router.delete('/{button_id}')
async def delete_main_menu_button_endpoint(button_id, db):
    await delete_main_menu_button(db, button)
    MainMenuButtonService.invalidate_cache()  # ✓ CORRECT
    return Response(status_code=204)
```

### Bot Usage
```python
# handlers/menu.py
custom_buttons = []
if not settings.is_text_main_menu_mode():
    custom_buttons = await MainMenuButtonService.get_buttons_for_user(
        db,
        is_admin=is_admin,
        has_active_subscription=has_active_subscription,
        subscription_is_active=subscription_is_active
    )

keyboard = await get_main_menu_keyboard_async(..., custom_buttons=custom_buttons)
```

**Status:** ✅ PROPERLY SYNCED (cache invalidation implemented correctly)

---

## 4. SYSTEM SETTINGS SYNCHRONIZATION

### Storage Model
```python
class SystemSetting(Base):
    key: str (unique)
    value: str | None
    description: str | None
```

### Access Pattern - NO REDIS, STARTUP MEMORY ONLY
```python
# app/config.py on startup:
class Settings:
    DEFAULT_DEVICE_LIMIT: int = env.int('DEFAULT_DEVICE_LIMIT', 1)
    SUPPORT_USERNAME: str = env.str('SUPPORT_USERNAME', '')
    TRIAL_DURATION_DAYS: int = env.int('TRIAL_DURATION_DAYS', 3)
    # ... etc - all loaded from .env at startup
```

**BotConfigurationService** provides admin UI but:
```python
class BotConfigurationService:
    # Settings can be STORED in DB via SystemSetting table
    # But bot still reads from in-memory `settings` object
    # ⚠️ NO mechanism to reload settings without restarting bot
```

### Bot Usage
```python
# Any handler:
if settings.is_support_ticket_enabled():
    show_support_button()

default_limit = settings.DEFAULT_DEVICE_LIMIT
# These values are FIXED at bot startup
```

### Admin API - NO CACHE INVALIDATION
```python
# Admin can update SystemSetting in DB
# But bot doesn't see changes until restart ❌
```

**Status:** ❌ DESYNCHRONIZED (no reload mechanism)

---

## 5. TARIFF SYNCHRONIZATION

### Database Model
```python
class Tariff(Base):
    name: str
    description: str | None
    is_active: bool
    traffic_limit_gb: int
    device_limit: int
    period_prices: dict[str, int]  # {"14": 30000, "30": 50000}
    is_trial_available: bool
    tier_level: int
    # ... many more fields
```

### CRUD Operations - NO CACHING
```python
async def get_all_tariffs(db, *, include_inactive=False):
    query = select(Tariff).options(selectinload(Tariff.allowed_promo_groups))
    # Direct DB query, no cache
    return result.scalars().all()

async def get_tariff_by_id(db, tariff_id):
    # Direct DB query
    return result.scalars().first()

async def get_tariffs_for_user(db, promo_group_id=None):
    # Direct DB query, filters by promo group
    return available_tariffs
```

### Bot Usage
```python
# handlers/subscription/pricing.py
tariffs = await get_tariffs_for_user(
    db,
    promo_group_id=db_user.promo_group_id
)
# Reads fresh from DB every time ✓
```

### Admin API - NO CACHE INVALIDATION
```python
# webapi/routes/subscriptions.py
@router.post('')
async def create_subscription(payload, db):
    subscription = await create_paid_subscription(db, ...)
    # NO TARIFF CACHE INVALIDATION - direct DB write
    return _serialize(subscription)
```

**Status:** ✅ SYNCED (DB-only, no cache layer to invalidate)

---

## 6. MENU LAYOUT CONFIGURATION

### Storage
```python
# Stored in SystemSetting table:
SystemSetting(
    key='menu_layout_config',
    value='{"version":1,"rows":[...],"buttons":{...}}'
)
```

### In-Memory Cache
```python
class MenuLayoutService:
    _cache: dict[str, Any] | None = None
    _cache_updated_at: datetime | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    async def get_config(cls, db):
        if cls._cache is not None:
            return cls._cache
        
        async with cls._lock:
            result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == 'menu_layout_config'
                )
            )
            setting = result.scalar_one_or_none()
            
            if setting and setting.value:
                cls._cache = json.loads(setting.value)
            else:
                cls._cache = cls.get_default_config()
            
            return cls._cache
    
    @classmethod
    async def save_config(cls, db, config):
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        await upsert_system_setting(
            db,
            'menu_layout_config',
            config_json,
            description='...'
        )
        await db.commit()
        cls.invalidate_cache()  # ✓ CORRECT
    
    @classmethod
    async def update_button(cls, db, button_id, updates):
        config = await cls.get_config(db)
        buttons = config.get('buttons', {})
        buttons[button_id].update(updates)
        config['buttons'] = buttons
        await cls.save_config(db, config)  # Will invalidate cache ✓
```

**Status:** ✅ PROPERLY SYNCED (save_config invalidates after every change)

---

## 7. SYNCHRONIZATION GAPS SUMMARY

| Component | Cache Type | Invalidation | Status |
|-----------|-----------|--------------|--------|
| Welcome Text | None | N/A | ✅ Synced |
| Main Menu Buttons | In-Memory | Manual ✓ | ✅ Synced |
| System Settings | Startup Mem | ✗ Missing | ❌ BROKEN |
| Tariffs | None | N/A | ✅ Synced |
| Menu Layout | In-Memory | Manual ✓ | ✅ Synced |

---

## 8. PHOTOS/MEDIA HANDLING

### Current State - NO MEDIA SUPPORT
```python
# MainMenuButton model - NO photo field
class MainMenuButton(Base):
    text: str
    action_type: enum
    action_value: str
    # ❌ NO media_id or photo_url field
```

### How Bot Sends Messages
```python
# handlers/menu.py
await message.answer(menu_text)  # Text only, no photos
```

### Missing Implementation
No support for:
- Buttons with attached photos
- Dynamic URLs for media
- Media IDs from Telegram

**Recommendation:**
```python
class MainMenuButton(Base):
    photo_url: str | None = None
    media_id: str | None = None  # Telegram file_id
    
# Bot would then:
if button.photo_url:
    await message.answer_photo(photo=button.photo_url, caption=button.text)
else:
    await message.answer(button.text)
```

---

## 9. BUTTON BEHAVIOR PATTERNS

### URL and MINI_APP Types
```python
# URL button - direct link (opens browser/app immediately)
InlineKeyboardButton(text="Join", url="https://example.com")

# MINI_APP button - Telegram Mini App (opens within Telegram)
InlineKeyboardButton(
    text="Open App",
    web_app=types.WebAppInfo(url="https://app.example.com")
)
```

### Support/Channel Pattern
```python
# Support handled via settings (hardcoded or from config)
settings.SUPPORT_USERNAME  # "@support_bot"
settings.CHANNEL_URL  # Required subscription link

# NO special model for these - handled in handlers
# Check: handlers/start.py for channel subscription logic
```

---

## 10. CACHE KEY NAMING

```python
cache_key('user', user_id)  # 'user:123'
cache_key('session', user_id, 'key')  # 'session:123:key'
cache_key('channel_sub', telegram_id, channel_id)  # 'channel_sub:456:789'
cache_key('rate_limit', user_id, 'action')  # 'rate_limit:123:action'
cache_key('stats', 'daily', date)  # 'stats:daily:2024-01-15'
```

**In-Memory Caches** (no key names, just class variables):
```python
MainMenuButtonService._cache  # list of buttons
MenuLayoutService._cache  # dict of config
```

---

## CRITICAL FINDING FOR YOUR PROJECT

### System Settings are NOT synchronized!

**Current Flow:**
1. Bot starts → Reads settings from .env file
2. Admin changes setting in panel → Stored in DB (SystemSetting table)
3. Bot continues using OLD startup values ❌
4. **SOLUTION REQUIRED:** Implement periodic reload or webhook invalidation

**Recommended Fix:**
```python
class Settings:
    # Add method to reload from DB:
    async def reload_from_db(self, db: AsyncSession):
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key.like('%'))
        )
        for setting in result.scalars().all():
            if hasattr(self, setting.key.upper()):
                setattr(self, setting.key.upper(), setting.value)
    
    # Call periodically or via webhook:
    # Every 60 seconds or when admin makes changes
```

This is the **PRIMARY SYNCHRONIZATION ISSUE** to fix!
