"""Persistent visibility for Mini App entry points, not an access-control switch."""
import asyncio
from urllib.parse import urlsplit
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo

menu_lock = asyncio.Lock()


def menu_enabled(settings):
    return bool(getattr(settings, 'mini_app_menu_enabled', True))


def valid_url(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password


async def sync_mini_app_menu(bot, settings, url):
    button = (MenuButtonWebApp(text='Mini App', web_app=WebAppInfo(url=url))
              if menu_enabled(settings) and valid_url(url) else MenuButtonCommands())
    await bot.set_chat_menu_button(menu_button=button)


async def toggle_mini_app_menu(db, bot, url):
    async with menu_lock:
        settings = await db.get_settings()
        previous = menu_enabled(settings)
        enabled = not previous
        if enabled and not valid_url(url):
            raise ValueError('Сначала настройте HTTPS-адрес WEBAPP_URL.')
        await db.update_settings(mini_app_menu_enabled=enabled)
        try:
            settings.mini_app_menu_enabled = enabled
            await sync_mini_app_menu(bot, settings, url)
        except Exception:
            await db.update_settings(mini_app_menu_enabled=previous)
            raise
        return enabled
