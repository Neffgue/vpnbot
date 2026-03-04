# ENDPOINT REFERENCE: Exact URLs, Fields, and Cache Issues

## Overview Table

| Endpoint | Method | Auth | Returns | Cache? | Issue |
|----------|--------|------|---------|--------|-------|
| `/admin/plans` | GET | ✓ | `[{id, plan_name, period_days, price_rub}]` | ✗ | No cache |
| `/subscriptions/plans` | GET | ✗ | `[{id, plan_name, period_days, price_rub}]` | ✗ | **Used by bot, no cache** |
| `/admin/plans/{id}` | PUT | ✓ | `{id, plan_name, period_days, price_rub, created_at}` | ✗ | Calls invalidate but ineffective |
| `/admin/upload-image` | POST | ✓ | `{url, filename, relative_url}` | - | No DB record, no linking |
| `/bot-buttons/public` | GET | ✗ | `{buttons: [{id, text, callback_data, url, row, image_url}]}` | ✗ | **Bot uses, no cache** |
| `/bot-texts/public` | GET | ✗ | `{key: value, ...}` | ✗ | **Bot uses, no cache** |
| `/bot-settings/public` | GET | ✗ | `{...json...}` | ✗ | **Bot uses, no cache** |

---

## PRICE SYNC DETAILS

### Admin Updates Price

**Endpoint:** `PUT /api/v1/admin/plans/{plan_id}`

**Auth:** Requires `get_admin_user()` ✓

**Request Body:**
```json
{
  "price_rub": 200.00
}
```

**Schema** (`backend/schemas/admin.py` lines 34-36):
```python
class PlanPriceUpdate(BaseModel):
    """Update plan price schema."""
    price_rub: Decimal
```

**Handler** (`backend/api/v1/endpoints/admin.py` lines 1489-1517):
```python
@router.put("/plans/{plan_id}", response_model=PlanPriceResponse)
async def update_plan_price(
    plan_id: str,
    plan_data: PlanPriceUpdate,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a plan price by ID (admin only)."""
    try:
        plan = await db.get(PlanPrice, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if plan_data.plan_name is not None:  # ← ALWAYS FALSE (schema has no plan_name)
            plan.plan_name = plan_data.plan_name
        if plan_data.period_days is not None:  # ← ALWAYS FALSE (schema has no period_days)
            plan.period_days = plan_data.period_days
        if plan_data.price_rub is not None:  # ← WORKS ✓
            plan.price_rub = plan_data.price_rub
        await db.commit()
        await db.refresh(plan)
        await _invalidate_bot_cache("bot:plans")  # ← Line 1509: Tries to clear Redis
        logger.info(f"Plan price {plan_id} updated")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update plan price")
```

**Response** (`backend/schemas/admin.py` lines 39-48):
```python
class PlanPriceResponse(BaseModel):
    """Plan price response schema."""
    id: str
    plan_name: str
    period_days: int
    price_rub: Decimal
    created_at: datetime
    # ↑ Returns as Decimal, needs float() conversion for JSON serialization
```

**Actual Response (200 OK):**
```json
{
  "id": "plan_abc123",
  "plan_name": "Solo",
  "period_days": 7,
  "price_rub": 200.00,
  "created_at": "2024-01-15T10:00:00"
}
```

### Bot Fetches Plans

**Endpoint:** `GET /api/v1/subscriptions/plans` (PUBLIC, NO AUTH)

**Handler** (`backend/api/v1/router.py` lines 103-124):
```python
@api_router.get("/subscriptions/plans", tags=["compat"])
async def subscriptions_plans_compat(
    db: AsyncSession = Depends(get_db),
):
    """Public alias: GET /subscriptions/plans — returns plan prices list."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select
    try:
        result = await db.execute(
            select(PlanPrice).order_by(PlanPrice.plan_name, PlanPrice.period_days)
        )
        plans = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "plan_name": p.plan_name,
                "period_days": p.period_days,
                "price_rub": float(p.price_rub),  # ← Converts Decimal to float
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"subscriptions_plans_compat error: {e}")
        return []
```

**Response (200 OK):**
```json
[
  {
    "id": "plan_abc123",
    "plan_name": "Solo",
    "period_days": 7,
    "price_rub": 200.00
  },
  {
    "id": "plan_def456",
    "plan_name": "Solo",
    "period_days": 30,
    "price_rub": 400.00
  }
]
```

**Bot Client** (`bot/utils/api_client.py` lines 155-167):
```python
async def get_subscription_plans(self) -> list:
    """Get available subscription plans"""
    try:
        result = await self.get("/subscriptions/plans")
        # API returns list directly
        if isinstance(result, list):
            return result
        # In case it returns dict
        if isinstance(result, dict):
            return result.get("plans", result.get("items", []))
        return []
    except Exception:
        return []
```

**Bot Handler** (`bot/handlers/payment.py` lines 58-94):
```python
async def _fetch_plans(api: APIClient) -> list:
    """Fetch plans from API. If error — return fallback values."""
    try:
        plans = await api.get_subscription_plans()
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API, using fallback: {e}")
    return FALLBACK_PLANS  # ← Hardcoded prices from lines 1-55


def _group_plans_by_name(plans: list) -> dict:
    """Group plans by plan_name → list of periods."""
    grouped: dict = {}
    for plan in plans:
        key = plan.get("plan_name") or plan.get("id") or "solo"
        if key not in grouped:
            grouped[key] = {
                "key": key,
                "name": plan.get("name", key.capitalize()),
                "devices": plan.get("devices", plan.get("device_limit", 1)),
                "periods": {},
            }
        days = int(plan.get("period_days", 30))
        # Support both field names: price_rub (from DB) and price (generic)
        price = float(
            plan.get("price_rub")  # ← Looks for price_rub field
            or plan.get("price")   # ← Falls back to price field
            or 0
        )
        grouped[key]["periods"][days] = price
    return grouped
```

**✓ Field Matching: CORRECT**
- Endpoint returns: `price_rub: 200.0` ✓
- Bot expects: `plan.get("price_rub")` ✓
- Values match!

**✗ Cache Issue: CRITICAL**
- Endpoint at line 103-124: NO `@cached_response` decorator
- No Redis caching layer
- Admin calls invalidate on "bot:plans" key (line 1509)
- But endpoint doesn't use Redis at all
- **Result:** Invalidation has NO EFFECT

---

## IMAGE UPLOAD DETAILS

### Admin Uploads Image

**Endpoint:** `POST /api/v1/admin/upload-image`

**Auth:** Requires `get_admin_user()` ✓

**Request:** Multipart form-data with file

```
POST /api/v1/admin/upload-image
Content-Type: multipart/form-data

[Binary image data]
```

**Handler** (`backend/api/v1/endpoints/admin.py` lines 602-631):
```python
@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user=Depends(get_admin_user),
):
    """Upload image for bot (welcome, plan, etc.)."""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        filename = f"{uuid4().hex}.{ext}"  # ← e.g., "abc123def456.jpg"
        path = os.path.join(UPLOAD_DIR, filename)
        
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        
        with open(path, "wb") as f:
            f.write(content)
        
        # Build URL
        base_url = os.getenv("BACKEND_URL", "").rstrip("/")
        if base_url:
            url = f"{base_url}/static/uploads/{filename}"
        else:
            url = f"/static/uploads/{filename}"
        
        return {
            "url": url,
            "filename": filename,
            "relative_url": f"/static/uploads/{filename}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
```

**Response (200 OK):**
```json
{
  "url": "http://backend.example.com/static/uploads/abc123def456.jpg",
  "filename": "abc123def456.jpg",
  "relative_url": "/static/uploads/abc123def456.jpg"
}
```

**✗ Critical Issues:**
1. ✗ No database record created for the image
2. ✗ No `BotMedia` table entry
3. ✗ Returns only URL, not image_id
4. ✗ No relationship to any button/text yet
5. ✗ If file deleted from disk later, bot still has stale URL

### Admin Updates Button with Image URL

**Endpoint:** `PUT /api/v1/admin/bot-buttons/{btn_id}`

**Auth:** Requires `get_admin_user()` ✓

**Request Body (Manual Step - Admin Pastes URL):**
```json
{
  "text": "💸 Buy Plan",
  "callback_data": "buy_subscription",
  "url": "",
  "row": 1,
  "image_url": "http://backend.example.com/static/uploads/abc123def456.jpg"
}
```

**Handler** (`backend/api/v1/endpoints/admin.py` lines 461-489):
```python
@router.put("/bot-buttons/{btn_id}")
async def update_bot_button(
    btn_id: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update button menu (full replacement)."""
    stmt = select(BotText).where(BotText.key == btn_id)
    result = await db.execute(stmt)
    btn = result.scalars().first()
    if not btn:
        raise HTTPException(status_code=404, detail="Button not found")
    
    # Read existing data first to preserve fields not provided
    try:
        existing = json.loads(btn.value)
    except Exception:
        existing = {}
    
    existing.update({
        "text": data.get("text", existing.get("text", "")),
        "callback_data": data.get("callback_data", existing.get("callback_data", "")),
        "url": data.get("url", existing.get("url", "")),
        "row": data.get("row", existing.get("row", 0)),
        "image_url": data.get("image_url", existing.get("image_url", "")),  # ← Accepts image_url
    })
    btn.value = json.dumps(existing, ensure_ascii=False)
    await db.commit()
    await _invalidate_bot_cache("bot:buttons")  # ← Line 488: Invalidates Redis
    return {"success": True}
```

**What Gets Stored in DB:**
```
Table: bot_texts
Row:
  key: "btn_xyz789"
  value: '{"text":"💸 Buy Plan","callback_data":"buy_subscription","url":"","row":1,"image_url":"http://backend.example.com/static/uploads/abc123def456.jpg"}'
```

**✗ Problems:**
1. ✗ Image URL embedded in JSON string
2. ✗ No separate `media_id` column
3. ✗ No foreign key to image file
4. ✗ If image file deleted, URL still in DB but returns 404
5. ✗ Requires manual copy-paste by admin

### Bot Fetches Buttons

**Endpoint:** `GET /api/v1/bot-buttons/public` (PUBLIC, NO AUTH)

**Handler** (`backend/api/v1/router.py` lines 434-456):
```python
@api_router.get("/bot-buttons/public", tags=["public"])
async def bot_buttons_public(db: AsyncSession = Depends(get_db)):
    """Public: Get bot menu buttons for the bot process.
    Buttons are stored as individual btn_* keys in BotText table.
    """
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        stmt = _select(_BotText).where(_BotText.key.like("btn_%")).order_by(_BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        buttons = []
        for r in rows:
            try:
                btn = _json.loads(r.value)  # ← Parses JSON from DB
                btn["id"] = r.key
                buttons.append(btn)
            except Exception:
                pass
        return {"buttons": buttons}
    except Exception:
        return {"buttons": []}
```

**Response (200 OK):**
```json
{
  "buttons": [
    {
      "id": "btn_xyz789",
      "text": "💸 Buy Plan",
      "callback_data": "buy_subscription",
      "url": "",
      "row": 1,
      "image_url": "http://backend.example.com/static/uploads/abc123def456.jpg"
    }
  ]
}
```

**Bot Client** (`bot/utils/api_client.py` lines 258-272):
```python
async def get_bot_buttons(self) -> list:
    """Get main menu buttons — uses public endpoint.
    API returns list directly (each item is a dict with id, text, callback_data, etc.)
    """
    try:
        result = await self.get("/bot-buttons/public")
        # API возвращает список напрямую
        if isinstance(result, list):
            return result
        # На случай если вернёт dict
        if isinstance(result, dict):
            return result.get("buttons", [])  # ← Gets buttons array
        return []
    except Exception:
        return []
```

**✗ Cache Issue: CRITICAL**
- Endpoint at line 434-456: NO `@cached_response` decorator
- No Redis caching
- Admin calls invalidate on "bot:buttons" key (line 488)
- But endpoint doesn't use Redis
- **Result:** Invalidation has NO EFFECT

---

## BOT TEXTS DETAILS

### Admin Updates Text

**Endpoint:** `PUT /api/v1/admin/bot-texts/{key}`

**Auth:** Requires `get_admin_user()` ✓

**Request Body:**
```json
{
  "value": "Updated welcome message 👋"
}
```

**Handler** (`backend/api/v1/endpoints/admin.py` lines 331-359):
```python
@router.put("/bot-texts/{key}")
async def upsert_bot_text_by_key(
    key: str,
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update bot text by key. Changes are immediate."""
    value = data.get("value", "")
    try:
        stmt = select(BotText).where(BotText.key == key)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.value = value
        else:
            existing = BotText(id=str(uuid4()), key=key, value=value)
            db.add(existing)

        await db.commit()
        await db.refresh(existing)
        await _invalidate_bot_cache("bot:texts")  # ← Line 353: Invalidates Redis
        logger.info(f"Bot text updated: {key}")
        return {"key": existing.key, "value": existing.value}
    except Exception as e:
        logger.error(f"Error upserting bot text {key}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save bot text")
```

**Response (200 OK):**
```json
{
  "key": "welcome",
  "value": "Updated welcome message 👋"
}
```

### Bot Fetches Texts

**Endpoint:** `GET /api/v1/bot-texts/public` (PUBLIC, NO AUTH)

**Handler** (`backend/api/v1/router.py` lines 390-410):
```python
@api_router.get("/bot-texts/public", tags=["public"])
async def bot_texts_public(db: AsyncSession = Depends(get_db)):
    """Public: Get all bot texts (for the bot process, no auth)."""
    import json as _json
    from sqlalchemy import select as _select
    from backend.models.config import BotText as _BotText
    try:
        stmt = _select(_BotText).order_by(_BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        out = {}
        # Skip service keys, rest are bot messages
        SKIP_KEYS = {"bot_settings_json", "bot_buttons_json", "system_settings_json"}
        for row in rows:
            if row.key in SKIP_KEYS:
                continue
            # Value is always string (text message)
            out[row.key] = row.value
        return out
    except Exception as e:
        return {}
```

**Response (200 OK):**
```json
{
  "welcome": "Updated welcome message 👋",
  "free_trial_success": "🎁 Trial activated!",
  "subscription_expired": "❌ Your subscription expired",
  ...
}
```

**Bot Client** (`bot/utils/api_client.py` lines 238-246):
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

**✗ Cache Issue: CRITICAL**
- Endpoint: NO `@cached_response` decorator
- No Redis caching
- Admin calls invalidate on "bot:texts" (line 353)
- But endpoint doesn't use Redis
- **Result:** Invalidation has NO EFFECT

---

## BOT SETTINGS DETAILS

### Admin Updates Settings

**Endpoint:** `PUT /api/v1/admin/settings`

**Auth:** Requires `get_admin_user()` ✓

**Handler** (`backend/api/v1/endpoints/admin.py` lines 562-586):
```python
@router.put("/settings")
async def save_bot_settings(
    data: dict,
    current_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Save bot settings. Changes are applied immediately."""
    try:
        value = json.dumps(data, ensure_ascii=False)
        stmt = select(BotText).where(BotText.key == SETTINGS_KEY)  # SETTINGS_KEY = "bot_settings_json"
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            row.value = value
        else:
            row = BotText(id=str(uuid4()), key=SETTINGS_KEY, value=value, description="bot_settings")
            db.add(row)
        await db.commit()
        await db.refresh(row)
        await _invalidate_bot_cache("bot:settings")  # ← Line 581: Invalidates Redis
        return data
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save settings")
```

### Bot Fetches Settings

**Endpoint:** `GET /api/v1/bot-settings/public` (PUBLIC, NO AUTH)

**Handler** (`backend/api/v1/router.py` lines 413-431):
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

**Bot Client** (`bot/utils/api_client.py` lines 248-256):
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

**✗ Cache Issue: CRITICAL**
- Endpoint: NO `@cached_response` decorator
- No Redis caching
- Admin calls invalidate on "bot:settings" (line 581)
- But endpoint doesn't use Redis
- **Result:** Invalidation has NO EFFECT

---

## SUMMARY: What Needs Redis Caching

All these endpoints need `@cached_response()` decorator with Redis backend:

```python
# Current (BROKEN)
@api_router.get("/subscriptions/plans", tags=["compat"])
async def subscriptions_plans_compat(db: AsyncSession = Depends(get_db)):
    ...

# Should be
@api_router.get("/subscriptions/plans", tags=["compat"])
@cached_response(ttl=60, redis_key="bot:plans")
async def subscriptions_plans_compat(db: AsyncSession = Depends(get_db)):
    ...
```

**Endpoints needing caching:**
1. `GET /api/v1/subscriptions/plans` → Cache key: `bot:plans` → TTL: 60 seconds
2. `GET /api/v1/bot-buttons/public` → Cache key: `bot:buttons` → TTL: 60 seconds
3. `GET /api/v1/bot-texts/public` → Cache key: `bot:texts` → TTL: 60 seconds
4. `GET /api/v1/bot-settings/public` → Cache key: `bot:settings` → TTL: 60 seconds

When these are added, the `_invalidate_bot_cache()` calls will actually work!

