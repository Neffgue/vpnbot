"""Script to initialize plan_prices table with default VPN subscription plans."""
import asyncio
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from backend.config import settings
from backend.database import Base, get_engine
from backend.models.config import PlanPrice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
import uuid

DEFAULT_PLANS = [
    # Solo — 1 устройство
    {"plan_name": "Solo", "period_days": 7,   "price_rub": 99},
    {"plan_name": "Solo", "period_days": 30,  "price_rub": 299},
    {"plan_name": "Solo", "period_days": 90,  "price_rub": 799},
    {"plan_name": "Solo", "period_days": 180, "price_rub": 1399},
    {"plan_name": "Solo", "period_days": 365, "price_rub": 2499},
    # Family — до 5 устройств
    {"plan_name": "Family", "period_days": 7,   "price_rub": 199},
    {"plan_name": "Family", "period_days": 30,  "price_rub": 599},
    {"plan_name": "Family", "period_days": 90,  "price_rub": 1599},
    {"plan_name": "Family", "period_days": 180, "price_rub": 2799},
    {"plan_name": "Family", "period_days": 365, "price_rub": 4999},
]


async def main():
    print(f"DB URL: {settings.DATABASE_URL}")
    engine = get_engine()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created/verified OK")

    async with AsyncSession(engine) as session:
        # Check existing
        result = await session.execute(select(PlanPrice))
        existing = result.scalars().all()
        print(f"Existing plans: {len(existing)}")

        # Insert only missing plans
        inserted = 0
        for plan_data in DEFAULT_PLANS:
            # Check if already exists
            result = await session.execute(
                select(PlanPrice).where(
                    PlanPrice.plan_name == plan_data["plan_name"],
                    PlanPrice.period_days == plan_data["period_days"],
                )
            )
            existing_plan = result.scalars().first()
            if not existing_plan:
                session.add(PlanPrice(
                    id=str(uuid.uuid4()),
                    plan_name=plan_data["plan_name"],
                    period_days=plan_data["period_days"],
                    price_rub=plan_data["price_rub"],
                ))
                inserted += 1

        await session.commit()
        print(f"Inserted {inserted} new plans")

        # Verify
        result = await session.execute(
            select(PlanPrice).order_by(PlanPrice.plan_name, PlanPrice.period_days)
        )
        all_plans = result.scalars().all()
        print(f"\nAll plans in DB ({len(all_plans)} total):")
        for p in all_plans:
            print(f"  {p.plan_name:10} {p.period_days:3} дн. — {float(p.price_rub):7.2f} ₽")

    await engine.dispose()
    print("\nDone! Restart backend to apply changes.")


if __name__ == "__main__":
    asyncio.run(main())
