"""Script to initialize bot buttons in DB.
Buttons are stored as individual btn_* keys in BotText table (JSON per button).
"""
import asyncio
import json
import os
import sys
from uuid import uuid4

# Ensure we run from project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from backend.config import settings
from backend.database import Base, get_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

DEFAULT_BUTTONS = [
    {"text": "🎁 Бесплатный доступ",  "callback_data": "free_trial",       "url": "", "row": 0},
    {"text": "💸 Оплатить тариф",      "callback_data": "buy_subscription",  "url": "", "row": 1},
    {"text": "👤 Личный кабинет",      "callback_data": "cabinet",           "url": "", "row": 2},
    {"text": "🎁 Получить бесплатно",  "callback_data": "get_free",          "url": "", "row": 2},
    {"text": "🔗 Реферальная система", "callback_data": "partner",           "url": "", "row": 3},
    {"text": "⚙️ Инструкция",          "callback_data": "instructions",      "url": "", "row": 3},
    {"text": "👨‍💻 Поддержка",            "callback_data": "support",           "url": "", "row": 4},
    {"text": "📢 Наш канал",            "callback_data": "channel",           "url": "", "row": 4},
]


async def main():
    print(f"DB URL: {settings.DATABASE_URL}")
    engine = get_engine()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created/verified OK")

    async with AsyncSession(engine) as session:
        # Show existing tables
        result = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [r[0] for r in result.fetchall()]
        print(f"Tables in DB: {tables}")

        # Delete all existing btn_* keys using raw SQL
        await session.execute(text("DELETE FROM bot_texts WHERE key LIKE 'btn_%'"))
        await session.commit()
        print("Deleted old btn_* keys")

        # Insert new default buttons using raw SQL
        for btn in DEFAULT_BUTTONS:
            key = f"btn_{uuid4().hex[:8]}"
            value = json.dumps({
                "text": btn["text"],
                "callback_data": btn["callback_data"],
                "url": btn["url"],
                "row": btn["row"],
            }, ensure_ascii=False)
            await session.execute(text(
                "INSERT INTO bot_texts (id, key, value, description) "
                "VALUES (:id, :key, :value, :desc)"
            ), {"id": str(uuid4()), "key": key, "value": value, "desc": "menu_button"})

        await session.commit()
        print(f"Inserted {len(DEFAULT_BUTTONS)} new buttons")

        # Verify
        result2 = await session.execute(text(
            "SELECT key, value FROM bot_texts WHERE key LIKE 'btn_%' ORDER BY key"
        ))
        saved = result2.fetchall()
        print(f"\nButtons in DB ({len(saved)} total):")
        for s in saved:
            b = json.loads(s[1])
            print(f"  [{s[0]}] row={b['row']} | {b['text']} -> {b['callback_data']}")

    await engine.dispose()
    print("\nAll done! Now restart the bot service in AlwaysData panel.")


if __name__ == "__main__":
    asyncio.run(main())
