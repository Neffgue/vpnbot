# Visual Architecture: Admin-to-Bot Synchronization

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADMIN PANEL                             │
│  (Web UI for editing buttons, texts, settings, menu layout)     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP REST API
                         │
┌─────────────────────────▼────────────────────────────────────────┐
│                    FASTAPI WEB SERVER                            │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Endpoints:                                                  ││
│  │  • PUT /config/{key} → Settings update                       ││
│  │  • PATCH /main-menu-buttons/{id} → Button update             ││
│  │  • PUT /menu-layout → Layout update                          ││
│  │  • PATCH /welcome-texts/{id} → Welcome text update           ││
│  │  • PATCH /tariffs/{id} → Price update                        ││
│  └──────────────────────────────────────────────────────────────┘│
└─────┬────────────────────────────┬──────────────────────────────┘
      │                            │
      │ Persist to DB              │ Invalidate Cache
      │                            │
┌─────▼────────────────────┐  ┌────▼──────────────────────────────┐
│   DATABASE                │  │   IN-MEMORY CACHES (per process)  │
│  (PostgreSQL/SQLite)      │  │  ┌────────────────────────────┐   │
│  ┌────────────────────┐   │  │  │ MainMenuButtonService._cache│  │
│  │ SystemSetting      │   │  │  │ Invalidated by: .invalidate()  │
│  │ MainMenuButton     │   │  │  │                            │   │
│  │ WelcomeText        │   │  │  │ MenuLayoutService._cache   │   │
│  │ Tariff             │   │  │  │ Invalidated by: .invalidate()  │
│  │ User               │   │  │  │                            │   │
│  │ ...                │   │  │  │ BotConfigurationService    │   │
│  └────────────────────┘   │  │  │ (needs reload mechanism)   │   │
└──────────────────────────┘  └────────────────────────────────┘   │
                                                                    │
                              ┌─────────────────────────────────┐   │
                              │    REDIS (Distributed)          │   │
                              │  ┌─────────────────────────────┐│  │
                              │  │ user:{id}                   ││  │
                              │  │ session:{id}:{key}          ││  │
                              │  │ channel_sub:{id}:{ch_id}    ││  │
                              │  │ required_channels:active    ││  │
                              │  │ (All with TTL)              ││  │
                              │  └─────────────────────────────┘│  │
                              └─────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                         ▲
                         │ Query when cache empty
                         │
                    ┌────┴──────────────────────────┐
                    │                               │
        ┌───────────▼──────────────┐   ┌────────────▼──────────────┐
        │  TELEGRAM BOT PROCESS    │   │  TELEGRAM BOT PROCESS     │
        │  (Instance 1)            │   │  (Instance 2)             │
        │  ┌────────────────────┐  │   │  ┌────────────────────┐   │
        │  │ Handler: /start    │  │   │  │ Handler: /start    │   │
        │  │ Handler: /menu     │  │   │  │ Handler: /menu     │   │
        │  │ Handler: buy       │  │   │  │ Handler: buy       │   │
        │  │                    │  │   │  │                    │   │
        │  │ Uses:              │  │   │  │ Uses:              │   │
        │  │ • get_welcome_text │  │   │  │ • get_welcome_text │   │
        │  │ • MainMenuButton   │  │   │  │ • MainMenuButton   │   │
        │  │   Service          │  │   │  │   Service          │   │
        │  │ • MenuLayoutService│  │   │  │ • MenuLayoutService│   │
        │  │ • settings.get_*   │  │   │  │ • settings.get_*   │   │
        │  └────────────────────┘  │   │  └────────────────────┘   │
        └──────────────────────────┘   └─────────────────────────┘
                    ▲                              ▲
                    └──────────────┬───────────────┘
                                   │ Telegram API
                    ┌──────────────▼───────────────┐
                    │   TELEGRAM SERVER            │
                    │   • Users send messages      │
                    │   • Bot responds with menus  │
                    └──────────────────────────────┘
```

---

## Data Flow: Button Text Update Example

```
Timeline: Admin updates button text "Subscribe" → "Buy Now"

t=0ms
  └─ Admin opens admin panel
     
t=100ms
  └─ Admin clicks "Edit Button" → sees current text "Subscribe"
  
t=200ms
  └─ Admin changes text to "Buy Now" and clicks Save
  
t=250ms
  └─ Browser sends: PATCH /api/main-menu-buttons/5
     Body: { "text": "Buy Now" }
  
t=260ms
  ├─ FastAPI endpoint receives request
  ├─ Queries DB: SELECT * FROM main_menu_button WHERE id = 5
  ├─ Database returns current button
  └─ Endpoint updates: button.text = "Buy Now"

t=270ms
  ├─ Endpoint calls: await db.commit()
  ├─ Database persists: UPDATE main_menu_button SET text="Buy Now" WHERE id=5
  └─ Database confirms commit

t=280ms
  ├─ Endpoint calls: MainMenuButtonService.invalidate_cache()
  ├─ Service sets: _cache = None
  └─ In-memory cache cleared
  
t=290ms
  ├─ Endpoint returns: HTTP 200 OK with updated button
  └─ Admin panel shows: "Button updated successfully"

--- Now waiting for user interaction ---

t=5000ms (5 seconds later)
  └─ User sends: /menu command to bot
  
t=5010ms
  ├─ Bot handler: show_main_menu()
  ├─ Calls: MainMenuButtonService.get_buttons_for_user(db, ...)
  └─ Service checks: if _cache is not None
     RESULT: _cache IS None (was invalidated)

t=5020ms
  ├─ Service acquires lock: async with _lock
  ├─ Checks again: if _cache is not None
  ├─ Service queries DB: SELECT * FROM main_menu_button ORDER BY display_order
  ├─ Database returns: [Button(id=5, text="Buy Now", ...)]
  └─ Service sets: _cache = [_MainMenuButtonData(...)]

t=5030ms
  ├─ Service returns: [InlineKeyboardButton(text="Buy Now", ...)]
  ├─ Bot builds keyboard with new button text
  ├─ Sends message: "Main menu" with button "Buy Now"
  └─ User receives updated menu with "Buy Now" button

Total latency: ~280ms (admin sees save confirmation) + 5s (until next user action)
              = User sees change within ~5 seconds of admin save
```

---

## Data Flow: System Setting Update Example (CURRENT PROBLEM)

```
Timeline: Admin updates PRICE_30_DAYS from 199 to 249 kopeks

t=0ms
  └─ Admin opens Settings → Subscription Prices
  
t=100ms
  └─ Admin changes: PRICE_30_DAYS = 249 kopeks and clicks Save

t=150ms
  └─ Browser sends: PUT /api/config/PRICE_30_DAYS
     Body: { "value": 249 }

t=160ms
  ├─ FastAPI endpoint receives request
  ├─ Validates value: is int? Yes ✓
  ├─ Calls: await bot_configuration_service.set_value(db, "PRICE_30_DAYS", 249)
  └─ Function updates: SystemSetting(key="PRICE_30_DAYS", value="249")

t=170ms
  ├─ Endpoint calls: await db.commit()
  ├─ Database persists: UPDATE system_setting SET value="249" WHERE key="PRICE_30_DAYS"
  └─ Database confirms commit

t=180ms
  ├─ ❌ BUG: No cache invalidation!
  └─ Endpoint returns: HTTP 200 OK

t=190ms
  └─ Admin panel shows: "Setting saved" ✓

--- Now waiting for user to buy ---

t=10000ms (10 seconds later)
  └─ User clicks: "Buy subscription"

t=10100ms
  ├─ Bot handler: initiate_subscription()
  ├─ Calls: _prepare_subscription_summary(db_user, data, texts)
  └─ Function reads: PERIOD_PRICES.get(30)
     RESULT: 199 (STALE VALUE!)

t=10110ms
  ├─ Pricing calculation shows: 199 kopeks
  ├─ User sees old price
  └─ Problem: Database has 249 but bot shows 199

t=10120ms
  ├─ Admin doesn't understand why change didn't work
  └─ Solution attempted: Restart bot
     ✓ Now bot reads from DB and gets 249

⚠️  BUG IDENTIFIED:
    - Database updated ✓
    - In-memory settings object NOT reloaded ✗
    - Bot uses stale value until restart ✗
    - No invalidation mechanism ✗

🔧 FIX REQUIRED:
    After db.commit(), call: await settings_service.reload_from_db("PRICE_30_DAYS")
```

---

## Cache State Transitions

### MainMenuButtonService Cache States

```
                     ┌──────────────────┐
                     │   START          │
                     │  _cache = None   │
                     └────────┬─────────┘
                              │
                              │ User requests menu for first time
                              │ get_buttons_for_user() called
                              │
                    ┌─────────▼──────────┐
                    │   LOADING          │
                    │  (acquiring lock)  │
                    └────────┬───────────┘
                             │
                   ┌─────────┴──────────┐
                   │ Load from DB       │
                   │ Parse results      │
                   │ Set _cache = items │
                   └─────────┬──────────┘
                             │
                    ┌────────▼─────────┐
                    │   CACHED         │
                    │  _cache = [...]  │
                    └────┬───────┬─────┘
                         │       │
                    (cache hit)  (invalidate_cache() called
                         │       │  by endpoint)
                         │       │
                    ┌────┴┐    ┌─┴─────────┐
                    │     │    │           │
            ┌──────▼──┐ │  ┌──▼─────┐
            │ CACHED  │─┘  │ INVALID │
            │(reuse)  │    │ _cache  │
            └─────────┘    │= None   │
                           └────┬───┘
                                │
                         (next user action)
                                │
                    ┌───────────▼──────────┐
                    │    (back to LOADING) │
                    └──────────────────────┘
```

---

## Performance Comparison

### Without Caching (Direct DB reads)

```
Request 1:  User asks for menu
  └─ Query DB: 50ms
  └─ Build keyboard: 5ms
  └─ Total: 55ms

Request 2:  User asks for menu again
  └─ Query DB: 50ms (same as request 1)
  └─ Build keyboard: 5ms
  └─ Total: 55ms

1000 Requests:
  └─ DB queries: 1000 × 50ms = 50,000ms = 50 seconds
  └─ Total latency for user: 50ms each
```

### With Caching (First load from DB, rest from cache)

```
Request 1:  User asks for menu
  └─ Cache miss, query DB: 50ms
  └─ Build keyboard: 5ms
  └─ Total: 55ms

Request 2:  Another user asks for menu
  └─ Cache hit, get from memory: 0.1ms
  └─ Build keyboard: 5ms
  └─ Total: 5.1ms

1000 Requests:
  └─ DB queries: 1 × 50ms = 50ms (only first request)
  └─ Cache hits: 999 × 0.1ms = 0.1ms
  └─ Total: 50.1ms
  └─ User latency: First user 55ms, others 5ms each

Performance improvement: 1000x faster after first request!
```

---

## Cache Invalidation Trigger Matrix

| Component | Trigger | Method | Result |
|-----------|---------|--------|--------|
| MainMenuButton | CRUD on button | `MainMenuButtonService.invalidate_cache()` | _cache = None |
| MainMenuButton | Reorder buttons | `MainMenuButtonService.invalidate_cache()` | _cache = None |
| MenuLayout | Update config | `MenuLayoutService.save_config()` | Calls invalidate_cache() |
| MenuLayout | Update row | `MenuLayoutService.save_config()` | Calls invalidate_cache() |
| MenuLayout | Update button in layout | `MenuLayoutService.save_config()` | Calls invalidate_cache() |
| WelcomeText | Create/Update/Delete | Direct DB (no cache) | N/A |
| Tariff | Create/Update/Delete | Direct DB (no cache) | N/A |
| SystemSetting | Update setting | ❌ **NOT INVALIDATED** | ⚠️ **BUG** |
| ChannelSub | Set subscription | `ChannelSubCache.set_sub_status()` | Stored in Redis w/ TTL |
| ChannelSub | Manual invalidation | `ChannelSubCache.invalidate_sub()` | Deleted from Redis |

---

## Redis Key Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ Example: Channel subscription cache for user 123            │
└─────────────────────────────────────────────────────────────┘

Key: channel_sub:123:@required_channel
TTL: 600 seconds (10 minutes)
Value: 1 (user is member) or 0 (user is not member)

Timeline:

t=0s
  └─ User joins channel @required_channel
  └─ Bot middleware checks: ChannelSubCache.get_sub_status(123, "@required_channel")
     └─ Cache miss (key doesn't exist yet)
     └─ Bot queries Telegram API
     └─ Telegram: Yes, user 123 is member
     └─ Cache: ChannelSubCache.set_sub_status(123, "@required_channel", True)
        └─ Redis: SET channel_sub:123:@required_channel 1 EX 600

t=0.5s
  └─ Same user sends another message
  └─ Middleware checks cache
  └─ Redis returns: 1 (cache hit!)
  └─ No Telegram API call needed

t=300s (5 minutes pass)
  └─ User still active, sending messages
  └─ Cache still valid (TTL still 300s remaining)
  └─ Redis returns: 1

t=600s (10 minutes pass)
  └─ Redis auto-deletes key (TTL expired)
  └─ Key no longer exists

t=600.5s
  └─ User sends another message
  └─ Middleware checks cache
  └─ Cache miss (key expired)
  └─ Bot queries Telegram API again (fresh check)
  └─ Telegram returns: Yes, still member
  └─ Cache: SET with new 10-minute TTL

Result: User subscription status checked every 10 minutes automatically
```

---

## Multi-Process Deployment Issue

```
WITHOUT Distributed Cache Invalidation:

┌─────────────────┐           ┌─────────────────┐
│ Bot Process 1   │           │ Bot Process 2   │
│ _cache = None   │           │ _cache = None   │
└────────┬────────┘           └────────┬────────┘
         │                             │
         │ Load from DB                │ Load from DB
         │                             │
         ├─ _cache = [v1,v2]         ├─ _cache = [v1,v2]
         │                             │
         └─────────────┬───────────────┘
                       │
             Admin updates button
             (but which process gets invalidated?)
                       │
         ┌─────────────┴───────────────┐
         │                             │
         ├─ Gets invalidation call    ├─ ❌ Doesn't get notified!
         │   _cache = None             │   _cache = [v1,v2] (STALE!)
         │                             │
         └─────────────┬───────────────┘
                       │
              Next user requests menu
                       │
         ┌─────────────┴───────────────┐
         │                             │
         ├─ Cache miss, reloads [v1'] ├─ Cache hit, serves [v1]
         │  Shows new button ✓         │  Shows OLD button ❌
         │                             │


WITH Redis Pub/Sub Invalidation:

         ┌─────────────────┐           ┌─────────────────┐
         │ Bot Process 1   │           │ Bot Process 2   │
         │ subscribed to:  │           │ subscribed to:  │
         │ cache:invalidate│           │ cache:invalidate│
         │ :menu_buttons   │           │ :menu_buttons   │
         └────────┬────────┘           └────────┬────────┘
                  │                             │
     Admin updates button through ANY endpoint  │
     (could be through process 1, 2, or API)   │
                  │                             │
     Endpoint calls:                            │
     await pubsub.publish(                      │
         'cache:invalidate:menu_buttons',       │
         ...                                    │
     )                                          │
                  │                             │
                  └─────────────┬───────────────┘
                                │
                    ┌───────────┴────────────┐
                    │                        │
         Message arrives at Process 1   Message arrives at Process 2
         _cache = None                   _cache = None
         Both processes reload fresh!    Both stay in sync!
```

---

## Time to Reflect Change (Expected Timings)

```
┌─────────────────────────────────────────────────────────────────┐
│               When Does User See Change?                         │
└─────────────────────────────────────────────────────────────────┘

Component         │ Storage    │ Cache    │ Invalidation   │ User Sees
──────────────────┼────────────┼──────────┼────────────────┼──────────
WelcomeText       │ DB direct  │ None     │ N/A            │ Next /start
MenuButton        │ DB + cache │ Memory   │ Endpoint call  │ Next menu (0.5-1s)
MenuLayout        │ DB + cache │ Memory   │ Endpoint call  │ Next menu (0.5-1s)
Tariff prices     │ DB direct  │ None     │ N/A            │ Next pricing calc
SystemSettings    │ DB + cache │ In-mem   │ ❌ BROKEN       │ ⚠️ AFTER RESTART
ChannelSub        │ Redis+DB   │ Redis    │ TTL expires    │ 10 min delay
UserSession       │ Redis      │ Redis    │ TTL expires    │ 30 min delay

Legend:
  DB direct = Always reads fresh from database
  Memory = Per-process in-memory cache
  Redis = Distributed cache with TTL
  Next = On next user action that triggers that code path
```

---

## Summary: The Sync Flow in One Diagram

```
ADMIN MAKES CHANGE
        ↓
FASTAPI ENDPOINT
        ↓
    VALIDATE
        ↓
 SAVE TO DATABASE
        ↓
  INVALIDATE CACHE
        ↓
RETURN SUCCESS
        ↓
[Waiting for user...]
        ↓
USER SENDS MESSAGE
        ↓
BOT HANDLER EXECUTES
        ↓
SERVICE READS CACHE
    ↙        ↘
 HIT         MISS
  ↓           ↓
RETURN    RELOAD FROM DB
CACHED      ↓
 DATA    CACHE RESULT
  ↓         ↓
  └────┬────┘
       ↓
   BUILD RESPONSE
       ↓
  SEND TO USER
       ↓
USER SEES CHANGE ✓
```

