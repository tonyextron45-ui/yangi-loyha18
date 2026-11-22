import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers import admin, broadcast, channels, movies, user


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("kino_bot.log", encoding="utf-8"),
        ],
    )
    logger = logging.getLogger(__name__)

    config = load_config()
    db = Database(db_path=config.db_path, initial_admins=config.admin_ids)
    await db.init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp["db"] = db

    dp.include_router(admin.router)
    dp.include_router(movies.router)
    dp.include_router(channels.router)
    dp.include_router(broadcast.router)
    dp.include_router(user.router)

    logger.info("Kino Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Kino Bot to‘xtatildi.")
