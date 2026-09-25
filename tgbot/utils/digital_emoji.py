"""Custom Telegram emoji retained from the original StarShop UI."""

from aiogram.types import InlineKeyboardButton


STARS_BUY_EMOJI_ID = "5199535185753831040"
PREMIUM_BUY_EMOJI_ID = "5362006552951690043"
GIFTS_MENU_EMOJI_ID = "5203996991054432397"
CRYPTOBOT_EMOJI_ID = "5427054176246991778"
XROCKET_EMOJI_ID = "5415897719522744378"
PAYMENTS_EMOJI_ID = "5445353829304387411"

STARS_EMOJI = f'<tg-emoji emoji-id="{STARS_BUY_EMOJI_ID}">⭐</tg-emoji>'
PREMIUM_EMOJI = f'<tg-emoji emoji-id="{PREMIUM_BUY_EMOJI_ID}">🌟</tg-emoji>'
GIFTS_EMOJI = f'<tg-emoji emoji-id="{GIFTS_MENU_EMOJI_ID}">🎁</tg-emoji>'


def emoji_button(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    web_app=None,
    emoji_id: str | None = None,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        url=url,
        web_app=web_app,
        icon_custom_emoji_id=emoji_id,
    )
