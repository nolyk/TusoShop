"""Preserve Telegram entities without putting HTML in plain catalog names."""
import html
import re
from html.parser import HTMLParser
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

CUSTOM = re.compile(r'<tg-emoji\s+emoji-id=[\"\'](\d+)[\"\']>(.*?)</tg-emoji>', re.S)


def name_fields(message):
    return {'name': message.text, 'name_html': message.html_text}


def catalog_button_name(item):
    value = getattr(item, 'name_html', None)
    return value if value and CUSTOM.search(value) else item.name


def catalog_name(item):
    return getattr(item, 'name_html', None) or item.name


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(value)
    return ''.join(parser.parts)


def unwrap_emoji_code(value):
    return re.sub(r'<(code|pre)\b[^>]*>(.*?)</\1>',
                  lambda m: m.group(2) if CUSTOM.search(m.group(2)) else m.group(0), value, flags=re.S)


class CatalogEmojiMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        for field in ('text', 'caption'):
            value = getattr(method, field, None)
            if isinstance(value, str) and CUSTOM.search(value):
                setattr(method, field, unwrap_emoji_code(value))
        media = getattr(method, 'media', None)
        if media is not None:
            def update(item):
                caption = getattr(item, 'caption', None)
                return item.model_copy(update={'caption': unwrap_emoji_code(caption)}) if caption and CUSTOM.search(caption) else item
            if isinstance(media, list):
                method.media = [update(item) for item in media]
            elif hasattr(media, 'caption'):
                method.media = update(media)
        markup = getattr(method, 'reply_markup', None)
        rows = getattr(markup, 'inline_keyboard', None)
        if rows is None:
            rows = getattr(markup, 'keyboard', ())
        for row in rows:
            for button in row:
                match = CUSTOM.search(button.text)
                if match:
                    original = plain_text(button.text)
                    label = plain_text(button.text[:match.start()] + button.text[match.end():]).strip()
                    button.text = label or original
                    button.icon_custom_emoji_id = match.group(1)
        return await make_request(bot, method)
