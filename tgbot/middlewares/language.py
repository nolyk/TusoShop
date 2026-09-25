from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from tgbot.utils.utils import get_language
from tgbot.data.config import BotTexts

from typing import Any, Callable, Dict, Awaitable

class UserLanguageMiddleware(BaseMiddleware):
    def __init__(self, admin_panel: bool = False):
        self.admin_panel = admin_panel

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user = data["event_from_user"]
        data["BotTexts"] = BotTexts.Ru if self.admin_panel else await get_language(user.id)
        return await handler(event, data)
