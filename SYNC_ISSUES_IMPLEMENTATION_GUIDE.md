# IMPLEMENTATION GUIDE: Fixing Price & Image Synchronization

## Quick Reference: Exact Field Names & Response Structures

### PlanPrice Model Response Fields

**Current (Broken):**
```python
# backend/api/v1/router.py lines 113-120
return [
    {
        "id": str(p.id),
        "plan_name": p.plan_name,
        "period_days": p.period_days,
        "price_rub": float(p.price_rub),  # ← Price field name
    }
    for p in plans
]
```

**Bot expects** (`bot/handlers/payment.py` lines 86-93):
```python
price = float(
    plan.get("price_rub")  # ← Looks for this field
    or plan.get("price")
    or 0
)
```

**Schema response** (`backend/schemas/admin.py` lines 39-48):
```python
class PlanPriceResponse(BaseModel):
    id: str
    plan_name: str
    period_days: int
    price_rub: Decimal  # ← Field name confirmed
    created_at: datetime
```

✓ **Field names MATCH.** The issue is NOT field naming, it's **cache invalidation and image linking**.

---

### BotButton Response Structure

**Current public endpoint** (`backend/api/v1/router.py` lines 434-456):
```python
@api_router.get("/bot-buttons/public")
async def bot_buttons_public(db: AsyncSession = Depends(get_db)):
    buttons = []
    for r in rows:
        btn = _json.loads(r.value)  # ← Parses JSON from BotText.value
        btn["id"] = r.key
        buttons.append(btn)
    return {"buttons": buttons}
```

**What BotText.value JSON contains** (`backend/api/v1/endpoints/admin.py` lines 446-452):
```python
btn_data = {
    "text": data.get("text", ""),
    "callback_data": data.get("callback_data", ""),
    "url": data.get("url", ""),
    "row": data.get("row", 0),
    "image_url": data.get("image_url", ""),  # ← Image field
}
```

**Bot expects** (`bot/handlers/payment.py` and `bot/utils/api_client.py`):
```python
result = await self.get("/bot-buttons/public")
if isinstance(result, dict):
    return result.get("buttons", [])  # ← Gets {"buttons": [...]}
```

✓ **Structure matches.** But `image_url` is OPTIONAL and never auto-populated when image uploaded.

---

### BotText/BotSettings Response Structure

**Admin endpoint** (`backend/api/v1/router.py` lines 390-410):
```python
@api_router.get("/bot-texts/public")
async def bot_texts_public(db: AsyncSession = Depends(get_db)):
    out = {}
    SKIP_KEYS = {"bot_settings_json", "bot_buttons_json", "system_settings_json"}
    for row in rows:
        if row.key in SKIP_KEYS:
            continue
        out[row.key] = row.value  # ← Key: value flat structure
    return out
```

**Bot settings endpoint** (`backend/api/v1/router.py` lines 413-431):
```python
@api_router.get("/bot-settings/public")
async def bot_settings_public(db: AsyncSession = Depends(get_db)):
    BOT_SETTINGS_KEY = "bot_settings_json"
    stmt = _select(_BotText).where(_BotText.key == BOT_SETTINGS_KEY)
    row = result.scalars().first()
    if row:
        return _json.loads(row.value)  # ← Parses JSON stored in value
    return {}
```

**Bot fetches** (`bot/utils/api_client.py` lines 238-256):
```python
async def get_all_bot_texts(self):
    try:
        return await self.get("/bot-texts/public")  # ← Dict {key: value}
    except Exception:
        return {}

async def get_bot_settings(self):
    try:
        return await self.get("/bot-settings/public")  # ← Dict
    except Exception:
        return {}
```

**Problem:** No schema validation or versioning. If admin manually edits `/bot-texts/public` response and includes `image_url`, bot gets it. But if image is deleted from disk, bot still has stale URL.

---

## WHERE DATA FLOWS BREAK

### Flow #1: Price Update → Bot Display

```
┌─────────────────────────────────────────────────────────────────────┐
│ ADMIN PANEL: Change price 100 → 200                                 │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PUT /api/v1/admin/plans/{plan_id}                                   │
│ Request: {"price_rub": 200}                                         │
│ Auth: Admin user via get_admin_user()                               │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ Handler: update_plan_price()                  │
        │ Line: backend/api/v1/endpoints/admin.py:1489  │
        │                                               │
        │ 1. Get PlanPrice from DB ✓                    │
        │ 2. Update price_rub field ✓                   │
        │ 3. await db.commit() ✓                        │
        │ 4. await _invalidate_bot_cache("bot:plans")   │
        │    ↳ Tries to delete Redis key "bot:plans"   │
        │    ↳ But /subscriptions/plans endpoint       │
        │       doesn't use Redis cache! ✗             │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESPONSE: {"id": "...", "plan_name": "...", "price_rub": 200} ✓    │
│ Admin Panel updates UI display ✓                                    │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ BOT: User clicks "Buy Plan" button            │
        │                                               │
        │ 1. Calls: api.get_subscription_plans()       │
        │    Line: bot/utils/api_client.py:156         │
        │ 2. Endpoint: GET /subscriptions/plans        │
        │    Line: backend/api/v1/router.py:103        │
        │ 3. No Redis caching decorator! ✗             │
        │ 4. Queries DB directly                       │
        │ 5. Should return new price 200 ✓             │
        │                                               │
        │ BUT: If bot has local cache from startup:   │
        │ - Bot memory: price = 100 (stale)            │
        │ - No TTL or invalidation event ✗             │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PROBLEM: Bot shows old price 100 if:                                │
│ - Bot cached locally on startup                                    │
│ - Network timeout forces fallback to FALLBACK_PLANS (hardcoded)    │
│ - No event notification from backend                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Flow #2: Image Upload → Button Display

```
┌─────────────────────────────────────────────────────────────────────┐
│ ADMIN PANEL: Upload image (logo.jpg)                                │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ POST /api/v1/admin/upload-image                                     │
│ Body: file=logo.jpg (binary)                                        │
│ Auth: Admin user                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ Handler: upload_image()                       │
        │ Line: backend/api/v1/endpoints/admin.py:602   │
        │                                               │
        │ 1. Generate filename: uuid.jpg ✓             │
        │ 2. Save to: /backend/static/uploads/uuid.jpg │
        │ 3. Build URL ✓                               │
        │ 4. Return: {                                 │
        │     "url": "http://backend/static/uploads/...",
        │     "filename": "uuid.jpg"                   │
        │    }                                         │
        │                                               │
        │ ✗ Does NOT:                                 │
        │ - Create DB record for image                │
        │ - Link image to any button/text             │
        │ - Return image_id                           │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESPONSE: {"url": "http://backend/static/uploads/abc123.jpg"}      │
│ Admin Panel shows image URL in clipboard                            │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ ADMIN PANEL: Manual Copy-Paste                │
        │                                               │
        │ 1. Admin clicks "Copy URL"                   │
        │ 2. Admin opens "Edit Button" dialog          │
        │ 3. Admin finds "image_url" field             │
        │ 4. Admin pastes URL manually                 │
        │ 5. Admin clicks "Save Button"                │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PUT /api/v1/admin/bot-buttons/{btn_id}                              │
│ Request: {                                                          │
│   "text": "💸 Buy Plan",                                            │
│   "callback_data": "buy_subscription",                              │
│   "image_url": "http://backend/static/uploads/abc123.jpg"          │
│ }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ Handler: update_bot_button()                  │
        │ Line: backend/api/v1/endpoints/admin.py:461   │
        │                                               │
        │ 1. Get BotText where key == btn_id ✓        │
        │ 2. Parse existing JSON ✓                     │
        │ 3. Update image_url field ✓                  │
        │ 4. Stringify back to JSON ✓                  │
        │ 5. await db.commit() ✓                       │
        │ 6. await _invalidate_bot_cache("bot:buttons")│
        │    ↳ Tries to clear Redis key "bot:buttons" │
        │    ↳ But endpoint uses no Redis cache! ✗    │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ RESPONSE: {"success": true}                                          │
│ Admin Panel confirms save                                            │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
        ┌───────────────────────────────────────────────┐
        │ BOT: User clicks menu button                 │
        │                                               │
        │ 1. Calls: api.get_bot_buttons()             │
        │    Line: bot/utils/api_client.py:258        │
        │ 2. Endpoint: GET /bot-buttons/public        │
        │    Line: backend/api/v1/router.py:434       │
        │ 3. Gets BotText records where key ~= btn_%  │
        │ 4. Parses JSON: {"text": "...", "image_url":
        │    "http://backend/static/uploads/abc123.jpg"}
        │ 5. Returns to bot ✓                         │
        └───────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PROBLEM: What if...                                                 │
│                                                                     │
│ 1. Admin forgets to update button JSON?                            │
│    ↳ Image URL never stored in BotText.value ✗                    │
│                                                                     │
│ 2. Image file deleted from /static/uploads/?                       │
│    ↳ Bot still has stale URL in JSON ✗                            │
│    ↳ Returns 404 to bot users ✗                                   │
│                                                                     │
│ 3. Nginx not serving /static/uploads/?                             │
│    ↳ Even if URL is correct, image returns 404 ✗                  │
│                                                                     │
│ 4. Redis cache cleared by admin?                                   │
│    ↳ Invalidation is called but doesn't affect anything ✗         │
│    ↳ No cache existed in the first place ✗                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Where Cache Invalidation Is Called (But Ineffective)

### Locations Where `_invalidate_bot_cache()` Is Called

| Line | Function | Called For | Redis Key | Problem |
|------|----------|-----------|-----------|---------|
| 353 | upsert_bot_text_by_key | Bot text update | "bot:texts" | Endpoint doesn't cache |
| 376 | delete_bot_text_by_key | Bot text delete | "bot:texts" | Endpoint doesn't cache |
| 457 | create_bot_button | New button | "bot:buttons" | Endpoint doesn't cache |
| 488 | update_bot_button | Button update | "bot:buttons" | Endpoint doesn't cache |
| 516 | patch_bot_button | Button partial update | "bot:buttons" | Endpoint doesn't cache |
| 581 | save_bot_settings | Settings update | "bot:settings" | Endpoint doesn't cache |
| 1509 | update_plan_price | **Price update** | "bot:plans" | **Endpoint doesn't cache!** |
| 1539 | delete_plan_price | Price delete | "bot:plans" | Endpoint doesn't cache |

**Key Finding:** Redis invalidation is called for "bot:plans" but `/subscriptions/plans` endpoint is NOT wrapped in Redis caching logic. So invalidation has NO EFFECT.

### Current Endpoints (NO CACHING)

```python
# backend/api/v1/router.py lines 103-124
@api_router.get("/subscriptions/plans", tags=["compat"])  # ← NO @cached_response decorator
async def subscriptions_plans_compat(db: AsyncSession = Depends(get_db)):
    """Public alias: GET /subscriptions/plans — returns plan prices list."""
    from backend.models.config import PlanPrice
    from sqlalchemy import select
    try:
        result = await db.execute(select(PlanPrice).order_by(...))
        plans = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "plan_name": p.plan_name,
                "period_days": p.period_days,
                "price_rub": float(p.price_rub),
            }
            for p in plans
        ]
    except Exception as e:
        logger.error(f"subscriptions_plans_compat error: {e}")
        return []
```

**What's needed:**
```python
# Pseudo-code for proper caching
@api_router.get("/subscriptions/plans/public")
@cached_response(ttl=60, redis_key="bot:plans")  # ← ADD THIS
async def subscriptions_plans_public(db: AsyncSession = Depends(get_db)):
    # ... same logic ...
```

---

## Exact Data Persistence Issues

### Issue: BotButton Image URL Stored as JSON String

**Database Record:**
```
Table: bot_texts
Columns: id, key, value, description, created_at, updated_at

Row:
id: "abc123def456"
key: "btn_xyz789"
value: '{"text":"💸 Buy","callback_data":"buy","url":"","row":1,"image_url":"http://backend/static/uploads/uuid.jpg"}'
description: "menu_button"
created_at: 2024-01-15 10:00:00
updated_at: 2024-01-15 10:05:00
```

**Problems:**
1. Image URL is embedded in JSON string — if JSON is corrupted, URL is lost
2. No `FOREIGN KEY` to image file on disk
3. No separate `media_id` column for quick lookups
4. No audit trail of "who uploaded this image when"
5. If image file is deleted from `/static/uploads/`, URL still exists in DB but returns 404

**What it should be:**
```
Table: bot_texts
Columns: id, key, value, description, media_id, created_at, updated_at

Row:
id: "abc123def456"
key: "btn_xyz789"
value: '{"text":"💸 Buy","callback_data":"buy","url":"","row":1}'
description: "menu_button"
media_id: "media_uuid_001"  ← Link to actual image record
created_at: 2024-01-15 10:00:00
updated_at: 2024-01-15 10:05:00

Table: bot_media
Columns: id, original_filename, stored_filename, file_path, mime_type, url, created_by, created_at

Row:
id: "media_uuid_001"
original_filename: "logo.jpg"
stored_filename: "abc123def456.jpg"
file_path: "/var/www/backend/static/uploads/abc123def456.jpg"
mime_type: "image/jpeg"
url: "http://backend.example.com/static/uploads/abc123def456.jpg"
created_by: "admin_user_123"
created_at: 2024-01-15 10:05:00
```

---

## Bot's Fallback Mechanism (Hidden Issue)

**Location:** `bot/handlers/payment.py` lines 1-55

```python
FALLBACK_PLANS = [
    {
        "id": "fallback_1",
        "plan_name": "Solo",
        "period_days": 7,
        "price_rub": 100.0,  # ← HARDCODED PRICES
        "is_active": True,
    },
    # ... more hardcoded plans ...
]
```

**When bot uses fallback:**

```python
async def _fetch_plans(api: APIClient) -> list:
    try:
        plans = await api.get_subscription_plans()
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API, using fallback: {e}")
    return FALLBACK_PLANS  # ← Falls back to hardcoded prices!
```

**When can this happen:**
1. Network timeout calling `/subscriptions/plans`
2. Backend returns 500 error
3. Backend returns invalid JSON
4. Bot can't parse response

If ANY of these happen during user's "Buy Plan" flow, bot shows FALLBACK_PLANS with prices that were hardcoded months ago and are completely out of sync!

---

## Summary: What Bot Actually Receives

### When Bot Starts Up

**Bot code** (`bot/handlers/payment.py` lines 58-66):
```python
async def _fetch_plans(api: APIClient) -> list:
    try:
        plans = await api.get_subscription_plans()  # ← Calls endpoint
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception:
        return FALLBACK_PLANS  # ← Fallback
    return FALLBACK_PLANS
```

**What endpoint returns** (`backend/api/v1/router.py` lines 113-120):
```python
[
    {
        "id": "abc123",
        "plan_name": "Solo",
        "period_days": 7,
        "price_rub": 100.0,  # ← Current DB value ✓
    },
    # ... more plans ...
]
```

**Bot expects** (`bot/handlers/payment.py` lines 86-93):
```python
price = float(plan.get("price_rub") or plan.get("price") or 0)
```

✓ **Bot WILL get updated price if endpoint responds correctly.**

**BUT:** If there's network delay or endpoint timeout, bot uses FALLBACK_PLANS (hardcoded old prices) ✗

---

## Quick Checklist: What Needs Fixing

### Priority 1: Cache Invalidation (Price Sync)
- [ ] Add `@cached_response()` decorator to `/subscriptions/plans` endpoint
- [ ] Add Redis TTL to cache plans for 60 seconds
- [ ] Verify `_invalidate_bot_cache("bot:plans")` is called in PUT /plans handler
- [ ] Test: Change price → Wait < 1 sec → User sees new price

### Priority 2: Image Persistence (Image Sync)
- [ ] Create `BotMedia` table with `id, original_filename, stored_filename, file_path, mime_type, url`
- [ ] Add `media_id` column to `BotText` table (NULLABLE)
- [ ] Modify `POST /upload-image` to create `BotMedia` record
- [ ] Modify `PUT /bot-buttons` to accept `media_id` instead of manual `image_url`
- [ ] Modify `GET /bot-buttons/public` to JOIN with `BotMedia` and return full image data

### Priority 3: Bot Cache Management
- [ ] Add TTL to bot's local plan cache (30-60 seconds)
- [ ] Add webhook/event endpoint for admin → bot notifications
- [ ] Modify bot to listen for invalidation events
- [ ] Remove hardcoded FALLBACK_PLANS or update them quarterly

### Priority 4: Data Model Fixes
- [ ] Add migration to create `BotMedia` table
- [ ] Add migration to add `media_id` to `BotText`
- [ ] Add migration to add `image_id` to `PlanPrice`
- [ ] Update schemas to include media references

