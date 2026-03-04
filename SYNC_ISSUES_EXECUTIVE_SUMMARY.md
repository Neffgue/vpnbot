# EXECUTIVE SUMMARY: Price & Image Sync Issues

## The Three Critical Problems

### PROBLEM 1: Price Changes Don't Sync to Bot
**Status:** ✗ BROKEN

**What happens:**
1. Admin changes price in UI: 100 → 200
2. Backend updates database ✓
3. Backend calls `_invalidate_bot_cache("bot:plans")` ✓
4. But `/subscriptions/plans` endpoint has NO Redis caching layer ✗
5. Bot queries endpoint and should get fresh data... ✓
6. **BUT** if bot is running old cached copy in memory, it shows old price ✗

**Root cause:** 
- Endpoint `GET /subscriptions/plans` (line 103-124 in `router.py`) returns fresh DB data
- But NO `@cached_response()` decorator, so invalidation has NO EFFECT
- Bot has NO mechanism to know data changed (no events, no TTL)
- Falls back to hardcoded `FALLBACK_PLANS` on any network error

**Fix:** Add Redis caching with 60-second TTL to endpoint

---

### PROBLEM 2: Image URLs Not Persisted
**Status:** ✗ BROKEN

**What happens:**
1. Admin uploads image → Returns URL ✓
2. Admin manually pastes URL into button JSON
3. Backend stores URL in `BotText.value` as JSON string
4. If file deleted from `/static/uploads/`, URL still in DB but returns 404 ✗
5. No audit trail of who uploaded what
6. No way to batch-query "all images" or "all buttons with images"

**Root cause:**
- No `BotMedia` table with proper image records
- Image URL embedded in JSON string, not in separate column
- No foreign key relationship
- `POST /upload-image` returns URL but doesn't create DB record

**Fix:** Create `BotMedia` table, add `media_id` columns to `BotText` and `PlanPrice`

---

### PROBLEM 3: Manual Image Linking Required
**Status:** ✗ BROKEN

**What happens:**
1. Admin uploads image via form
2. System returns URL
3. Admin must MANUALLY copy-paste URL into button settings
4. If admin forgets, image never appears
5. If URL is wrong, no validation
6. If image is renamed/deleted, bot still has stale URL

**Root cause:**
- No automatic image-to-button linking
- Admin must manually manage image_url field
- No validation that image_url actually exists/is accessible
- No schema for image relationships

**Fix:** Auto-link uploaded images to buttons/plans via database relationships

---

## Field Names & Response Structures (CORRECT)

### Price Field
```
Admin → PUT: {"price_rub": 200}
DB Column: price_rub (Numeric)
API Response: "price_rub": 200.0
Bot Expects: plan.get("price_rub") ✓
Status: ✓ FIELD NAMES MATCH
Issue: Cache, not field names
```

### Image URL Field
```
Admin → PUT: {"image_url": "http://..."}
DB Storage: BotText.value JSON {"image_url": "..."}
API Response: {"image_url": "http://..."}
Bot Expects: btn.get("image_url") ✓
Status: ✓ FIELD NAMES MATCH
Issue: No persistence, must be manually managed
```

---

## Where Sync Fails (Timeline)

### Price Update Failure Scenario

```
T=0:00  Bot starts → Calls GET /subscriptions/plans → Gets plans list
T=0:00  Bot stores plans in memory: {Solo-7d: 100 RUB}

T=0:05  Admin changes price: 100 → 200
T=0:06  PUT /admin/plans/abc123 → {"price_rub": 200}
T=0:06  Database updated: PlanPrice.price_rub = 200 ✓
T=0:06  _invalidate_bot_cache("bot:plans") called
        ↳ Tries to delete Redis key "bot:plans"
        ↳ But endpoint uses no Redis! No effect ✗

T=0:07  User clicks "Buy Plan"
T=0:07  Bot calls _fetch_plans()
T=0:07  Bot calls api.get_subscription_plans()
T=0:07  GET /subscriptions/plans queried
        ↳ If endpoint responds: Bot gets 200 ✓
        ↳ If timeout (3s): Bot uses FALLBACK_PLANS with 100 ✗
        
RESULT: User pays for "100 RUB plan" but gets "200 RUB plan" setup? 
        OR sees old price in old cached data if bot never re-queried?
```

### Image Upload Failure Scenario

```
T=0:00  Admin clicks "Upload Image"
T=0:01  POST /upload-image with logo.jpg
T=0:01  File saved: /backend/static/uploads/abc123.jpg ✓
T=0:01  Response: {"url": "http://backend/static/uploads/abc123.jpg"}
T=0:02  Admin manually finds button settings dialog
T=0:03  Admin manually pastes URL into "image_url" field
T=0:04  PUT /bot-buttons/btn_xyz with {"image_url": "http://..."}
T=0:04  BotText.value JSON updated ✓
T=0:05  User loads button list
T=0:05  GET /bot-buttons/public returns button with image_url ✓

BUT RISK: 
- Server admin deletes /backend/static/uploads/abc123.jpg
- Bot still has URL in DB
- Bot shows image, user clicks, gets 404 ✗
- No one knows image is missing

OR:
- Admin forgets to update button settings with image_url
- Image uploaded but never used ✗

OR:
- Admin updates button but pastes wrong URL
- No validation happens ✗
```

---

## Database Schema Issues

### Current (Problematic)

**PlanPrice Table:**
```
Columns: id, plan_name, period_days, price_rub, created_at, updated_at
Problem: No image_id column, can't attach product image to plan
```

**BotText Table:**
```
Columns: id, key, value (JSON string), description, created_at, updated_at
Problem: All data stuffed in JSON string, no media_id column, no type field
Used for: Buttons (btn_*), Texts (welcome, etc.), Settings (bot_settings_json)
```

**Broadcast Table:**
```
Columns: id, message, is_sent, created_at
Problem: No media_id, can't attach image to broadcast
```

**Missing: BotMedia Table**
```
Needed:
  id, original_filename, stored_filename, file_path, mime_type, url, 
  file_size, created_by, created_at, updated_at
```

---

## The Three Fixes (Priority Order)

### Fix #1: Add Redis Caching to Public Endpoints (CRITICAL)
**Difficulty:** Easy | **Impact:** CRITICAL | **Time:** 30 minutes

**Files to modify:**
- `backend/api/v1/router.py`

**What to do:**
```python
# Add to imports
from some_caching_library import cached_response

# Wrap these endpoints:
@api_router.get("/subscriptions/plans")
@cached_response(ttl=60, redis_key="bot:plans")
async def subscriptions_plans_compat(db):
    ...

@api_router.get("/bot-buttons/public")
@cached_response(ttl=60, redis_key="bot:buttons")
async def bot_buttons_public(db):
    ...

@api_router.get("/bot-texts/public")
@cached_response(ttl=60, redis_key="bot:texts")
async def bot_texts_public(db):
    ...

@api_router.get("/bot-settings/public")
@cached_response(ttl=60, redis_key="bot:settings")
async def bot_settings_public(db):
    ...
```

**Result:**
- Admin changes price
- Cache is invalidated automatically
- Bot gets fresh data within 60 seconds
- ✓ Price sync works

---

### Fix #2: Create Media Persistence Layer (MEDIUM)
**Difficulty:** Medium | **Impact:** HIGH | **Time:** 2-3 hours

**Files to modify:**
- `backend/models/config.py` (add BotMedia model)
- `backend/alembic/versions/` (create migration)
- `backend/schemas/admin.py` (add BotMediaResponse schema)

**What to do:**
```python
# Add to models/config.py
class BotMedia(Base):
    __tablename__ = "bot_media"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_by = Column(String(36), nullable=True)  # User ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Modify BotText
class BotText(Base):
    # ... existing columns ...
    media_id = Column(String(36), ForeignKey("bot_media.id"), nullable=True)  # NEW

# Modify PlanPrice
class PlanPrice(Base):
    # ... existing columns ...
    image_id = Column(String(36), ForeignKey("bot_media.id"), nullable=True)  # NEW
```

**Result:**
- Images have persistent DB records
- Foreign keys ensure referential integrity
- Can query "all images" or "all buttons with images"
- ✓ Image persistence works

---

### Fix #3: Auto-Link Images to Buttons (MEDIUM)
**Difficulty:** Medium | **Impact:** HIGH | **Time:** 2-3 hours

**Files to modify:**
- `backend/api/v1/endpoints/admin.py` (modify upload_image handler)
- `backend/api/v1/endpoints/admin.py` (modify button update handler)
- `backend/api/v1/router.py` (modify bot_buttons_public to include media)

**What to do:**
```python
# Modify upload_image to create DB record
@router.post("/upload-image")
async def upload_image(file, current_user, db):
    # ... save file ...
    
    # NEW: Create BotMedia record
    media = BotMedia(
        id=str(uuid4()),
        original_filename=file.filename,
        stored_filename=filename,
        file_path=path,
        mime_type=file.content_type,
        url=url,
        file_size=len(content),
        created_by=current_user.id
    )
    db.add(media)
    await db.commit()
    
    return {"media_id": media.id, "url": url, "filename": filename}

# Modify button update to accept media_id
@router.put("/bot-buttons/{btn_id}")
async def update_bot_button(btn_id, data, current_user, db):
    # ... existing code ...
    
    # NEW: Accept media_id field
    if "media_id" in data:
        btn.media_id = data["media_id"]
    
    # ... rest of handler ...
```

**Result:**
- Admin uploads image → Get image_id automatically
- Admin selects "image_id" from dropdown (not manual paste)
- Button.media_id links to actual image record
- ✓ Image linking is automatic

---

## Testing Each Fix

### Test #1: Price Sync
```bash
# Start bot
docker exec bot python -m bot.main

# Admin changes price
curl -X PUT http://localhost:8000/api/v1/admin/plans/abc123 \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"price_rub": 200}'

# Wait 2 seconds
sleep 2

# Bot fetches plans
curl http://localhost:8000/api/v1/subscriptions/plans

# Should return 200 ✓
```

### Test #2: Image Upload
```bash
# Admin uploads image
curl -X POST http://localhost:8000/api/v1/admin/upload-image \
  -H "Authorization: Bearer admin_token" \
  -F "file=@logo.jpg"

# Should return media_id
# {"media_id": "abc123", "url": "http://...", ...}

# Check BotMedia table
docker exec postgres psql -U admin -d vpndb -c "SELECT * FROM bot_media;"

# Should have one row with our image ✓
```

### Test #3: Button with Image
```bash
# Admin updates button with image
curl -X PUT http://localhost:8000/api/v1/admin/bot-buttons/btn_xyz \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Buy", "media_id": "abc123"}'

# Bot fetches buttons
curl http://localhost:8000/api/v1/bot-buttons/public

# Response should include full image data (URL, size, etc.) ✓
```

---

## Why This Happened

### Root Cause Analysis

1. **Separation of Concerns Violated**
   - Images treated as "optional JSON strings" in BotText
   - No separate image management system
   - No concept of "media" as first-class object

2. **Admin Tool Not Integrated with Backend**
   - Upload returns URL but doesn't create records
   - Admin must manually paste URLs
   - Frontend doesn't have dropdown of "available images"

3. **No Cache Layer**
   - Cache invalidation infrastructure exists (Redis keys)
   - But endpoints don't actually USE the cache
   - Admin action → DB update → invalidate call → but endpoint always queries DB fresh
   - No TTL or stale-data detection in bot

4. **No Events/Webhooks**
   - Admin updates data
   - Backend has no way to notify bot of changes
   - Bot has no way to know to refresh

---

## Expected vs Actual Behavior

| Scenario | Expected | Actual | Issue |
|----------|----------|--------|-------|
| Admin changes price | Bot shows new price in < 2 min | Bot shows price if endpoint responds, else uses hardcoded fallback | No cache invalidation event |
| Admin uploads image | Image appears in dropdown, auto-linked | Admin manually pastes URL, might forget | No auto-linking |
| Image deleted from disk | Bot shows placeholder or 404 message | Bot still has URL, returns 404 silently | No validation |
| Price cache cleared | Bot refetches within TTL | Invalidation called but endpoint not cached | Ineffective invalidation |
| Button text + image sync | Both available together | Text ✓, Image manual | Partial sync |

---

## Implementation Timeline

**Phase 1: Quick Cache Fix (30 min)**
- Add `@cached_response()` to 4 public endpoints
- Deploy
- Test price sync works within 60 seconds

**Phase 2: Media Persistence (2-3 hours)**
- Create `BotMedia` model
- Create migration
- Deploy
- Test image records persist across restarts

**Phase 3: Auto-Linking (2-3 hours)**
- Modify upload endpoint to create records
- Modify button/plan update to use media_id
- Update public endpoints to return media data
- Deploy
- Test full image sync pipeline

**Total Time: ~5-6 hours**

---

## Verification Checklist

- [ ] Redis cache decorator installed on endpoints
- [ ] Admin changes price → Bot gets new price within 2 seconds
- [ ] BotMedia table created and populated
- [ ] Image upload creates DB record with media_id
- [ ] Button update accepts media_id field
- [ ] Bot buttons include full image data in response
- [ ] Image deleted from disk → No 404 in logs (validation exists)
- [ ] Cache invalidation is called and effective
- [ ] Hardcoded FALLBACK_PLANS removed or rarely used

