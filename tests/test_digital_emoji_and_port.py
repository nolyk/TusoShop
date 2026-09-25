from pathlib import Path

from tgbot.data.config import BotConfig
from tgbot.utils.digital_emoji import (
    PREMIUM_BUY_EMOJI_ID,
    PREMIUM_EMOJI,
    STARS_BUY_EMOJI_ID,
    STARS_EMOJI,
    emoji_button,
)


def test_starshop_custom_emoji_ids_are_retained():
    stars = emoji_button("Stars", callback_data="digital:stars", emoji_id=STARS_BUY_EMOJI_ID)
    premium = emoji_button("Premium", callback_data="digital:premium", emoji_id=PREMIUM_BUY_EMOJI_ID)
    assert stars.icon_custom_emoji_id == "5199535185753831040"
    assert premium.icon_custom_emoji_id == "5362006552951690043"
    assert STARS_BUY_EMOJI_ID in STARS_EMOJI
    assert PREMIUM_BUY_EMOJI_ID in PREMIUM_EMOJI


def test_ngrok_upstream_port_matches_webapp_launcher():
    launcher = Path("start_webapp.bat").read_text(encoding="utf-8")
    ngrok = Path("start_ngrok.bat").read_text(encoding="utf-8")
    assert BotConfig.WEBAPP_PORT == 8080
    assert BotConfig.WEBAPP_HOST == "0.0.0.0"
    assert "web_main.py" in launcher
    assert "127.0.0.1:8080" in ngrok


def test_miniapp_starshop_assets_exist():
    static = Path("tgbot/webapp/static")
    assert (static / "stars-logo.webp").stat().st_size > 0
    assert (static / "premium-logo.webp").stat().st_size > 0
