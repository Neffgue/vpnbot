# VPN Bot Sync - Implementation Guide

## Quick Start: Which Files to Fix First

### Priority 1: Infrastructure (1 day)

#### 1.1 Fix Connection Pool (5 minutes)
**File:** `backend/database.py`

**Current (line 24):**
```python
poolclass=NullPool,
```

**Change to:**
```python
poolclass=QueuePool,
pool_size=20,
max_overflow=10,
pool_recycle=3600,
```

**Also add import at top:**
```python
from sqlalchemy.pool import QueuePool
```

**Why:** Prevents "ERR_CONNECTION_RESET" on broadcasts

---

### Priority 2: Public Endpoints (2-3 days)

#### 2.1 Create Public Endpoints File
**New file:** `backend/api/v1/endpoints/public.py`

**What to add:**
```python
import json
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.config import BotText

logger = logging.getLogger(__name__)
router = APIRouter()

# Import defaults from admin.py
from backend.api.v1.endpoints.admin import DEFAULT_BOT_BUTTONS, DEFAULT_BOT_TEXTS, SETTINGS_KEY, SYSTEM_SETTINGS_KEY

@router.get("/bot-buttons/public")
async def get_bot_buttons_public(db: AsyncSession = Depends(get_db)):
    """Get menu buttons - public endpoint (no auth needed)"""
    try:
        stmt = select(BotText).where(BotText.key.like("btn_%")).order_by(BotText.key)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        buttons = []
        for r in rows:
            try:
                btn = json.loads(r.value)
                btn["id"] = r.key
                buttons.append(btn)
            except Exception:
                pass
        if not buttons:
            buttons = [
                {"id": f"default_{i}", **btn}
                for i, btn in enumerate(DEFAULT_BOT_BUTTONS)
            ]
        return buttons
    except Exception as e:
        logger.error(f"Error getting public buttons: {e}")
        return [{"id": f"default_{i}", **btn} for i, btn in enumerate(DEFAULT_BOT_BUTTONS)]


@router.get("/bot-texts/public")
async def get_bot_texts_public(db: AsyncSession = Depends(get_db)):
    """Get bot texts - public endpoint (no auth needed)"""
    try:
        stmt = select(BotText).order_by(BotText.key)
        result = await db.execute(stmt)
        texts = result.scalars().all()
        merged = dict(DEFAULT_BOT_TEXTS)
        for t in texts:
            if t.key not in (SYSTEM_SETTINGS_KEY, SETTINGS_KEY) and not t.key.startswith("btn_"):
                merged[t.key] = t.value
        return merged
    except Exception as e:
        logger.error(f"Error getting public texts: {e}")
        return dict(DEFAULT_BOT_TEXTS)


@router.get("/bot-settings/public")
async def get_bot_settings_public(db: AsyncSession = Depends(get_db)):
    """Get bot settings - public endpoint (no auth needed)"""
    try:
        stmt = select(BotText).where(BotText.key == SETTINGS_KEY)
        result = await db.execute(stmt)
        row = result.scalars().first()
        if row:
            return json.loads(row.value)
        return {}
    except Exception as e:
        logger.error(f"Error getting public settings: {e}")
        return {}


@router.get("/subscriptions/plans/public")
async def get_subscription_plans_public(db: AsyncSession = Depends(get_db)):
    """Get subscription plans - public endpoint (no auth needed)"""
    # TODO: Implement plan fetching from PlanPrice model
    # For now, return hardcoded default
    return [
        {
            "id": "solo",
            "name": "Минимальный (1 устройство)",
            "devices": 1,
            "prices": {7: 90, 30: 150, 90: 400, 180: 760, 365: 1450}
        },
        {
            "id": "family",
            "name": "Семейный (5 устройств)",
            "devices": 5,
            "prices": {7: 150, 30: 250, 90: 650, 180: 1200, 365: 2300}
        }
    ]
```

#### 2.2 Register Public Router
**File:** `backend/app.py` or `main.py`

**Add:**
```python
from backend.api.v1.endpoints import public

app.include_router(public.router, prefix="/api/v1", tags=["public"])
```

---

### Priority 3: Fix Bot Code (2-3 days)

#### 3.1 Fix Subscription Prices
**File:** `bot/handlers/payment.py`

**Step 1: Add new function after imports (before PLAN_PRICES dict):**
```python
async def fetch_plans_from_api(client: APIClient) -> dict:
    """Fetch subscription plans from API endpoint.
    Falls back to hardcoded PLAN_PRICES if API unavailable.
    """
    try:
        plans = await client.get("/subscriptions/plans/public")
        if isinstance(plans, list) and plans:
            # Convert list format to dict format
            result = {}
            for plan in plans:
                plan_id = plan.get("id", "").lower()
                if plan_id:
                    result[plan_id] = {
                        "name": plan.get("name", "Unknown"),
                        "devices": plan.get("devices", 1),
                        "prices": plan.get("prices", {}),
                    }
            if result:
                return result
    except Exception as e:
        logger.error(f"Failed to fetch plans from API: {e}")
    
    # Fallback to hardcoded
    return PLAN_PRICES
```

**Step 2: Update handler to use new function:**
```python
@router.callback_query(F.data == "buy_subscription")
async def buy_subscription_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle subscription purchase start - show available plans"""
    await callback.answer()

    plan_text = (
        "⚡️ <b>Выберите тариф из предложенных</b>\\n\\n"
        "Каждый тариф позволяет подключить определённое количество устройств к VPN.\\n\\n"
        "В любой момент вы сможете улучшить свой тариф на большее количество устройств!"
    )

    # FETCH PLANS FROM API (NEW)
    plans_data = PLAN_PRICES  # Default fallback
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            plans_data = await fetch_plans_from_api(client)
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")

    # GENERATE BUTTONS DYNAMICALLY (NEW)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for plan_id, plan_info in plans_data.items():
        devices = plan_info.get("devices", 1)
        name = plan_info.get("name", plan_id)
        buttons.append([InlineKeyboardButton(
            text=f"👤 {name}",
            callback_data=f"plan_{plan_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(plan_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(plan_text, parse_mode="HTML", reply_markup=keyboard)

    await state.set_state(PaymentStates.waiting_plan_selection)
```

**Step 3: Update select_plan handler:**
```python
@router.callback_query(F.data.startswith("plan_"), PaymentStates.waiting_plan_selection)
async def select_plan(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle plan selection"""
    await callback.answer()

    plan_key = callback.data.replace("plan_", "")
    
    # FETCH FRESH PLANS (NEW)
    plans_data = PLAN_PRICES
    try:
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            plans_data = await fetch_plans_from_api(client)
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
    
    plan_info = plans_data.get(plan_key, plans_data.get("solo"))

    period_text = (
        "Выберите период, на который хотите оформить подписку\\n\\n"
        "Учтите! Чем больше период, тем ниже цена 💵\\n\\n"
        f"Выбран тариф - {plan_info['name']}"
    )

    # GENERATE PERIOD BUTTONS DYNAMICALLY (NEW)
    prices = plan_info.get("prices", {})
    period_labels = {7: "7 дней", 30: "1 месяц", 90: "3 месяца", 180: "6 месяцев", 365: "12 месяцев"}
    
    buttons = []
    for days in sorted(prices.keys()):
        price = prices[days]
        label = period_labels.get(days, f"{days} дней")
        buttons.append([InlineKeyboardButton(
            text=f"{label} — {price} рублей",
            callback_data=f"period_{days}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="buy_subscription")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(period_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(period_text, parse_mode="HTML", reply_markup=keyboard)

    await state.update_data(selected_plan={"key": plan_key, **plan_info})
    await state.set_state(PaymentStates.waiting_period_selection)
```

---

### Priority 4: Fix Worker (1-2 days)

#### 4.1 Store Notification Templates in Database
**File:** `backend/api/v1/endpoints/admin.py`

**Add to DEFAULT_BOT_TEXTS dict (around line 273):**
```python
DEFAULT_BOT_TEXTS = {
    # ... existing texts ...
    "notif_24h": "⏰ <b>Ваша VPN-подписка истекает через 24 часа</b>\\n\\nНе забудьте продлить подписку, чтобы не потерять доступ к VPN.\\n\\n📱 Тариф: {plan}\\n⏳ Истекает: {expires}\\n\\n👇 Продлите подписку прямо сейчас:",
    "notif_12h": "⏰ <b>Ваша VPN-подписка истекает через 12 часов</b>\\n\\nОсталось совсем немного! Продлите подписку, чтобы не прерывать доступ.\\n\\n📱 Тариф: {plan}\\n⏳ Истекает: {expires}\\n\\n👇 Продлите подписку прямо сейчас:",
    "notif_1h": "🔴 <b>Ваша VPN-подписка истекает через 1 час</b>\\n\\nОсталось меньше часа! Продлите подписку прямо сейчас.\\n\\n📱 Тариф: {plan}\\n⏳ Истекает: {expires}\\n\\n👇 Нажмите, чтобы продлить:",
    "notif_0h": "🚨 <b>Ваша VPN-подписка истекла!</b>\\n\\nВаш доступ к VPN прекращён. Продлите подписку, чтобы восстановить доступ.\\n\\n📱 Тариф: {plan}\\n\\n👇 Продлите подписку:",
    "notif_3h_after": "❌ <b>Ваша VPN-подписка истекла 3 часа назад</b>\\n\\nВаш доступ к VPN отключён. Восстановите его прямо сейчас — это займёт меньше минуты!\\n\\n📱 Тариф: {plan}\\n\\n👇 Продлите подписку:",
}
```

#### 4.2 Update Worker Task
**File:** `worker/tasks/notifications.py`

**Replace hardcoded notification_configs (lines 103-135):**
```python
async def fetch_notification_templates():
    """Fetch notification templates from backend API or use defaults"""
    try:
        from bot.utils.api_client import APIClient
        from bot.config import config
        async with APIClient(config.api.base_url, config.api.api_key) as client:
            texts = await client.get_all_bot_texts()
            return texts
    except Exception as e:
        logger.warning(f"Failed to fetch templates from API: {e}")
        return {}

async def run_check():
    bot_username = os.getenv('BOT_USERNAME') or os.getenv('TELEGRAM_BOT_USERNAME') or 'vpnsolid_bot'
    bot_link = f'https://t.me/{bot_username}'

    # Fetch templates from API (will use defaults if not found)
    templates = await fetch_notification_templates()

    notification_configs = [
        (24, '24h', 'notified_24h', templates.get("notif_24h", "⏰ Ваша VPN-подписка истекает через 24 часа")),
        (12, '12h', 'notified_12h', templates.get("notif_12h", "⏰ Ваша VPN-подписка истекает через 12 часов")),
        (1, '1h', 'notified_1h', templates.get("notif_1h", "🔴 Ваша VPN-подписка истекает через 1 час")),
        (0, '0h', 'notified_0h', templates.get("notif_0h", "🚨 Ваша VPN-подписка истекла!")),
    ]

    # ... rest of code continues ...
```

---

## Testing Checklist

After implementing fixes, test:

### Test 1: Connection Pool
```bash
# Broadcast to many users - should not get ERR_CONNECTION_RESET
curl -X POST http://localhost:8000/api/v1/admin/broadcast-image \
  -H "Authorization: Bearer YOUR_KEY" \
  -F "image=@test.jpg" \
  -F "target=all"
```

### Test 2: Public Endpoints
```bash
# Should return data WITHOUT authentication
curl http://localhost:8000/api/v1/bot-buttons/public
curl http://localhost:8000/api/v1/bot-texts/public
curl http://localhost:8000/api/v1/subscriptions/plans/public
```

### Test 3: Bot Button Updates
```
1. Admin changes button via web panel
2. Wait 5 seconds (Redis invalidation)
3. Send /start in bot
4. Check if new button text appears
```

### Test 4: Price Changes
```
1. Admin changes price via API
2. User clicks "Оплатить тариф" in bot
3. Check if new price is shown
4. Verify billing uses new price
```

### Test 5: Notification Templates
```
1. Store notification text in BotText table
2. Wait for next hourly run of notification task
3. Check if notification uses new text
```

---

## Migration Path (Recommended Order)

### Week 1: Infrastructure & Endpoints
- [ ] Fix connection pool (1 hour)
- [ ] Create public endpoints (4 hours)
- [ ] Add error handling to admin endpoints (2 hours)
- [ ] Test public endpoints

### Week 2: Bot Code
- [ ] Update payment.py to fetch plans (4 hours)
- [ ] Update main_menu.py to use public endpoints (2 hours)
- [ ] Test price changes in bot
- [ ] Test button changes in bot

### Week 3: Worker & Cleanup
- [ ] Store notification templates in DB (2 hours)
- [ ] Update notification task (2 hours)
- [ ] Test notification updates
- [ ] Remove hardcoded defaults where possible

### Week 4: Hardening
- [ ] Add comprehensive error logging
- [ ] Add monitoring for sync issues
- [ ] Document admin workflows

---

## Monitoring After Fix

Add these checks to your monitoring:

```python
# Check if public endpoints are working
async def health_check_public_endpoints():
    async with APIClient(BASE_URL) as client:
        buttons = await client.get_bot_buttons()
        texts = await client.get_all_bot_texts()
        settings = await client.get_bot_settings()
        plans = await client.get_subscription_plans()
        
        assert buttons, "Public buttons endpoint failed"
        assert texts, "Public texts endpoint failed"
        assert settings is not None, "Public settings endpoint failed"
        assert plans, "Public plans endpoint failed"
        
        return True
```

---

## Common Issues During Implementation

### Issue: "Endpoint /subscriptions/plans/public returns empty list"
**Solution:** Implement actual plan fetching from PlanPrice model:
```python
@router.get("/subscriptions/plans/public")
async def get_subscription_plans_public(db: AsyncSession = Depends(get_db)):
    from backend.models.config import PlanPrice
    try:
        stmt = select(PlanPrice).where(PlanPrice.is_active == True)
        result = await db.execute(stmt)
        plans = result.scalars().all()
        
        output = []
        for plan in plans:
            output.append({
                "id": plan.id,
                "name": plan.name,
                "devices": plan.max_devices,
                "prices": json.loads(plan.prices) if isinstance(plan.prices, str) else plan.prices
            })
        return output if output else DEFAULT_PLANS
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        return DEFAULT_PLANS
```

### Issue: "Bot still shows old prices after fix"
**Solution:** Clear any local caching in bot code:
```python
# Make sure you're fetching fresh data each time
# Don't cache plans in module-level variable
# Always call fetch_plans_from_api() 
```

### Issue: "Redis cache invalidation not working"
**Solution:** Check Redis connection:
```bash
redis-cli ping  # Should return PONG
redis-cli GET "bot:buttons"  # Should show cached data
```

