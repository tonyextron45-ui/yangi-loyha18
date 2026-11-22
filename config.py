import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    db_path: str = "kino_bot.db"


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "9073444204:AAFbX5ChFDdyijdldHzWlIyLdgXhZSBHlMw").strip()
    if not token:
        raise ValueError("BOT_TOKEN muhit o'zgaruvchisida ko'rsatilmagan!")

    raw_admins = os.getenv("ADMIN_IDS", "8671990338")
    admin_ids: list[int] = []
    for part in raw_admins.split(","):
        part = part.strip()
        if part.isdigit():
            admin_ids.append(int(part))

    if not admin_ids:
        raise ValueError("ADMIN_IDS muhit o'zgaruvchisida kamida bitta raqamli ID bo'lishi shart!")

    db_path = os.getenv("DB_PATH", "kino_bot.db").strip() or "kino_bot.db"
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    return Config(bot_token=token, admin_ids=admin_ids, db_path=db_path)
