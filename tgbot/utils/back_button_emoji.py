"""Style all outgoing back buttons without changing their destinations."""
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from tgbot.utils.premium_emoji import normalize_button_text

BACK_EMOJI_ID = "6181715848965661096"

class BackButtonEmojiMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        markup = getattr(method, 'reply_markup', None)
        rows = getattr(markup, 'inline_keyboard', None)
        if rows is None:
            rows = getattr(markup, 'keyboard', ())
        for row in rows:
            for button in row:
                label = normalize_button_text(button.text).strip(' ◀◀️←⬅⬅️«‹').casefold()
                callback = getattr(button, 'callback_data', None) or ''
                if label in {'հետ', 'назад', 'back', 'повернутися'} or callback.startswith(('back_', 'back:')):
                    button.icon_custom_emoji_id = BACK_EMOJI_ID
        return await make_request(bot, method)
