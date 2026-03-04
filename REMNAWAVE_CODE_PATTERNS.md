# REMNAWAVE: Sync Implementation - Code Patterns & Function Reference

## Quick Reference: Cache Invalidation Code

### Pattern 1: MainMenuButtonService Invalidation

**File**: `app/services/main_menu_button_service.py`

```python
class MainMenuButtonService:
    _cache: list[_MainMenuButtonData] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def invalidate_cache(cls) -> None:
        """Called after any CRUD operation"""
        cls._cache = None
    
    @classmethod
    async def _load_cache(cls, db: AsyncSession) -> list[_MainMenuButtonData]:
        """Lazy load from DB if cache miss"""
        if cls._cache is not None:
            return cls._cache  # Cache hit
        
        async with cls._lock:  # Thread-safe reload
            if cls._cache is not None:
                return cls._cache
            
            # Load from database
            result = await db.execute(
                select(MainMenuButton).order_by(
                    MainMenuButton.display_order.asc(),
                    MainMenuButton.id.asc(),
                )
            )
            items = []
            for record in result.scalars().all():
                # Parse and validate
                items.append(_MainMenuButtonData(
                    text=record.text.strip(),
                    action_type=MainMenuButtonActionType(record.action_type),
                    action_value=record.action_value.strip(),
                    visibility=MainMenuButtonVisibility(record.visibility),
                    is_active=bool(record.is_active),
                    display_order=int(record.display_order),
                ))
            
            cls._cache = items
            return items
```

**Usage in endpoints** (`app/webapi/routes/main_menu_buttons.py`):

```python
@router.post('')
async def create_main_menu_button_endpoint(
    payload: MainMenuButtonCreateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    button = await create_main_menu_button(
        db,
        text=payload.text,
        action_type=payload.action_type,
        action_value=payload.action_value,
        visibility=payload.visibility,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    MainMenuButtonService.invalidate_cache()  # ← INVALIDATE HERE
    return _serialize(button)

@router.patch('/{button_id}')
async def update_main_menu_button_endpoint(
    button_id: int,
    payload: MainMenuButtonUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    button = await get_main_menu_button_by_id(db, button_id)
    if not button:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    
    button = await update_main_menu_button(db, button, **payload.dict(exclude_unset=True))
    MainMenuButtonService.invalidate_cache()  # ← INVALIDATE HERE
    return _serialize(button)

@router.delete('/{button_id}')
async def delete_main_menu_button_endpoint(button_id: int, db: AsyncSession):
    button = await get_main_menu_button_by_id(db, button_id)
    if not button:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Not found')
    
    await delete_main_menu_button(db, button)
    MainMenuButtonService.invalidate_cache()  # ← INVALIDATE HERE
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

**Usage in handlers** (`app/handlers/start.py` and `app/handlers/menu.py`):

```python
async def show_main_menu(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    # Get buttons for user (hits cache or loads from DB)
    buttons = await MainMenuButtonService.get_buttons_for_user(
        db,
        is_admin=db_user.is_admin,
        has_active_subscription=has_active_subscription,
        subscription_is_active=subscription_is_active,
    )
    
    # Build keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
    
    # Send to user
    await callback.message.edit_text("Main menu", reply_markup=keyboard)
```

---

### Pattern 2: MenuLayoutService Invalidation

**File**: `app/services/menu_layout/service.py`

```python
class MenuLayoutService:
    _cache: dict[str, Any] | None = None
    _cache_updated_at: datetime | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    CACHE_KEY = 'MENU_LAYOUT_CONFIG'
    
    @classmethod
    def invalidate_cache(cls) -> None:
        """Clear cache after config update"""
        cls._cache = None
        cls._cache_updated_at = None
    
    @classmethod
    async def get_config(cls, db: AsyncSession) -> dict[str, Any]:
        """Get menu layout config (with caching)"""
        if cls._cache is not None:
            return cls._cache
        
        async with cls._lock:
            if cls._cache is not None:
                return cls._cache
            
            # Load from database
            result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == cls.CACHE_KEY
                )
            )
            setting = result.scalar_one_or_none()
            
            if setting and setting.value:
                cls._cache = json.loads(setting.value)
            else:
                cls._cache = copy.deepcopy(DEFAULT_MENU_CONFIG)
            
            return cls._cache
    
    @classmethod
    async def save_config(cls, db: AsyncSession, config: dict[str, Any]) -> None:
        """Save config to DB and invalidate cache"""
        await upsert_system_setting(
            db,
            key=cls.CACHE_KEY,
            value=json.dumps(config),
        )
        await db.commit()
        cls.invalidate_cache()  # ← INVALIDATE HERE

    @classmethod
    async def get_config_updated_at(cls, db: AsyncSession) -> datetime | None:
        """Get when config was last updated"""
        result = await db.execute(
            select(SystemSetting.updated_at).where(
                SystemSetting.key == cls.CACHE_KEY
            )
        )
        return result.scalar_one_or_none()
```

**Usage in endpoints** (`app/webapi/routes/menu_layout.py`):

```python
@router.put('')
async def update_menu_layout(
    payload: MenuLayoutUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MenuLayoutResponse:
    """Update menu layout (rows and buttons)"""
    config = await MenuLayoutService.get_config(db)
    config = config.copy()  # Don't modify cached dict
    
    if payload.rows is not None:
        config['rows'] = [row.model_dump() for row in payload.rows]
    
    if payload.buttons is not None:
        buttons_config = {}
        for btn_id, btn in payload.buttons.items():
            btn_dict = btn.model_dump()
            buttons_config[btn_id] = btn_dict
        config['buttons'] = buttons_config
    
    await MenuLayoutService.save_config(db, config)  # ← SAVES & INVALIDATES
    updated_at = await MenuLayoutService.get_config_updated_at(db)
    return _serialize_config(config, settings.MENU_LAYOUT_ENABLED, updated_at)

@router.patch('/buttons/{button_id}')
async def update_button(
    button_id: str,
    payload: ButtonUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Update single button config"""
    config = await MenuLayoutService.get_config(db)
    config = config.copy()
    
    if button_id not in config['buttons']:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Button not found')
    
    # Update button
    btn_updates = payload.model_dump(exclude_unset=True)
    config['buttons'][button_id].update(btn_updates)
    
    await MenuLayoutService.save_config(db, config)  # ← SAVES & INVALIDATES
    return config['buttons'][button_id]

@router.post('/rows')
async def add_row(
    payload: AddRowRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Add new menu row"""
    config = await MenuLayoutService.get_config(db)
    config = config.copy()
    
    new_row = payload.model_dump()
    config['rows'].append(new_row)
    
    await MenuLayoutService.save_config(db, config)  # ← SAVES & INVALIDATES
    return new_row
```

---

## Redis Cache Pattern

**File**: `app/utils/cache.py`

```python
class CacheService:
    def __init__(self):
        self.redis_client: redis.Redis | None = None
        self._connected = False
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            self._connected = True
            logger.info('✅ Redis connected')
        except Exception as e:
            logger.warning('⚠️ Redis connection failed', error=e)
            self._connected = False
    
    async def get(self, key: str) -> Any | None:
        """Retrieve value from Redis"""
        if not self._connected:
            return None
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)  # Deserialize
            return None
        except Exception as e:
            logger.error('Redis GET failed', key=key, error=e)
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: int | timedelta = None
    ) -> bool:
        """Store value in Redis with optional TTL"""
        if not self._connected:
            return False
        try:
            serialized_value = json.dumps(value, default=str)
            
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            await self.redis_client.set(
                key, 
                serialized_value, 
                ex=expire  # Expiration in seconds
            )
            return True
        except Exception as e:
            logger.error('Redis SET failed', key=key, error=e)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self._connected:
            return False
        try:
            deleted = await self.redis_client.delete(key)
            return deleted > 0
        except Exception as e:
            logger.error('Redis DELETE failed', key=key, error=e)
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._connected:
            return 0
        try:
            keys = await self.redis_client.keys(pattern)
            if not keys:
                return 0
            deleted = await self.redis_client.delete(*keys)
            return int(deleted)
        except Exception as e:
            logger.error('Redis KEYS/DELETE failed', pattern=pattern, error=e)
            return 0

# Global instance
cache = CacheService()

def cache_key(*parts) -> str:
    """Build Redis key from parts"""
    return ':'.join(str(part) for part in parts)
```

**Channel Subscription Cache** (`app/utils/cache.py`):

```python
class ChannelSubCache:
    SUB_TTL = 600  # 10 minutes
    CHANNELS_TTL = 60  # 1 minute
    
    @staticmethod
    async def get_sub_status(telegram_id: int, channel_id: str) -> bool | None:
        """Get channel subscription status from cache
        
        Returns:
            True: user is subscribed
            False: user is not subscribed
            None: cache miss
        """
        key = cache_key('channel_sub', telegram_id, channel_id)
        result = await cache.get(key)
        if result is None:
            return None
        return result == 1
    
    @staticmethod
    async def set_sub_status(
        telegram_id: int, 
        channel_id: str, 
        is_member: bool
    ) -> None:
        """Cache user's channel subscription status
        
        Args:
            telegram_id: User's Telegram ID
            channel_id: Channel to check
            is_member: True if user is member, False otherwise
        """
        key = cache_key('channel_sub', telegram_id, channel_id)
        await cache.set(key, 1 if is_member else 0, expire=ChannelSubCache.SUB_TTL)
    
    @staticmethod
    async def invalidate_sub(telegram_id: int, channel_id: str) -> None:
        """Manually clear channel subscription cache"""
        key = cache_key('channel_sub', telegram_id, channel_id)
        await cache.delete(key)
    
    @staticmethod
    async def get_required_channels() -> list[dict] | None:
        """Get list of channels that are currently required"""
        return await cache.get('required_channels:active')
    
    @staticmethod
    async def set_required_channels(channels: list[dict]) -> None:
        """Cache list of required channels"""
        await cache.set('required_channels:active', channels, expire=ChannelSubCache.CHANNELS_TTL)
    
    @staticmethod
    async def invalidate_channels() -> None:
        """Clear required channels cache"""
        await cache.delete('required_channels:active')
```

---

## Welcome Text Pattern (Direct DB Reads)

**File**: `app/database/crud/welcome_text.py`

```python
async def get_active_welcome_text(db: AsyncSession) -> str | None:
    """Get currently active welcome text from database
    
    No caching - always reads fresh from DB
    """
    result = await db.execute(
        select(WelcomeText)
        .where(WelcomeText.is_active == True)
        .where(WelcomeText.is_enabled == True)
        .order_by(WelcomeText.updated_at.desc())
    )
    welcome_text = result.scalar_one_or_none()
    
    if welcome_text:
        return welcome_text.text_content
    
    return None

async def get_welcome_text_for_user(
    db: AsyncSession, 
    user
) -> str:
    """Get welcome text with placeholders replaced for specific user"""
    welcome_text = await get_active_welcome_text(db)
    
    if not welcome_text:
        return None
    
    # Replace placeholders
    return replace_placeholders(welcome_text, user)

def replace_placeholders(text: str, user) -> str:
    """Replace dynamic placeholders in welcome text
    
    Placeholders:
    - {user_name}: Name or username (priority: name → username → "друг")
    - {first_name}: Only name (or "друг")
    - {username}: @username or name
    - {username_clean}: username without @
    """
    first_name = getattr(user, 'first_name', None)
    username = getattr(user, 'username', None)
    
    first_name = first_name.strip() if first_name else None
    username = username.strip() if username else None
    
    user_name = first_name or username or 'друг'
    display_first_name = first_name or 'друг'
    display_username = f'@{username}' if username else (first_name or 'друг')
    clean_username = username or first_name or 'друг'
    
    replacements = {
        '{user_name}': user_name,
        '{first_name}': display_first_name,
        '{username}': display_username,
        '{username_clean}': clean_username,
    }
    
    result = text
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result
```

**Usage in handler** (`app/handlers/start.py`):

```python
async def handle_start(message: types.Message, db: AsyncSession):
    # Get active welcome text (fresh from DB)
    welcome_text = await get_welcome_text_for_user(db, message.from_user)
    
    if welcome_text:
        await message.answer(welcome_text)
    else:
        # Fallback if no welcome text configured
        await message.answer("Welcome!")
```

---

## System Settings Pattern (PROBLEMATIC)

**File**: `app/services/system_settings_service.py` & `app/config.py`

```python
# In config.py - loaded at startup
class Settings:
    def __init__(self):
        # Load from environment variables
        self.PRICE_30_DAYS = int(os.getenv('PRICE_30_DAYS', '199'))
        self.PRICE_60_DAYS = int(os.getenv('PRICE_60_DAYS', '299'))
        # ... more settings
    
    def get_traffic_price(self, traffic_gb: int) -> int:
        """Get traffic price in kopeks"""
        if traffic_gb == 0:
            return 0
        return traffic_gb * self.TRAFFIC_PRICE_PER_GB

# Global singleton
settings = Settings()
```

**Issue**: Settings loaded at startup, not refreshed

**Web API to update settings** (`app/webapi/routes/config.py`):

```python
@router.put('/{key}')
async def update_setting(
    key: str,
    payload: SettingUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SettingDefinition:
    """Update a setting (persists to DB but doesn't reload singleton)"""
    try:
        definition = bot_configuration_service.get_definition(key)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Setting not found')
    
    # Validate and coerce value
    value = _coerce_value(key, payload.value)
    
    # Persist to database
    try:
        await bot_configuration_service.set_value(db, key, value)
    except ReadOnlySettingError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Read-only setting')
    
    await db.commit()
    
    # ⚠️ BUG: No cache invalidation!
    # The global 'settings' object still has old values
    # Bot won't see the change until restart
    
    return _serialize_definition(definition)
```

**Problem Code Flow**:

```
1. Admin changes PRICE_30_DAYS to 249 in panel
2. PUT /config/PRICE_30_DAYS with value=249
3. Endpoint calls: await bot_configuration_service.set_value(db, "PRICE_30_DAYS", 249)
4. Database updated: SystemSetting(key="PRICE_30_DAYS", value="249")
5. db.commit()
6. ❌ NO RELOAD of settings singleton
7. settings.PRICE_30_DAYS still = 199
8. Next pricing calculation reads stale value

FIX NEEDED:
- Add settings.reload_from_db(key)
- Or: Implement Redis cache for settings with short TTL
- Or: Implement webhook/pub-sub to notify bot of setting changes
```

---

## Tariff Pricing Pattern (Direct DB)

**File**: `app/handlers/subscription/pricing.py`

```python
async def _prepare_subscription_summary(
    db_user: User,
    data: dict[str, Any],
    texts,
) -> tuple[str, dict[str, Any]]:
    """Calculate subscription price with all components
    
    Reads prices fresh from config/DB on each call
    """
    period_days = data['period_days']
    
    # 1. Base period price (from in-memory PERIOD_PRICES)
    base_price_original = PERIOD_PRICES.get(period_days, 0)
    
    # 2. Apply period discount from promo group
    period_discount_percent = db_user.get_promo_discount('period', period_days)
    base_price, base_discount_total = apply_percentage_discount(
        base_price_original,
        period_discount_percent,
    )
    
    # 3. Traffic price (from config method call)
    if settings.is_traffic_fixed():
        traffic_limit = settings.get_fixed_traffic_limit()
        traffic_price_per_month = settings.get_traffic_price(traffic_limit)
        final_traffic_gb = traffic_limit
    else:
        traffic_gb = data.get('traffic_gb', 0)
        traffic_price_per_month = settings.get_traffic_price(traffic_gb)
        final_traffic_gb = traffic_gb
    
    # 4. Server/country prices (from DB)
    countries = await _get_available_countries(db_user.promo_group_id)
    countries_price_per_month = 0
    
    selected_country_ids = set(data.get('countries', []))
    for country in countries:
        if country['uuid'] in selected_country_ids:
            countries_price_per_month += country['price_kopeks']
    
    # 5. Device price (from config)
    devices_price_per_month = (
        (data.get('devices', 0) - settings.DEFAULT_DEVICE_LIMIT) 
        * settings.PRICE_PER_DEVICE
    )
    
    # 6. Total
    total_price = (
        base_price 
        + traffic_price_per_month 
        + countries_price_per_month 
        + devices_price_per_month
    )
    
    return summary_text, summary_data
```

**Key Point**: All prices computed fresh on demand - no intermediate caching

---

## Database Connection Pattern

**File**: `app/database/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db_session() -> AsyncSession:
    """Dependency for FastAPI endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Usage in endpoints**:

```python
@router.get('')
async def list_items(
    db: AsyncSession = Depends(get_db_session),
):
    """Each request gets fresh session"""
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return items
```

---

## Complete Example: Adding New Cached Data Type

If you wanted to add caching for a new entity (like FAQ items), follow this pattern:

```python
# 1. Create service with cache
class FaqService:
    _cache: list[FaqItem] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
    
    @classmethod
    async def get_all(cls, db: AsyncSession) -> list[FaqItem]:
        if cls._cache is not None:
            return cls._cache
        
        async with cls._lock:
            if cls._cache is not None:
                return cls._cache
            
            result = await db.execute(select(FaqItem).where(FaqItem.is_active == True))
            cls._cache = result.scalars().all()
            return cls._cache

# 2. Add invalidation to endpoints
@router.post('/faq')
async def create_faq(payload: FaqCreateRequest, db: AsyncSession):
    item = await create_faq_item(db, **payload.dict())
    FaqService.invalidate_cache()  # ← INVALIDATE
    return item

@router.patch('/faq/{item_id}')
async def update_faq(item_id: int, payload: FaqUpdateRequest, db: AsyncSession):
    item = await update_faq_item(db, item_id, **payload.dict(exclude_unset=True))
    FaqService.invalidate_cache()  # ← INVALIDATE
    return item

# 3. Use in handlers
async def show_faq(message: types.Message, db: AsyncSession):
    faqs = await FaqService.get_all(db)  # Hits cache or loads from DB
    # Display to user
```

---

## Testing Cache Invalidation

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test that cache is properly invalidated"""
    db = AsyncSessionLocal()
    
    # Initial load
    buttons1 = await MainMenuButtonService.get_buttons_for_user(
        db, is_admin=False, has_active_subscription=False, subscription_is_active=False
    )
    assert len(buttons1) > 0
    
    # Cache should be populated
    assert MainMenuButtonService._cache is not None
    
    # Invalidate
    MainMenuButtonService.invalidate_cache()
    assert MainMenuButtonService._cache is None
    
    # Next load should hit DB again
    buttons2 = await MainMenuButtonService.get_buttons_for_user(
        db, is_admin=False, has_active_subscription=False, subscription_is_active=False
    )
    assert len(buttons2) > 0
    assert MainMenuButtonService._cache is not None
```

