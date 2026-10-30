import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str
    currency: str
    timezone: ZoneInfo


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и впишите токен от @BotFather."
        )
    return Config(
        bot_token=token,
        db_path=os.getenv("DB_PATH", "data/expenses.db"),
        currency=os.getenv("CURRENCY", "₽"),
        timezone=ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow")),
    )
