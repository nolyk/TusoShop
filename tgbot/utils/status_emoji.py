"""Apply requested status icons at the Telegram delivery boundary."""
import re
from aiogram.client.default import Default
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.types import MessageEntity
from tgbot.utils.premium_emoji import STATUS_IDS, BUTTON_STATUS_IDS, strip_tg_emoji

SYMBOL = re.compile(r'[✅✔☑✓❌✖✗✘❎📢]\ufe0f?')
TOKEN = re.compile(r'<tg-emoji\b[^>]*>.*?</tg-emoji>|<code\b[^>]*>.*?</code>|<pre\b[^>]*>.*?</pre>|<[^>]+>', re.S)


def html_status(text):
    def replace(match):
        symbol = match.group(0)
        return f'<tg-emoji emoji-id="{STATUS_IDS[symbol[0]]}">{symbol}</tg-emoji>'
    result = []; start = 0
    for token in TOKEN.finditer(text):
        result.append(SYMBOL.sub(replace, text[start:token.start()]))
        value = token.group(0)
        if value.startswith('<tg-emoji'):
            fallback = strip_tg_emoji(value)
            if SYMBOL.fullmatch(fallback):
                value = SYMBOL.sub(replace, fallback)
        result.append(value); start = token.end()
    result.append(SYMBOL.sub(replace, text[start:]))
    return ''.join(result)


def style_content(obj, bot):
    updates = {}
    for field, entity_field in (('text', 'entities'), ('caption', 'caption_entities')):
        text = getattr(obj, field, None)
        if not isinstance(text, str) or not hasattr(obj, entity_field):
            continue
        entities = getattr(obj, entity_field, None)
        mode = getattr(obj, 'parse_mode', None)
        if isinstance(mode, Default):
            mode = bot.default.parse_mode
        if not entities and mode == 'HTML':
            updates[field] = html_status(text)
        elif entities or mode is None:
            styled = [entity.model_copy() for entity in (entities or [])]
            for match in SYMBOL.finditer(text):
                offset = len(text[:match.start()].encode('utf-16-le')) // 2
                length = len(match.group().encode('utf-16-le')) // 2
                overlaps = [e for e in styled if e.offset < offset + length and offset < e.offset + e.length]
                if any(e.type in {'code', 'pre'} for e in overlaps):
                    continue
                custom = next((e for e in overlaps if e.type == 'custom_emoji'), None)
                if custom:
                    if custom.offset == offset and custom.length == length:
                        styled[styled.index(custom)] = custom.model_copy(update={'custom_emoji_id': STATUS_IDS[match.group()[0]]})
                else:
                    styled.append(MessageEntity(type='custom_emoji', offset=offset, length=length,
                                               custom_emoji_id=STATUS_IDS[match.group()[0]]))
            if styled:
                updates[entity_field] = sorted(styled, key=lambda e: (e.offset, -e.length))
                updates['parse_mode'] = None
    return obj.model_copy(update=updates)


class StatusEmojiMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        styled = style_content(method, bot)
        for field in ('text', 'caption', 'entities', 'caption_entities', 'parse_mode'):
            if field in styled.model_fields_set:
                setattr(method, field, getattr(styled, field))
        media = getattr(method, 'media', None)
        if isinstance(media, list):
            method.media = [style_content(item, bot) for item in media]
        elif media is not None and hasattr(media, 'caption'):
            method.media = style_content(media, bot)
        markup = getattr(method, 'reply_markup', None)
        inline = getattr(markup, 'inline_keyboard', None)
        rows = inline if inline is not None else getattr(markup, 'keyboard', ())
        for row in rows:
            for button in row:
                label = strip_tg_emoji(button.text)
                match = SYMBOL.search(label)
                emoji_id = STATUS_IDS[match.group()[0]] if match else BUTTON_STATUS_IDS.get(label)
                old_icon = getattr(button, 'icon_custom_emoji_id', None)
                emoji_id = emoji_id or {'5211226456100738227': STATUS_IDS['✅'], '5213056077809099062': STATUS_IDS['✅'], '5213168202225325288': STATUS_IDS['📢']}.get(old_icon)
                callback = getattr(button, 'callback_data', '') or ''
                if callback in {'ad_buttons', 'ad_buttons:create'}:
                    emoji_id = STATUS_IDS['📢']
                if emoji_id:
                    button.icon_custom_emoji_id = emoji_id
                    if inline is not None and match:
                        button.text = SYMBOL.sub('', label).strip() or ('Այո' if emoji_id == STATUS_IDS['✅'] else 'Ոչ')
        return await make_request(bot, method)
