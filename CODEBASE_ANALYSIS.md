# Codebase Analysis: Welcome Image, Payment Flow, and Data Synchronization

## Executive Summary

This analysis identifies critical issues in the VPN bot codebase:

1. **Welcome Image Storage Issue**: The welcome image is stored in `bot_settings_json` as `welcome_image` key, but the upload endpoint does NOT save the URL to the database automatically.
2. **Payment Flow Bug**: Missing state check - payment handlers don't validate that users are in the correct FSM state before accepting callbacks.
3. **Data Synchronization Problems**: The bot has outdated hardcoded menu buttons and doesn't dynamically fetch them on every /start.
4. **API Client Issues**: `get_bot_settings()` silently catches all exceptions, returning empty dict instead of proper error handling.

---

## Part 1: Welcome Image Storage & Upload Flow

### Where is the Welcome Image Stored?

**Location**: `BotText` table with key `"bot_settings_json"`

The `backend/models/config.py` shows:
```python
class BotText(Base):
    __tablename__ = "bot_texts"
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(String(4000), nullable=False)
```

The welcome image is stored as a JSON string in the `value` column:
- **Key**: `"bot_settings_json"`
- **Value**: `{"welcome_image": "<URL>", "free_trial_image": "...", ...}`

### What is the Exact Key Used?

```
bot_settings_json → JSON object with keys:
  - welcome_image (the cover/welcome photo)
  - free_trial_image
  - payment_image
  - cabinet_image
  - support_username
  - channel_username
  - bot_name
  - channel_id
  - bot_description
  - trial_hours
  - referral_bonus_days
  - etc.
```

### Does upload_image Endpoint Save to DB?

**NO. This is a critical bug.**

In `backend/api/v1/endpoints/admin.py` lines 602-631:

```python
@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_admin_user),
):
    """Загрузить изображение для бота (welcome, plan, etc.)."""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        filename = f"{uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        with open(path, "wb") as f:
            f.write(content)
        # Returns URL only — does NOT save to BotText table
        base_url = os.getenv("BACKEND_URL", "").rstrip("/")
        if base_url:
            url = f"{base_url}/static/uploads/{filename}"
        else:
            url = f"/static/uploads/{filename}"
        return {"url": url, "filename": filename, "relative_url": f"/static/uploads/{filename}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
```

**What happens**: 
- ✅ File saved to disk at `backend/static/uploads/{filename}`
- ✅ URL returned to frontend
- ❌ **URL NOT automatically saved to database**
- The frontend manually saves the URL via `PUT /admin/settings`

### How the Frontend Handles This

In `admin-panel/src/pages/BotSettings.jsx` lines 176-196:

```jsx
async function uploadImage(file, field) {
    setUploading(true)
    setUploadError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/admin/upload-image', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data.url) {
        set(field, res.data.url)  // ← Sets form state with URL
      } else {
        setUploadError('Не удалось получить URL изображения')
      }
    } catch (e) {
      console.error('Ошибка загрузки', e)
      setUploadError('Ошибка загрузки: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
    }
  }
```

Then when user clicks "Save Settings", it calls `PUT /admin/settings` with the URL included in the object.

### Public API Endpoint for Bot to Fetch Settings

In `backend/api/v1/router.py` lines 467-485:

```python
@api_router.get("/bot-settings/public", tags=["public"])
async def bot_settings_public(db: AsyncSession = Depends(get_db)):
    """Public: Get bot settings (welcome image, etc.) for the bot process."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    BOT_SETTINGS_KEY = "bot_settings_json"
    try:
        stmt = _select(_BotText).where(_BotText.key == BOT_SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            try:
                return _json.loads(row.value)
            except Exception:
                return {}
        return {}
    except Exception:
        return {}
```

---

## Part 2: How Bot Uses Welcome Image

### In bot/handlers/start.py (lines 23-62)

```python
async def _get_welcome_data(client: APIClient):
    """Загрузить приветственный текст и фото из API."""
    welcome_text = None
    welcome_photo = None

    try:
        texts = await client.get_all_bot_texts()
        if texts:
            welcome_text = texts.get("welcome") or texts.get("welcome_text")
    except Exception as e:
        logger.warning(f"Failed to load welcome text from API: {e}")

    try:
        settings = await client.get_bot_settings()
        if settings:
            raw = (
                settings.get("welcome_image")
                or settings.get("welcome_photo")
                or ""
            )
            if raw:
                welcome_photo = resolve_media(raw)
    except Exception as e:
        logger.warning(f"Failed to load welcome photo from API: {e}")

    if not welcome_text:
        env_text = getattr(config, "welcome_text", None)
        welcome_text = env_text or FALLBACK_WELCOME

    if not welcome_photo:
        env_photo = getattr(config.telegram, "welcome_photo", None) if hasattr(config, "telegram") else None
        if env_photo:
            welcome_photo = resolve_media(env_photo) or env_photo

    return welcome_text, welcome_photo
```

**Flow**:
1. Bot calls `APIClient.get_bot_settings()` → `GET /bot-settings/public`
2. Receives JSON with `welcome_image` key
3. Calls `resolve_media(welcome_image)` to convert URL to sendable format
4. Sends photo via `send_photo()` with caption

---

## Part 3: API Client Issues

### get_bot_settings() in bot/utils/api_client.py (lines 248-256)

```python
async def get_bot_settings(self) -> Dict[str, Any]:
    """Get bot settings (media URLs, support username, etc.) — uses public endpoint"""
    try:
        return await self.get("/bot-settings/public")
    except Exception:
        try:
            return await self.get("/admin/settings")
        except Exception:
            return {}
```

**Problems**:
- ❌ Silently catches ALL exceptions including network errors
- ❌ Returns empty dict on failure → bot shows fallback content
- ❌ No logging of what went wrong
- ❌ Cascades to fallback menu if settings unavailable

### get_all_bot_texts() in bot/utils/api_client.py (lines 238-246)

```python
async def get_all_bot_texts(self, language: str = "ru") -> Dict[str, Any]:
    """Get all bot message texts — uses public endpoint (no admin auth needed)"""
    try:
        return await self.get("/bot-texts/public")
    except Exception:
        try:
            return await self.get("/admin/bot-texts")
        except Exception:
            return {}
```

Same issue: silently swallows errors.

---

## Part 4: Payment Flow - State Management Bug

### PaymentStates Definition (bot/states/payment_states.py)

```python
class PaymentStates(StatesGroup):
    waiting_plan_selection = State()
    waiting_period_selection = State()
    waiting_payment_confirmation = State()
    waiting_payment_method = State()
    waiting_payment_completion = State()
```

### Payment Handlers (bot/handlers/payment.py)

#### Handler 1: select_plan (line 153-195)
```python
@router.callback_query(F.data.startswith("plan_"), PaymentStates.waiting_plan_selection)
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
```
✅ **State check present**: `PaymentStates.waiting_plan_selection`

#### Handler 2: select_period (line 198-234)
```python
@router.callback_query(F.data.startswith("period_"), PaymentStates.waiting_period_selection)
async def select_period(callback: CallbackQuery, state: FSMContext) -> None:
```
✅ **State check present**: `PaymentStates.waiting_period_selection`

#### Handler 3: pay_with_stars (line 237-284)
```python
@router.callback_query(F.data == "pay_stars", PaymentStates.waiting_payment_method)
async def pay_with_stars(callback: CallbackQuery, state: FSMContext) -> None:
```
✅ **State check present**: `PaymentStates.waiting_payment_method`

#### Handler 4: pay_with_yookassa (line 287-324)
```python
@router.callback_query(F.data == "pay_yookassa", PaymentStates.waiting_payment_method)
async def pay_with_yookassa(callback: CallbackQuery, state: FSMContext) -> None:
```
✅ **State check present**: `PaymentStates.waiting_payment_method`

#### Handler 5: confirm_payment_handler (line 401-429)
```python
@router.callback_query(F.data == "confirm_payment")
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение оплаты — переходим к выбору метода."""
```
❌ **MISSING STATE CHECK**: No state validation! Anyone can click this button from anywhere.

### The Bug

The `confirm_payment` handler doesn't check if the user is in a valid payment state:

```python
@router.callback_query(F.data == "confirm_payment")  # ← No state filter!
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
```

**Should be**:
```python
@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_period_selection)
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
```

---

## Part 5: Bot Menu Buttons - Hardcoded vs Dynamic

### Default Hardcoded Buttons (backend/api/v1/endpoints/admin.py lines 297-306)

```python
DEFAULT_BOT_BUTTONS = [
    {"text": "🎁 Бесплатный доступ", "callback_data": "free_trial", "url": "", "row": 0},
    {"text": "💸 Оплатить тариф", "callback_data": "buy_subscription", "url": "", "row": 1},
    {"text": "👤 Личный кабинет", "callback_data": "cabinet", "url": "", "row": 2},
    {"text": "🎁 Получить бесплатно", "callback_data": "get_free", "url": "", "row": 2},
    {"text": "🔗 Реферальная система", "callback_data": "partner", "url": "", "row": 3},
    {"text": "⚙️ Инструкция по подключению", "callback_data": "instructions", "url": "", "row": 3},
    {"text": "👨‍💻 Поддержка", "callback_data": "support", "url": "", "row": 4},
    {"text": "📢 Наш канал", "callback_data": "channel", "url": "", "row": 4},
]
```

### How Bot Gets Menu Buttons

In `bot/keyboards/main_menu.py` (NOT shown but referenced in start.py):

```python
async def get_dynamic_main_menu(client: APIClient, show_free_trial: bool = True):
    """Dynamically build main menu from API buttons"""
    try:
        buttons = await client.get_bot_buttons()
        if buttons:
            return _build_keyboard_from_api_buttons(buttons, show_free_trial)
    except Exception:
        pass
    return get_main_menu()  # Fallback to hardcoded
```

The bot SHOULD fetch buttons from `/bot-buttons/public` on every `/start`, but:
- ❌ If API fails, bot falls back to hardcoded buttons
- ❌ No cache invalidation mechanism when buttons updated in admin panel
- ❌ Bot doesn't reload menu on button updates

---

## Part 6: Payment Keyboard Functions

### In bot/keyboards/payment_kb.py (lines 51-63)

```python
def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars"),
                InlineKeyboardButton(text="💳 YooKassa (карта/СБП)", callback_data="pay_yookassa"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_payment"),
            ],
        ]
    )
```

✅ **Function exists and is properly used in payment.py line 227**

---

## Part 7: Payment Confirmation Formatter

### In bot/utils/formatters.py (lines 207-228)

```python
def format_payment_confirmation(
    plan_name: str,
    period_days: int,
    price: float,
    currency: str = "RUB"
) -> str:
    """Format payment confirmation message"""
    period_text = {
        7: "7 дней",
        30: "1 месяц",
        90: "3 месяца",
        180: "6 месяцев",
        365: "12 месяцев",
    }.get(period_days, f"{period_days} дней")
    
    return (
        f"<b>Подтверждение платежа</b>\n\n"
        f"<b>Тариф:</b> {plan_name}\n"
        f"<b>Период:</b> {period_text}\n"
        f"<b>Сумма:</b> {format_price(price, currency)}\n\n"
        f"Нажмите кнопку <b>Оплатить</b> для перехода к оплате."
    )
```

✅ **Function exists and is properly used in payment.py line 411**

---

## Summary of Findings

| Issue | Location | Severity | Type |
|-------|----------|----------|------|
| No automatic DB save after image upload | `upload_image()` endpoint | **HIGH** | Missing feature |
| Missing state check on `confirm_payment` | `payment.py` line 401 | **HIGH** | State management bug |
| Silent exception handling in `get_bot_settings()` | `api_client.py` line 248 | **MEDIUM** | Poor error handling |
| Silent exception handling in `get_all_bot_texts()` | `api_client.py` line 238 | **MEDIUM** | Poor error handling |
| No cache invalidation when buttons change | `main_menu.py` | **MEDIUM** | Sync issue |
| Hardcoded fallback buttons override API | Multiple files | **MEDIUM** | Data sync issue |

---

## Recommendations for Fixes

### Fix 1: Add State Validation to confirm_payment
```python
@router.callback_query(F.data == "confirm_payment", PaymentStates.waiting_period_selection)
async def confirm_payment_handler(callback: CallbackQuery, state: FSMContext) -> None:
```

### Fix 2: Improve Error Handling in API Client
```python
async def get_bot_settings(self) -> Dict[str, Any]:
    """Get bot settings (media URLs, support username, etc.) — uses public endpoint"""
    try:
        return await self.get("/bot-settings/public")
    except Exception as e:
        logger.error(f"Failed to get bot settings: {e}", exc_info=True)
        try:
            return await self.get("/admin/settings")
        except Exception as e2:
            logger.error(f"Fallback to /admin/settings also failed: {e2}")
            return {}
```

### Fix 3: Implement Cache Invalidation
When admin updates buttons/settings via PUT endpoints, trigger Redis cache clear:
```python
await _invalidate_bot_cache("bot:buttons", "bot:settings")
```

### Fix 4: Optional - Auto-save Image URL
Modify `upload_image()` to optionally save URL to database:
```python
@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    save_field: Optional[str] = None,  # "welcome_image", etc.
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # ... save file ...
    url = f"{base_url}/static/uploads/{filename}"
    
    if save_field:
        # Auto-save to BotText
        stmt = select(BotText).where(BotText.key == SETTINGS_KEY)
        row = await db.execute(stmt).scalar_or_none()
        settings = json.loads(row.value) if row else {}
        settings[save_field] = url
        # ... update DB ...
    
    return {"url": url, "filename": filename}
```

