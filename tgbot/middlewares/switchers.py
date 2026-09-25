from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from tgbot.data.config import DB, BotConfig, BotButtons
from tgbot.utils.utils import get_language

from typing import Any, Callable, Dict, Awaitable


def _is_joined_channel(member) -> bool:
    status = getattr(member.status, "value", member.status)
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return status not in {"left", "kicked"}


class SwitchersMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        user = data["event_from_user"]
        update: Update = data['event_update']
        settings = await DB.get_settings()
        BotTexts = await get_language(user.id)
        
        if settings.is_work and user.id not in BotConfig.ADMINS:
            return await event.answer(BotTexts.TEXTS.is_work_text)
        
        if settings.is_sub and user.id not in BotConfig.ADMINS:
            count = 0
            urls_txt = ''

            channels = await DB.get_mandatory_channels(enabled_only=True)
            if not channels:
                return await handler(event, data)

            for channel in channels:
                try:
                    user_status = await event.bot.get_chat_member(chat_id=channel.channel_id, user_id=user.id)
                    subscribed = _is_joined_channel(user_status)
                except Exception:
                    subscribed = False
                if not subscribed:
                    urls_txt += f"<a href='{channel.invite_link}'>{channel.title}</a> — Բաժանորդագրված չեք\n"
                else:
                    count += 1
                    urls_txt += f"<a href='{channel.invite_link}'>{channel.title}</a> — Բաժանորդագրված եք\n"

            if count != len(channels):
                if update.message:
                    return await update.message.answer(BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt), 
                                                reply_markup=BotButtons.USERS_INLINE.mandatory_sub_kb(BotTexts, channels).as_markup())
                if update.callback_query and update.callback_query.message:
                    return await update.callback_query.message.answer(BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt), 
                                                reply_markup=BotButtons.USERS_INLINE.mandatory_sub_kb(BotTexts, channels).as_markup())
                return await event.answer(BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt))
                

        
        return await handler(event, data)
