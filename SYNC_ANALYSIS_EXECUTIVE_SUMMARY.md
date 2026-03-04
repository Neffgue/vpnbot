# VPN Bot Admin Panel Sync Issues - Executive Summary

## The Core Problem

**The bot and admin panel are completely desynchronized because the bot ignores the admin panel's database changes and uses hardcoded values instead.**

When admin changes data via the web panel (prices, buttons, messages), it saves to the database ✓, but the bot doesn't read from the database - it reads from hardcoded Python dictionaries. This causes:
- Users see old prices, get charged new prices
- Admin changes menu buttons, users still see old buttons
- Worker sends notification texts that can never be updated

---

## 5 CRITICAL BUGS

### 🔴 BUG #1: Subscription Price Mismatch (REVENUE RISK)
**Location:** `bot/handlers/payment.py` lines 56-67 & 139-140

**What happens:**
1. Admin changes price: 30-day Solo plan from 150₽ → 200₽
2. Backend saves to database ✓
3. Bot shows user: "30 дней — 150₽" (HARDCODED from PLAN_PRICES dict)
4. User clicks expecting 150₽
5. Backend charges 200₽ (from database)
6. **User sees unexpected charge - billing dispute!**

**Root cause:** Bot never calls API to fetch plans. Lines 139-140 read from hardcoded `PLAN_PRICES["solo"]["prices"][30]` = 150

**Impact:** Lost revenue, refunds, billing disputes, user complaints

---

### 🔴 BUG #2: Menu Buttons Not Updating (UX BROKEN)
**Location:** `bot/keyboards/main_menu.py` lines 8-43

**What happens:**
1. Admin updates button text: "💸 Оплатить тариф" → "💳 Купить подписку"
2. Backend saves to database ✓ + invalidates Redis cache ✓
3. Bot tries to fetch from `/bot-buttons/public` endpoint
4. **Endpoint doesn't exist** → returns error
5. Bot falls back to hardcoded buttons in `_build_default_buttons()` function
6. User still sees old button text: "💸 Оплатить тариф"

**Root cause:** 
- Public endpoint `/bot-buttons/public` never created
- Bot's fallback uses hardcoded buttons instead of admin-configured ones

**Impact:** User confusion, broken marketing campaigns

---

### 🔴 BUG #3: Notification Text Never Updates (STALE MESSAGES)
**Location:** `worker/tasks/notifications.py` lines 103-208

**What happens:**
1. Admin might want to change notification text (in future)
2. Worker task runs every hour with HARDCODED message templates
3. Lines 106-207: All notification texts are embedded as Python strings
4. Worker NEVER checks database or API for updated texts
5. **Message content cannot be changed without redeploying worker**

**Root cause:** Notification texts hardcoded in task. No database/API fetch logic.

**Impact:** Can't respond to issues, stale messaging, broken campaigns

---

### 🟡 BUG #4: Connection Pool Exhaustion (SERVER CRASHES)
**Location:** `backend/database.py` line 24

**What happens:**
1. Admin broadcasts to 1000 users
2. Backend tries to create 1000 database connections
3. `poolclass=NullPool` means: create new connection, use it, close it
4. Under load, database receives 1000 open/close events rapidly
5. Database max_connections limit hit
6. **Server returns ERR_CONNECTION_RESET errors**

**Root cause:** NullPool creates/destroys connection for each request instead of reusing

**Impact:** Broadcast failures, server crashes, "ERR_CONNECTION_RESET" errors

---

### 🟡 BUG #5: No Transaction Atomicity (DATA CORRUPTION RISK)
**Location:** `backend/api/v1/endpoints/admin.py` - multiple endpoints

**What happens:**
1. Admin updates button text via PUT `/admin/bot-buttons/{id}`
2. Code reads button from DB ✓
3. Updates button value ✓
4. Calls `await db.commit()` at line 483
5. If commit fails → session left in error state
6. No try-finally block to recover
7. **Session might hang, connection never returned to pool**
8. Eventually all connections exhausted

**Root cause:** Missing try-except-finally around database transactions

**Impact:** Cascading failures, connection leaks, eventual server crash

---

## WHERE DATA IS HARDCODED

| What | File | Lines | Why It's Broken |
|------|------|-------|-----------------|
| **Subscription Prices** | `bot/handlers/payment.py` | 56-67, 139-140 | Never fetches from API; dict hardcoded in Python |
| **Plan Names/Devices** | `bot/handlers/payment.py` | 39-45, 280-286 | Button text hardcoded; could be 1-5 devices but hardcoded to 1 or 5 |
| **Main Menu Buttons** | `bot/keyboards/main_menu.py` | 8-43 | Fallback uses hardcoded buttons when API fails |
| **All Button Texts** | `bot/keyboards/subscription_kb.py` | 6-73 | Could be dynamic but not currently |
| **Cancel/Back Buttons** | `bot/keyboards/inline_kb.py` | 5-103 | Helper buttons, less critical |
| **Notification Texts** | `worker/tasks/notifications.py` | 103-208 | Embedded as Python strings; never fetches from DB |

---

## WHY SYNC FAILS: TECHNICAL ROOT CAUSES

### Root Cause #1: Missing Public API Endpoints
Bot tries to call:
- `GET /bot-buttons/public` → **DOESN'T EXIST**
- `GET /bot-texts/public` → **DOESN'T EXIST**
- `GET /bot-settings/public` → **DOESN'T EXIST**
- `GET /subscriptions/plans/public` → **DOESN'T EXIST**

These endpoints should return fresh data from database (with Redis caching). When they don't exist, bot falls back to hardcoded values.

### Root Cause #2: Bot Never Fetches Dynamic Data
Bot code doesn't call any API to get:
- Subscription plans and prices
- Menu button configuration
- Notification message templates

It only reads hardcoded Python dictionaries and strings.

### Root Cause #3: Worker Never Fetches from Database
Worker task has hardcoded notification text templates. It never:
- Calls API to fetch templates
- Reads from database
- Checks if admin changed the text

### Root Cause #4: Infrastructure Problem
Connection pool is misconfigured (`NullPool` instead of `QueuePool`), causing:
- Every request = new DB connection
- Broadcasts kill the server by creating 1000+ connections rapidly
- No connection reuse

---

## WHAT'S WORKING CORRECTLY ✓

- Admin panel CAN save data to database ✓
- Backend CAN invalidate Redis cache ✓
- Broadcast infrastructure uses BackgroundTasks (doesn't hang) ✓
- Welcome text/image WORK because they have fallback to `/admin/` endpoints ✓

---

## HOW TO FIX (High Level)

### 1. Create Missing Public Endpoints (Backend)
Create these 4 new endpoints that return fresh data (cached with Redis):
- `GET /bot-buttons/public`
- `GET /bot-texts/public`
- `GET /bot-settings/public`
- `GET /subscriptions/plans/public`

### 2. Fix Subscription Prices (Bot)
- Remove hardcoded `PLAN_PRICES` dictionary
- Load plans from `/subscriptions/plans/public` API instead
- Generate price buttons dynamically

### 3. Fix Notification Task (Worker)
- Create `/admin/notification-templates` API endpoints
- Store notification texts in database (BotText table)
- Fetch from database before sending (with fallback to hardcoded)

### 4. Fix Connection Pool (Backend)
- Change `poolclass=NullPool` to `poolclass=QueuePool` with proper pool_size
- One-line fix, prevents server crashes

### 5. Add Error Handling (Backend)
- Wrap all DB transactions in try-except-finally
- Ensures sessions always returned to pool

---

## FILES THAT NEED CHANGES

### Backend (New endpoints needed)
- `backend/api/v1/endpoints/admin.py` or new `backend/api/v1/endpoints/public.py`
  - Add 4 public endpoints for buttons, texts, settings, plans
  - Implement Redis caching with invalidation on admin updates
  - Fix try-finally in admin endpoint handlers

- `backend/database.py`
  - Change connection pool from NullPool to QueuePool (1 line)

### Bot (Fetch from API instead of hardcoded)
- `bot/handlers/payment.py`
  - Remove PLAN_PRICES hardcoded dict
  - Fetch plans from API endpoint
  - Generate keyboard dynamically

- `bot/keyboards/main_menu.py`
  - Ensure get_dynamic_main_menu() uses `/bot-buttons/public` (already tries, but endpoint missing)

### Worker (Fetch from database)
- `worker/tasks/notifications.py`
  - Fetch notification templates from API or database
  - Fall back to hardcoded only if unavailable

---

## BUSINESS IMPACT

| Issue | Severity | Impact | Frequency |
|-------|----------|--------|-----------|
| Price mismatch | 🔴 CRITICAL | Revenue loss, billing disputes | Every subscription after price change |
| Buttons not updating | 🔴 CRITICAL | User confusion, marketing breaks | Every /start after button change |
| Notifications stuck | 🔴 CRITICAL | Can't respond to issues, stale messaging | Every hour (recurring task) |
| Server crashes | 🟡 HIGH | Broadcast failures, downtime | Every large broadcast |
| Session hangs | 🟡 HIGH | Cascading failures, eventual crash | Every admin update |

---

## RECOMMENDED NEXT STEPS

1. **Immediate** (today): Fix connection pool - 1 line change in database.py
2. **This sprint** (this week): 
   - Create 4 public endpoints
   - Fix subscription prices bot code
   - Fix notification task
3. **Follow-up**: Add try-finally to all admin endpoints

This will fully synchronize the bot with admin panel changes.

