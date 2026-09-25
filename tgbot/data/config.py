import hashlib
import os
from pathlib import Path

from tgbot.data.texts.ru import Language as RU
from tgbot.data.texts.en import Language as EN
from tgbot.data.texts.ua import Language as UA
from tgbot.data.texts.hy import Language as HY

from tgbot.keyboards import users, admins


def _load_local_env():
    root = Path(__file__).resolve().parents[2]
    for env_path in (root / ".env", root / ".env.webapp"):
        if not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)


def _required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


_load_local_env()


class BotConfig:
    BOT_TOKEN = _required_env("BOT_TOKEN")
    ADMINS = [int(value) for value in os.environ.get("BOT_ADMINS", "").split(",") if value.strip().isdigit()]
    CHANNELS_FOR_SUBSCRIBE = [int(value) for value in os.environ.get("BOT_CHANNELS", "").split(",") if value.strip().lstrip("-").isdigit()]
    LOGS_CHANNEL = int(os.environ.get("BOT_LOGS_CHANNEL", "0"))
    BOT_VERSION = "3.0"
    CURRENCIES = {
        "rub": {
            'txt': 'rub',
            "text": 'RUB',
            'sign': '₽'
        },
        "eur": {
            'txt': 'eur',
            "text": "EUR",
            'sign': "€"
        },
        "usd": {
            'txt': 'usd',
            'text': "USD",
            "sign": "$"
        },
        "amd": {
            'txt': 'amd',
            "text": "AMD",
            "sign": "֏"
        }
    }
    LANGUAGES = [
        {
            "language": "ru",
            "name": "Русский",
        },
        {
            "language": "en",
            "name": "English",
        },
        {
            "language": "ua",
            "name": "Український",
        },
    ]
    ######
    ######
    ######
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
    DATABASE_HOST = os.environ.get("DATABASE_HOST", "localhost")
    DATABASE_PORT = int(os.environ.get("DATABASE_PORT", "5432"))
    DATABASE_USERNAME = os.environ.get("DATABASE_USERNAME", "nolyk")
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "autoshop")
    WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip().rstrip("/") or (
        "https://" + os.environ["RAILWAY_PUBLIC_DOMAIN"].strip().rstrip("/")
        if os.environ.get("RAILWAY_PUBLIC_DOMAIN") else ""
    )
    WEBAPP_HOST = "0.0.0.0" if os.environ.get("RAILWAY_ENVIRONMENT_ID") else (
        os.environ.get("WEBAPP_HOST", "0.0.0.0").strip() or "0.0.0.0"
    )
    WEBAPP_PORT = int(os.environ.get("PORT") or os.environ.get("WEBAPP_PORT", "8080"))
    WEBAPP_ALLOWED_ORIGINS = tuple(
        value.strip() for value in os.environ.get("WEBAPP_ALLOWED_ORIGINS", "").split(",") if value.strip()
    )
    DIGITAL_SHOP_ENABLED = os.environ.get("DIGITAL_SHOP_ENABLED", "true").lower() == "true"
    DIGITAL_STARS_ENABLED = os.environ.get("DIGITAL_STARS_ENABLED", "true").lower() == "true"
    DIGITAL_PREMIUM_ENABLED = os.environ.get("DIGITAL_PREMIUM_ENABLED", "true").lower() == "true"
    DIGITAL_GIFTS_ENABLED = os.environ.get("DIGITAL_GIFTS_ENABLED", "false").lower() == "true"
    MARKETAPP_API_URL = os.environ.get("MARKETAPP_API_URL", "https://api.marketapp.ws").rstrip("/")
    MARKETAPP_API_TOKEN = os.environ.get("MARKETAPP_API_TOKEN", "").strip()
    TONAPI_KEY = os.environ.get("TONAPI_KEY", "").strip()
    MARKETAPP_TIMEOUT = float(os.environ.get("MARKETAPP_TIMEOUT", "15"))
    JWT_SECRET = os.environ.get("JWT_SECRET", "").strip() or hashlib.sha256(
        f"autoshop-miniapp:{BOT_TOKEN}".encode("utf-8")
    ).hexdigest()


class BotTexts:
    class Hy:
        ADMIN_TEXTS = RU.AdminTexts()
        TEXTS = HY.Texts()
        BUTTONS = HY.Buttons()

    class Ru:
        ADMIN_TEXTS = RU.AdminTexts()
        TEXTS = RU.Texts()
        BUTTONS = RU.Buttons()
    
    
    class En:
        ADMIN_TEXTS = EN.AdminTexts()
        TEXTS = EN.Texts()
        BUTTONS = EN.Buttons()
        
        
    class Ua:
        ADMIN_TEXTS = UA.AdminTexts()
        TEXTS = UA.Texts()
        BUTTONS = UA.Buttons()


class BotButtons:
    USERS_REPLY = users.ReplyButtons()
    USERS_INLINE = users.InlineButtons()
    ADMIN_INLINE = admins.InlineButtons()


class BotImages:
    START_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    PROFILE_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    TOPUP_BALANCE_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    SUPPORT_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    BUY_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    FAQ_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"
    CONTEST_PHOTO = "https://i.postimg.cc/50PX4QbK/image.png"


def main_db():
    from tgbot.utils.db import DataBase
    return DataBase()

DB = main_db()
