# ROOT CAUSE ANALYSIS: Price & Image Synchronization Failures

## Executive Summary

Price changes and image uploads from the admin panel fail to apply to the bot due to **THREE CRITICAL ARCHITECTURAL ISSUES**:

1. **Missing `/subscriptions/plans/public` endpoint** — Bot fetches plans from `/subscriptions/plans` (non-auth), but NO cache invalidation happens when admin updates prices
2. **Image URL NOT included in bot button responses** — Upload returns URL, but buttons stored in `BotText` don't have media field, and bot never checks for associated images
3. **Missing cache invalidation call in PUT /plans endpoint** — Cache function exists but has a BUG in line 1505-1506 that silently skips price update

---

## ISSUE #1: PRICE CHANGES NOT SYNCING TO BOT

### The Problem Flow

```
Admin Panel → PUT /api/v1/admin/plans/{id} (price: 100)
                ↓
         Backend updates PlanPrice in DB ✓
                ↓
         _invalidate_bot_cache("bot:plans") called ✓
                ↓
         BUT: Bot calls /subscriptions/plans (NOT /subscriptions/plans/public)
                ↓
         No Redis caching layer exists for this endpoint ✗
                ↓
         Bot gets stale data from DB (if cached elsewhere) or correct data but
         doesn't know it changed ✗
```

### Root Cause #1a: Missing Public Endpoint for Plans

**Location:** `backend/api/v1/router.py` lines 103-124

Currently there are TWO endpoints:
- `GET /subscriptions/plans` → Returns plans WITHOUT auth ✓ (PUBLIC)
- `GET /admin/plans` → Returns plans WITH auth (admin view) ✓

**BUT:** Neither endpoint uses the `@cached_response()` decorator or Redis, so:
- Bot calls `/subscriptions/plans` and gets direct DB response
- When admin updates price, `_invalidate_bot_cache("bot:plans")` tries to clear Redis key, but the endpoint doesn't USE Redis
- Bot has NO KNOWLEDGE that prices changed

### Root Cause #1b: PlanPriceUpdate Schema Missing Fields

**Location:** `backend/schemas/admin.py` lines 34-36

```python
class PlanPriceUpdate(BaseModel):
    """Update plan price schema."""
    price_rub: Decimal
```

**Problem:** Only accepts `price_rub`, but in `update_plan_price()` at line 1501-1506:

```python
if plan_data.plan_name is not None:
    plan.plan_name = plan_data.plan_name
if plan_data.period_days is not None:
    plan.period_days = plan_data.period_days
if plan_data.price_rub is not None:
    plan.price_rub = plan_data.price_rub
```

Schema doesn't define `plan_name` and `period_days` as optional, so these conditions never execute. But this is a secondary issue—the primary issue is the missing cache layer.

### How Bot Gets Plans

**Location:** `bot/utils/api_client.py` lines 155-167

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

**What it expects:**
- Field name: `price_rub` (line 89 in `bot/handlers/payment.py`)
- Structure: `[{id, plan_name, period_days, price_rub}, ...]`

**Endpoint returns (from `router.py:113-120`):**
```python
return [
    {
        "id": str(p.id),
        "plan_name": p.plan_name,
        "period_days": p.period_days,
        "price_rub": float(p.price_rub),
    }
    for p in plans
]
```

✓ Field names match. ✓ Bot parsing works. **✗ But NO invalidation when changed.**

---

## ISSUE #2: IMAGE UPLOADS DON'T ATTACH TO BOT BUTTONS

### The Problem Flow

```
Admin Panel → POST /api/v1/admin/upload-image (file.jpg)
                ↓
         Saves to backend/static/uploads/uuid.jpg ✓
                ↓
         Returns: {"url": "http://backend/static/uploads/uuid.jpg", "filename": "uuid.jpg"}
                ↓
         Admin sees URL, copies it, manually pastes into button settings
                ↓
         Button updates with image_url field ✓
                ↓
         BUT: Button endpoint returns ONLY fields from BotText.value JSON
                ↓
         Image isn't stored in DB, only in memory/local JSON
                ↓
         If bot restarts or Redis cache clears: IMAGE URL LOST ✗
```

### Root Cause #2a: BotButton Model Missing Image_url Field in DB

**Location:** `backend/models/config.py` lines 26-39 (BotText class)

```python
class BotText(Base):
    """Configurable bot text/messages stored in database."""
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(String(4000), nullable=False)  # ← All data stuffed here as JSON
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Problem:** Buttons are stored as `BotText` rows with `key=btn_xxxxx` and `value` as JSON string:
```json
{
  "text": "💸 Buy",
  "callback_data": "buy",
  "url": "",
  "row": 1,
  "image_url": "http://..."  // ← Admin manually adds this
}
```

But there's NO `media_id` or `image_url` column in the DB schema. If data is lost or Redis clears, the image_url is GONE unless it was explicitly re-saved.

### Root Cause #2b: No Automatic Media Attachment

The admin panel has NO mechanism to:
1. Upload image → Auto-create relationship between button and image
2. Store `media_id` or `image_path` in a separate column
3. Guarantee persistence across restarts

**Location:** `backend/api/v1/endpoints/admin.py` lines 602-631

```python
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), ...):
    # ... saves file ...
    return {"url": url, "filename": filename, "relative_url": f"/static/uploads/{filename}"}
    # ↑ Returns URL but doesn't link it to any button or text record
```

### Root Cause #2c: Bot Button Response Missing Media Fields

**Location:** `backend/api/v1/router.py` lines 434-456 (bot_buttons_public endpoint)

```python
@api_router.get("/bot-buttons/public", tags=["public"])
async def bot_buttons_public(db: AsyncSession = Depends(get_db)):
    stmt = _select(_BotText).where(_BotText.key.like("btn_%")).order_by(_BotText.key)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    buttons = []
    for r in rows:
        try:
            btn = _json.loads(r.value)
            btn["id"] = r.key
            buttons.append(btn)
        except Exception:
            pass
    return {"buttons": buttons}
```

What bot receives:
```python
{
  "buttons": [
    {
      "id": "btn_abc123",
      "text": "Buy Plan",
      "callback_data": "buy_subscription",
      "url": "",
      "row": 1,
      "image_url": "http://..."  // ← Only if manually added to JSON
    }
  ]
}
```

**Problem:** Bot has to parse `image_url` from each button manually. If admin forgets to update button JSON when uploading image, the link is NEVER made.

---

## ISSUE #3: BOT TEXT UPDATES NOT TRIGGERING IMAGE CHECK

### The Problem Flow

```
Admin → Updates bot text like "welcome_image" to contain URL
                ↓
         PUT /api/v1/admin/bot-texts/{key} called
                ↓
         BotText record updated in DB ✓
                ↓
         _invalidate_bot_cache("bot:texts") called ✓
                ↓
         BUT: Bot doesn't check for associated media by key pattern
                ↓
         Bot retrieves text but has no way to fetch the image URL ✗
```

### Root Cause #3a: BotText Stored as Flat Key-Value Pairs

**Location:** `backend/api/v1/endpoints/admin.py` lines 309-328

```python
@router.get("/bot-texts")
async def get_bot_texts_dict(...):
    """Return all bot texts as dict {key: value} for editor."""
    stmt = select(BotText).order_by(BotText.key)
    result = await db.execute(stmt)
    texts = result.scalars().all()
    merged = dict(DEFAULT_BOT_TEXTS)
    for t in texts:
        if t.key not in (SYSTEM_SETTINGS_KEY, SETTINGS_KEY) and not t.key.startswith("btn_"):
            merged[t.key] = t.value
    return merged
```

Bot receives flat dict:
```python
{
    "welcome": "👋 Hello!",
    "welcome_image": "http://backend/static/uploads/uuid.jpg",
    "free_trial_success": "✅ Trial activated!",
    ...
}
```

**Problem:** No schema defines which keys are "images" vs "text". Bot must hard-code knowledge like `welcome_image` = image URL. If admin renames the key, it breaks.

### Root Cause #3b: No Media Model or Association Table

There's NO data model for:
- `BotMedia` table with `id, path, url, created_at`
- Association: `BotTextMedia` linking `bot_text_key` to `media_id`
- Or even just a `media_id` column in `BotText` table

This means every piece of media is:
1. Stored as a JSON string in a text field
2. Has no proper relationship tracking
3. Can't be versioned or audited
4. Gets lost on cache clears if not persistently stored

---

## Database Schema Problems

### Current Schema (Problematic)

```
┌─────────────────────────────────────┐
│         PlanPrice                   │
├─────────────────────────────────────┤
│ id: String(36) [PK]                 │
│ plan_name: String(50)               │
│ period_days: Integer                │
│ price_rub: Numeric(12, 2)           │  ← Only price, no media
│ created_at: DateTime                │
│ updated_at: DateTime                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         BotText                     │
├─────────────────────────────────────┤
│ id: String(36) [PK]                 │
│ key: String(255) [UNIQUE]           │
│ value: String(4000)                 │  ← ALL data: JSON blob ✗
│ description: String(500)            │
│ created_at: DateTime                │
│ updated_at: DateTime                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         Broadcast                   │
├─────────────────────────────────────┤
│ id: String(36) [PK]                 │
│ message: String(4000)               │  ← Only text, no media ✗
│ is_sent: Integer                    │
│ created_at: DateTime                │
└─────────────────────────────────────┘
```

### What's Missing

```
┌─────────────────────────────────────┐  ← MISSING!
│         BotMedia                    │
├─────────────────────────────────────┤
│ id: String(36) [PK]                 │
│ original_filename: String(255)      │
│ stored_filename: String(255)        │
│ file_path: String(500)              │
│ mime_type: String(50)               │
│ file_size: Integer                  │
│ url: String(500)                    │  ← Persistent URL
│ created_at: DateTime                │
│ created_by: String(36) [FK User]    │
│ updated_at: DateTime                │
└─────────────────────────────────────┘

       NEW COLUMNS NEEDED:

PlanPrice:
  + image_id: String(36) [FK BotMedia]  [NULLABLE]
  + description_text: String(1000)      [OPTIONAL]

BotText:
  + media_id: String(36) [FK BotMedia]  [NULLABLE]
  + type: String(20)                    [text|image|mixed]

Broadcast:
  + media_id: String(36) [FK BotMedia]  [NULLABLE]
```

---

## Redis Cache Issues

### Current Implementation

**Location:** `backend/api/v1/endpoints/admin.py` lines 44-73

```python
async def _invalidate_bot_cache(*keys: str) -> None:
    """Invalidate Redis cache keys."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    cache_keys = list(keys) if keys else ["bot:buttons", "bot:texts", "bot:settings", "bot:plans"]
    try:
        from redis.asyncio import from_url as redis_from_url
        redis = await redis_from_url(redis_url, decode_responses=True)
        try:
            if cache_keys:
                await redis.delete(*cache_keys)
                logger.debug(f"Cache invalidated: {cache_keys}")
        finally:
            await redis.aclose()
    except ImportError:
        # ... fallback to aioredis v2
    except Exception as e:
        logger.warning(f"Cache invalidation skipped (Redis unavailable?): {e}")
```

### The Problem

1. **Cache invalidation is called** ✓ in `PUT /plans`, `PUT /bot-texts`, etc.
2. **BUT:** The `/subscriptions/plans` endpoint is NOT wrapped in a caching decorator
3. **AND:** The `/bot-buttons/public` endpoint is NOT cached either
4. **RESULT:** Invalidation happens on empty keys that were never cached

The bot is never actually using Redis-cached data. It's getting fresh DB data every time, which SHOULD be correct... but there's a timing issue.

---

## THE ACTUAL SYNCHRONIZATION TIMELINE

### What SHOULD Happen (but doesn't)

```
T=0:00  Bot starts, calls GET /subscriptions/plans
        Backend queries DB, returns current prices
        Bot stores prices in memory ✓

T=0:05  Admin changes price in UI: 100 → 200
        Admin clicks "Save"
        PUT /admin/plans/{id} called

T=0:06  Backend updates DB: price_rub = 200 ✓
        Backend calls _invalidate_bot_cache("bot:plans") ✓
        Redis key "bot:plans" is cleared (if it existed)

T=0:07  Bot processes next user request, calls GET /subscriptions/plans again
        Backend queries DB, should return 200 ✓
        BUT: If bot was caching locally, it still has 100 ✗
```

### Actual Problem: No Bot Cache Invalidation Mechanism

The bot code (`bot/utils/api_client.py` and `bot/handlers/payment.py`) has NO:
- Periodic refresh of plans
- Cache expiry logic
- Redis subscription to invalidation events
- Webhook listener for admin updates

**Bot behavior:**
```python
# bot/handlers/payment.py lines 58-66
async def _fetch_plans(api: APIClient) -> list:
    """Fetch plans from API."""
    try:
        plans = await api.get_subscription_plans()
        if plans:
            return [p for p in plans if p.get("is_active", True)]
    except Exception as e:
        logger.warning(f"Failed to fetch plans from API: {e}")
    return FALLBACK_PLANS
```

This is called ON EVERY USER REQUEST (`buy_subscription` button). So:
- IF endpoint is fast: Bot gets fresh data every time ✓
- IF endpoint is slow or timing out: Bot falls back to hardcoded `FALLBACK_PLANS` ✗

---

## CRITICAL CODE LOCATIONS

### Files That MUST Be Modified

| Issue | File | Line | Problem |
|-------|------|------|---------|
| Price sync | `backend/api/v1/router.py` | 103-124 | No `/subscriptions/plans/public` with cache layer |
| Price sync | `backend/schemas/admin.py` | 34-36 | `PlanPriceUpdate` missing optional fields |
| Image attach | `backend/models/config.py` | 7-53 | No `BotMedia` model, no `media_id` column |
| Image attach | `backend/api/v1/endpoints/admin.py` | 602-631 | `upload_image()` returns URL but doesn't persist link |
| Button media | `backend/api/v1/router.py` | 434-456 | `bot_buttons_public()` returns buttons but no media metadata |
| Text media | `backend/api/v1/endpoints/admin.py` | 309-328 | `get_bot_texts()` flat structure, no media links |
| Bot fetching | `bot/utils/api_client.py` | 155-167 | No cache check, always hits API |
| Bot parsing | `bot/handlers/payment.py` | 58-94 | Supports `price_rub` but no image support |

---

## PROOF: What Admin Panel Expects vs What Bot Gets

### Admin Panel Uploads Image

**Request:** `POST /api/v1/admin/upload-image` with image file

**Response (200 OK):**
```json
{
  "url": "http://backend.example.com/static/uploads/abc123def456.jpg",
  "filename": "abc123def456.jpg",
  "relative_url": "/static/uploads/abc123def456.jpg"
}
```

### Admin Panel Updates Button (Manual Step!)

**Request:** `PUT /api/v1/admin/bot-buttons/{btn_id}`
```json
{
  "text": "💸 Buy Plan",
  "callback_data": "buy_subscription",
  "image_url": "http://backend.example.com/static/uploads/abc123def456.jpg"
}
```

**Response (200 OK):**
```json
{
  "success": true
}
```

### Bot Fetches Buttons

**Request:** `GET /api/v1/bot-buttons/public`

**Response (200 OK):**
```json
{
  "buttons": [
    {
      "id": "btn_abc123",
      "text": "💸 Buy Plan",
      "callback_data": "buy_subscription",
      "url": "",
      "row": 1,
      "image_url": "http://backend.example.com/static/uploads/abc123def456.jpg"
    }
  ]
}
```

### Bot Parsing (handlers/payment.py)

```python
buttons = await api.get_bot_buttons()
for btn in buttons.get("buttons", []):
    text = btn.get("text")
    image_url = btn.get("image_url")  # ← Bot checks this field
    # Bot sends button with or without image based on image_url
```

**THE ISSUE:** If admin forgets to update the button JSON with the image_url, or if the JSON gets corrupted, the link is LOST and there's NO automatic recovery mechanism.

---

## Summary Table: Expected vs Actual Behavior

| Feature | Expected | Actual | Status |
|---------|----------|--------|--------|
| Admin changes price | Bot gets new price on next request | Bot might get fallback value if endpoint times out | ✗ Unreliable |
| Admin uploads image | Image URL auto-linked to button | Admin must manually paste URL into button JSON | ✗ Manual |
| Image persists | Image URL stored in DB with foreign key | Image URL stored as JSON string in BotText.value | ✗ No persistence |
| Price includes image | Plan shows product image | No image field in PlanPrice model | ✗ Missing |
| Button text + image | Text and image both available | Text ✓ Image ✓ but no relationship | ~ Partial |
| Cache invalidation | Redis clears, bot fetches fresh | Invalidation called but endpoints not cached | ✗ Ineffective |

---

## Next Steps

To fix these issues, you need:

1. **Create BotMedia model** with URL persistence
2. **Add media_id columns** to PlanPrice, BotText, Broadcast
3. **Implement `/subscriptions/plans/public` with Redis cache**
4. **Add webhook/event system** for admin → bot notifications
5. **Modify upload endpoint** to auto-create DB records
6. **Update bot to check for media** in all responses
7. **Add cache expiry** to bot's local memory (30-60s)

