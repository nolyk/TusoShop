"""Dependency-free checks for menu navigation and banner security."""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path


class TelegramBadRequest(Exception):
    pass


class InlineKeyboardMarkup:
    pass


class InputMediaPhoto:
    def __init__(self, media, caption):
        self.media = media
        self.caption = caption


class FakeImages:
    START_PHOTO = "https://example.com/main.jpg"
    PROFILE_PHOTO = TOPUP_BALANCE_PHOTO = SUPPORT_PHOTO = BUY_PHOTO = START_PHOTO
    FAQ_PHOTO = CONTEST_PHOTO = START_PHOTO


class FakeDB:
    def __init__(self):
        self.items = {}

    async def get_menu_banner(self, key):
        value = self.items.get(key)
        return types.SimpleNamespace(photo_url=value) if value else None


def load_menu_module():
    aiogram = types.ModuleType("aiogram")
    exceptions = types.ModuleType("aiogram.exceptions")
    exceptions.TelegramBadRequest = TelegramBadRequest
    aiogram_types = types.ModuleType("aiogram.types")
    aiogram_types.InlineKeyboardMarkup = InlineKeyboardMarkup
    aiogram_types.InputMediaPhoto = InputMediaPhoto
    config = types.ModuleType("tgbot.data.config")
    config.BotImages = FakeImages
    config.DB = FakeDB()
    sys.modules.update({
        "aiogram": aiogram,
        "aiogram.exceptions": exceptions,
        "aiogram.types": aiogram_types,
        "tgbot.data.config": config,
    })
    path = Path(__file__).parents[1] / "tgbot" / "utils" / "menu.py"
    spec = importlib.util.spec_from_file_location("menu_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMessage:
    def __init__(self, photo=True):
        self.photo = [object()] if photo else []
        self.deleted = False
        self.edited_media = None

    async def edit_media(self, media, reply_markup):
        self.edited_media = (media, reply_markup)
        return self

    async def edit_caption(self, caption, reply_markup):
        return self

    async def edit_text(self, text, reply_markup):
        return self

    async def delete(self):
        self.deleted = True


class FakeCall:
    def __init__(self, message):
        self.message = message

    async def answer(self):
        pass


def main():
    menu = load_menu_module()
    assert menu.validate_menu_key("buy") == "buy"
    assert menu.validate_menu_key("category:12") == "category:12"
    for bad in ("buy-anything", "category:-1", "unknown", "position:x"):
        try:
            menu.validate_menu_key(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe menu key accepted: {bad}")
    assert menu.validate_banner_url("https://cdn.example.com/banner.jpg")
    for bad in ("http://example.com/a.jpg", "https://localhost/a.jpg", "https://127.0.0.1/a.jpg", "file:///tmp/a"):
        try:
            menu.validate_banner_url(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe URL accepted: {bad}")

    menu.DB.items["all"] = "https://cdn.example.com/all.jpg"
    assert asyncio.run(menu.get_banner("buy")) == "https://cdn.example.com/all.jpg"
    menu.DB.items["buy"] = "telegram-file-id"
    assert asyncio.run(menu.get_banner("buy")) == "telegram-file-id"

    message = FakeMessage(photo=True)
    call = FakeCall(message)
    asyncio.run(menu.edit_menu(call, "next", InlineKeyboardMarkup(), "buy"))
    assert message.edited_media is not None
    assert message.deleted is False, "photo-to-photo navigation must preserve message id"

    handlers = Path(__file__).parents[1] / "tgbot" / "handlers" / "users"
    sources = "\n".join(p.read_text(encoding="utf-8") for p in handlers.glob("*.py"))
    assert "USERS_INLINE.close" not in sources
    keyboards = "\n".join(
        (Path(__file__).parents[1] / "tgbot" / "keyboards" / name).read_text(encoding="utf-8")
        for name in ("users.py", "admins.py")
    )
    assert "icon_custom_emoji_id=" not in keyboards
    assert '"menu_banner:all"' in keyboards
    assert "telyx==0.0.1" in (Path(__file__).parents[1] / "requirements.txt").read_text(encoding="utf-8")
    print("MENU_TEST PASS url_validation=PASS global_banner=PASS photo_file_id=PASS in_place_media=PASS telyx_buttons=PASS")


if __name__ == "__main__":
    main()
