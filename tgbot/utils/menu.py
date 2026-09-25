"""Safe, in-place rendering for Telegram inline menus."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto

from tgbot.data.config import BotImages, DB


DEFAULT_BANNERS = {
    "main": BotImages.START_PHOTO,
    "profile": BotImages.PROFILE_PHOTO,
    "refill": BotImages.TOPUP_BALANCE_PHOTO,
    "support": BotImages.SUPPORT_PHOTO,
    "buy": BotImages.BUY_PHOTO,
    "faq": BotImages.FAQ_PHOTO,
    "contests": BotImages.CONTEST_PHOTO,
    "admin": BotImages.START_PHOTO,
}

STATIC_MENU_KEYS = {"main", "profile", "refill", "support", "buy", "faq", "contests", "admin"}
DYNAMIC_MENU_PREFIXES = ("category:", "subcategory:", "position:", "admin:")


def validate_menu_key(value: str) -> str:
    key = (value or "").strip().lower()
    if not key or len(key) > 64:
        raise ValueError("unsupported menu key")
    if key in STATIC_MENU_KEYS:
        return key
    if not key.startswith(DYNAMIC_MENU_PREFIXES):
        raise ValueError("unsupported menu key")
    if ":" in key:
        prefix, item_id = key.split(":", 1)
        if prefix not in {"category", "subcategory", "position", "admin"}:
            raise ValueError("unsupported dynamic menu")
        if prefix != "admin" and (not item_id.isdigit() or int(item_id) < 1):
            raise ValueError("invalid menu id")
        if prefix == "admin" and (not item_id or not item_id.replace("_", "").isalnum()):
            raise ValueError("invalid admin menu")
    return key


def validate_banner_url(value: str) -> str:
    """Allow only public HTTPS URLs; Telegram fetches the image server-side."""
    url = (value or "").strip()
    if len(url) > 2048:
        raise ValueError("URL is too long")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("only HTTPS URLs without credentials are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("local hosts are forbidden")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("private and special IP addresses are forbidden")
    return url


async def get_banner(menu_key: str, fallback: str | None = None) -> str | None:
    banner = await DB.get_menu_banner(menu_key)
    if banner:
        return banner.photo_url
    global_banner = await DB.get_menu_banner("all")
    if global_banner:
        return global_banner.photo_url
    if fallback is not None:
        return fallback
    if menu_key.startswith(("category:", "subcategory:")):
        return DEFAULT_BANNERS.get("buy")
    if menu_key.startswith("admin:"):
        return DEFAULT_BANNERS.get("admin")
    return DEFAULT_BANNERS.get(menu_key)


async def send_menu(message, text: str, reply_markup, menu_key: str, fallback: str | None = None):
    banner = await get_banner(menu_key, fallback)
    if banner and len(text) <= 1024:
        return await message.answer_photo(photo=banner, caption=text, reply_markup=reply_markup)
    return await message.answer(text, reply_markup=reply_markup)


async def edit_menu(call, text: str, reply_markup, menu_key: str, fallback: str | None = None):
    """Edit the same Telegram message whenever the media type permits it."""
    banner = await get_banner(menu_key, fallback)
    message = call.message
    if reply_markup is not None and not isinstance(reply_markup, InlineKeyboardMarkup):
        await message.delete()
        return await send_menu(message, text, reply_markup, menu_key, fallback)
    try:
        if message.photo and banner and len(text) <= 1024:
            return await message.edit_media(
                InputMediaPhoto(media=banner, caption=text), reply_markup=reply_markup
            )
        if message.photo and len(text) <= 1024:
            return await message.edit_caption(caption=text, reply_markup=reply_markup)
        if not message.photo and not banner:
            return await message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await call.answer()
            return message
        raise

    # Telegram cannot convert a text message to a photo (or remove media) in place.
    # This is the only transition where a replacement message is unavoidable.
    await message.delete()
    return await send_menu(message, text, reply_markup, menu_key, fallback)


async def safe_edit_text(message, text: str, reply_markup=None):
    """Edit caption for media menus and text for plain menus."""
    try:
        if message.photo and len(text) <= 1024:
            return await message.edit_caption(caption=text, reply_markup=reply_markup)
        if message.photo:
            await message.delete()
            return await message.answer(text, reply_markup=reply_markup)
        return await message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return message
        raise
