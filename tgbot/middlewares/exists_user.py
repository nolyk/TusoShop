from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from tgbot.data.config import DB, BotButtons
from tgbot.utils.utils import send_admins, get_language

from traceback import print_exc
from loguru import logger
from typing import Any, Callable, Dict, Awaitable


class ExistsUserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        update: Update = data['event_update']
        user = data["event_from_user"]
        if update.message:
            logger.info("Incoming message user_id={} message_id={}", user.id if user else None, update.message.message_id)
        else:
            logger.info(f"{user.full_name} - {update.callback_query.data} (Callback)")
        try:
            if user is not None and not user.is_bot:
                settings = await DB.get_settings()

                db_user = await DB.get_user(user_id=user.id)

                # Եթե օգտատերը նոր է՝ գրանցել և պահել նույն հայերեն ցուցափեղկը։
                if db_user is None:
                    await DB.register_user(user.id, user.username, user.full_name)
                    BotTexts = await get_language(user.id)
                    if settings.is_notify:
                        await send_admins("new_user_alert", name=user.mention_html(), user_id=user.id)
                else:
                    # Кешируем объект user
                    self.user = db_user
                    BotTexts = await get_language(user.id)
                    # Проверяем бан
                    if self.user.is_ban:
                        return await event.answer(BotTexts.TEXTS.is_ban_text)

                    # Обновляем только если что-то поменялось
                    updates = {}
                    if self.user.user_name != user.full_name:
                        updates['full_name'] = user.full_name
                    # Проверяем username отдельно
                    new_username = user.username or ""
                    if new_username != self.user.user_name:
                        updates['user_name'] = new_username

                    # Если что-то поменялось — делаем update
                    if updates:
                        await DB.update_user(user.id, **updates)

        except Exception:
            print_exc()
        
        return await handler(event, data)

