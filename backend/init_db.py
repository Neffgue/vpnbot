"""Создание таблиц БД при старте контейнера и заполнение дефолтными данными."""
import asyncio
import sys
import os

sys.path.insert(0, '/app')
# Для запуска вне Docker (например на AlwaysData)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Дефолтные тарифы (соответствуют PLAN_PRICES в bot/handlers/payment.py)
DEFAULT_PLANS = [
    {"plan_name": "Solo", "period_days": 7,   "price_rub": 90,   "device_limit": 1},
    {"plan_name": "Solo", "period_days": 30,  "price_rub": 150,  "device_limit": 1},
    {"plan_name": "Solo", "period_days": 90,  "price_rub": 400,  "device_limit": 1},
    {"plan_name": "Solo", "period_days": 180, "price_rub": 760,  "device_limit": 1},
    {"plan_name": "Solo", "period_days": 365, "price_rub": 1450, "device_limit": 1},
    {"plan_name": "Family", "period_days": 7,   "price_rub": 150,  "device_limit": 3},
    {"plan_name": "Family", "period_days": 30,  "price_rub": 250,  "device_limit": 3},
    {"plan_name": "Family", "period_days": 90,  "price_rub": 650,  "device_limit": 3},
    {"plan_name": "Family", "period_days": 180, "price_rub": 1200, "device_limit": 3},
    {"plan_name": "Family", "period_days": 365, "price_rub": 2300, "device_limit": 3},
]

# Дефолтные тексты бота
DEFAULT_BOT_TEXTS = {
    "welcome": (
        "👋 <b>Добро пожаловать в VPN бот!</b>\n\n"
        "🔒 Быстрый, надёжный и безопасный VPN.\n\n"
        "Выберите действие в меню ниже:"
    ),
    "free_trial_used": (
        "❌ <b>Бесплатный доступ уже использован</b>\n\n"
        "<blockquote>Каждый аккаунт может получить пробный доступ только один раз.</blockquote>\n\n"
        "💸 Оформите подписку для продолжения:"
    ),
    "cabinet_header": "👤 <b>Личный кабинет</b>",
    "support_text": "💬 Для связи с поддержкой напишите @TechWizardsSupport",
    "channel_text": "📢 Наш канал: https://t.me/techwizardsru",
    "payment_success": "✅ <b>Оплата прошла успешно!</b>\n\nВаша подписка активирована.",
    "payment_failed": "❌ <b>Ошибка оплаты.</b>\n\nПопробуйте ещё раз или обратитесь в поддержку.",
    "subscription_expiring_24h": "⚠️ <b>Ваша подписка истекает через 24 часа.</b>\n\nПродлите её, чтобы не потерять доступ.",
    "subscription_expiring_1h": "⚠️ <b>Ваша подписка истекает через 1 час!</b>\n\nСрочно продлите подписку.",
    "subscription_expired": "❌ <b>Ваша подписка истекла.</b>\n\nОформите новую подписку для продолжения.",
    "referral_header": "🤝 <b>Партнёрская программа</b>",
}


async def create_tables():
    from backend.database import get_engine, Base
    # Импортируем все модели чтобы Base знал о них
    from backend.models import user, subscription, server, payment, referral  # noqa
    from backend.models.config import PlanPrice, BotText, Broadcast  # noqa

    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()
    print("  Tables created/verified OK")


async def seed_default_data():
    """Заполнить БД дефолтными тарифами и текстами если их нет."""
    from backend.database import get_engine
    from backend.models.config import PlanPrice, BotText
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from uuid import uuid4

    eng = get_engine()
    async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed plan prices
        result = await session.execute(select(PlanPrice))
        existing_plans = result.scalars().all()
        existing_keys = {(p.plan_name, p.period_days) for p in existing_plans}

        added_plans = 0
        for plan in DEFAULT_PLANS:
            key = (plan["plan_name"], plan["period_days"])
            if key not in existing_keys:
                session.add(PlanPrice(
                    id=str(uuid4()),
                    plan_name=plan["plan_name"],
                    period_days=plan["period_days"],
                    price_rub=plan["price_rub"],
                    device_limit=plan.get("device_limit", 1),
                    is_active=True,
                ))
                added_plans += 1

        # Seed bot texts
        result = await session.execute(select(BotText))
        existing_texts = {t.key for t in result.scalars().all()}

        added_texts = 0
        for key, value in DEFAULT_BOT_TEXTS.items():
            if key not in existing_texts:
                session.add(BotText(
                    id=str(uuid4()),
                    key=key,
                    value=value,
                    description=f"Default text for {key}",
                ))
                added_texts += 1

        await session.commit()
        if added_plans:
            print(f"  Seeded {added_plans} default plan prices")
        if added_texts:
            print(f"  Seeded {added_texts} default bot texts")
        if not added_plans and not added_texts:
            print("  Default data already present, skipping seed")

    await eng.dispose()


async def main():
    await create_tables()
    await seed_default_data()


if __name__ == "__main__":
    asyncio.run(main())
