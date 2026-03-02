"""Bot loader and initialization module"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Initialize bot and dispatcher with all configurations"""

    # Setup proxy session if PROXY_URL is set
    session = None
    if config.proxy_url:
        session = AiohttpSession(proxy=config.proxy_url)

    # Setup bot with default parsing mode
    bot = Bot(
        token=config.telegram.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    # Use MemoryStorage for FSM (no Redis required)
    storage = MemoryStorage()

    # Create dispatcher
    dp = Dispatcher(storage=storage)

    return bot, dp


async def close_bot(bot: Bot) -> None:
    """Close bot session"""
    await bot.session.close()
