"""Main bot entry point"""

import asyncio
import logging
from aiogram import Dispatcher, Bot

from bot.config import config
from bot.loader import setup_bot, close_bot
from bot.middlewares import AuthMiddleware, ThrottlingMiddleware

# Import all handlers
from bot.handlers import (
    start,
    free_trial,
    payment,
    subscription,
    referral,
    support,
    instructions,
    channel,
    cabinet,
    admin,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO if not config.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_handlers(dp: Dispatcher) -> None:
    """Register all handlers with dispatcher"""
    
    # Register routers in order of priority
    # Admin handlers should be first
    dp.include_router(admin.router)
    
    # Then main handlers
    dp.include_router(start.router)
    dp.include_router(free_trial.router)
    dp.include_router(referral.router)
    dp.include_router(support.router)
    dp.include_router(instructions.router)
    dp.include_router(channel.router)
    dp.include_router(cabinet.router)
    dp.include_router(payment.router)
    dp.include_router(subscription.router)


async def setup_middlewares(dp: Dispatcher) -> None:
    """Register all middlewares with dispatcher"""
    
    # Throttling middleware first (outermost)
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    
    # Auth middleware second
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())


async def main() -> None:
    """Main bot function"""
    
    logger.info("Starting VPN Sales Bot...")
    
    # Validate config
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Setup bot and dispatcher
    bot, dp = await setup_bot()
    
    try:
        # Setup handlers and middlewares
        await setup_handlers(dp)
        await setup_middlewares(dp)
        
        # Set bot commands — only /start is visible to all users
        # /admin works but is not listed in the menu
        await bot.set_my_commands([
            {"command": "start", "description": "Запустить бота"},
        ])
        
        logger.info("Bot started successfully")
        logger.info(f"Admin IDs: {config.telegram.admin_ids}")
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    finally:
        await close_bot(bot)
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
