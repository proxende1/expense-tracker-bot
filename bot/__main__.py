import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import load_config
from bot.db import Database
from bot.handlers import router

COMMANDS = [
    BotCommand(command="today", description="Расходы за сегодня"),
    BotCommand(command="month", description="Статистика за месяц"),
    BotCommand(command="history", description="Последние траты"),
    BotCommand(command="budget", description="Бюджет на месяц"),
    BotCommand(command="undo", description="Удалить последнюю трату"),
    BotCommand(command="export", description="Выгрузить в CSV"),
    BotCommand(command="help", description="Помощь"),
]


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    config = load_config()
    db = Database(config.db_path)
    await db.connect()

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    try:
        await bot.set_my_commands(COMMANDS)
        await dp.start_polling(bot, db=db, config=config)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
