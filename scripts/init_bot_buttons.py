"""Script to initialize bot_buttons and bot_texts tables with default data."""
import asyncio
import os
import sys

# Ensure we run from project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from backend.config import settings
from backend.database import Base, get_engine
from backend.models.config import BotButton, BotText
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

DEFAULT_BUTTONS = [
    {"text": "🎁 Бесплатный доступ", "callback_data": "free_trial", "url": "", "row": 0},
    {"text": "💸 Оплатить тариф",     "callback_data": "buy_subscription", "url": "", "row": 1},
    {"text": "👤 Личный кабинет",     "callback_data": "cabinet", "url": "", "row": 2},
    {"text": "🎁 Получить бесплатно", "callback_data": "get_free", "url": "", "row": 2},
    {"text": "🔗 Реферальная система","callback_data": "partner", "url": "", "row": 3},
    {"text": "⚙️ Инструкция",         "callback_data": "instructions", "url": "", "row": 3},
    {"text": "👨‍💻 Поддержка",           "callback_data": "support", "url": "", "row": 4},
    {"text": "📢 Наш канал",           "callback_data": "channel", "url": "", "row": 4},
]


async def main():
    print(f"DB URL: {settings.DATABASE_URL}")
    engine = get_engine()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created/verified OK")

    async with AsyncSession(engine) as session:
        # Clear old buttons and insert defaults
        await session.execute(text("DELETE FROM bot_buttons"))
        for btn in DEFAULT_BUTTONS:
            await session.execute(text(
                "INSERT INTO bot_buttons (text, callback_data, url, row, is_active) "
                "VALUES (:text, :callback_data, :url, :row, true)"
            ), btn)
        await session.commit()

        # Verify
        result = await session.execute(text("SELECT text, callback_data, row FROM bot_buttons ORDER BY row"))
        rows = result.fetchall()
        print("\nButtons in DB:")
        for r in rows:
            print(f"  row={r[2]} | {r[0]} -> {r[1]}")

        # Check bot_texts
        result2 = await session.execute(text("SELECT key FROM bot_texts LIMIT 20"))
        texts = result2.fetchall()
        print(f"\nBot texts count: {len(texts)}")
        for t in texts:
            print(f"  {t[0]}")

    await engine.dispose()
    print("\nAll done! Restart the bot service in AlwaysData panel.")


if __name__ == "__main__":
    asyncio.run(main())
