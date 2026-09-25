"""Lossless Telegram item content without HTML markup."""

import base64
import json
from html.parser import HTMLParser

from aiogram.types import MessageEntity


PREFIX = "item:v1:"
PURCHASE_PREFIX = "purchase:v1:"


def encode_item(kind, text="", entities=None, file_id=None):
    payload = {"kind": kind, "text": text or "", "entities": [
        entity.model_dump(exclude_none=True) if hasattr(entity, "model_dump") else entity
        for entity in (entities or [])
    ], "file_id": file_id}
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return PREFIX + base64.urlsafe_b64encode(raw).decode("ascii")


def decode_item(value):
    if not value or not value.startswith(PREFIX):
        return None
    return json.loads(base64.urlsafe_b64decode(value[len(PREFIX):]).decode("utf-8"))


def encode_purchase(items):
    raw = json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return PURCHASE_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii")


def decode_purchase(value):
    if not value or not value.startswith(PURCHASE_PREFIX):
        return None
    return json.loads(base64.urlsafe_b64decode(value[len(PURCHASE_PREFIX):]).decode("utf-8"))


class _LegacyHTML(HTMLParser):
    """Convert old aiogram html_text captions to Telegram entities."""

    TAGS = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic",
            "u": "underline", "s": "strikethrough", "strike": "strikethrough",
            "code": "code", "pre": "pre", "a": "text_link", "tg-emoji": "custom_emoji",
            "tg-spoiler": "spoiler", "blockquote": "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.offset = 0
        self.open = []
        self.entities = []

    def handle_data(self, data):
        self.parts.append(data)
        self.offset += len(data.encode("utf-16-le")) // 2

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            return
        attrs = dict(attrs)
        entity = {"type": self.TAGS[tag], "offset": self.offset}
        if tag == "a":
            entity["url"] = attrs.get("href", "")
        if tag == "tg-emoji":
            entity["custom_emoji_id"] = attrs.get("emoji-id", "")
        self.open.append((tag, entity))

    def handle_endtag(self, tag):
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index][0] == tag:
                _, entity = self.open.pop(index)
                entity["length"] = self.offset - entity["offset"]
                if entity["length"]:
                    self.entities.append(entity)
                break


def legacy_media_item(kind, text, file_id):
    parser = _LegacyHTML()
    parser.feed(text or "")
    parser.close()
    return encode_item(kind, "".join(parser.parts), parser.entities, file_id)


def from_message(msg):
    kind = msg.content_type
    media = {
        "photo": lambda: msg.photo[-1].file_id,
        "document": lambda: msg.document.file_id,
        "video": lambda: msg.video.file_id,
        "audio": lambda: msg.audio.file_id,
        "animation": lambda: msg.animation.file_id,
        "voice": lambda: msg.voice.file_id,
        "video_note": lambda: msg.video_note.file_id,
        "sticker": lambda: msg.sticker.file_id,
    }
    if kind == "text":
        return encode_item("text", msg.text, msg.entities)
    if kind not in media:
        return None
    return encode_item(kind, msg.caption, msg.caption_entities, media[kind]())


async def deliver(message, value):
    item = decode_item(value)
    if item is None:
        # Previous plain-text stock remains readable; no HTML is interpreted.
        return await message.answer(value, parse_mode=None)
    kind, file_id = item["kind"], item["file_id"]
    text = item["text"]
    entities = [MessageEntity.model_validate(e) for e in item["entities"]]
    if kind == "text":
        return await message.answer(text, entities=entities, parse_mode=None)
    if kind in {"photo", "document", "video", "audio", "animation", "voice"}:
        method = getattr(message, f"answer_{kind}")
        argument = {"document": "document", "animation": "animation"}.get(kind, kind)
        return await method(**{argument: file_id}, caption=text or None,
                            caption_entities=entities or None, parse_mode=None)
    if kind == "video_note":
        result = await message.answer_video_note(file_id)
    elif kind == "sticker":
        result = await message.answer_sticker(file_id)
    else:
        raise ValueError(f"Unsupported item kind: {kind}")
    if text:
        await message.answer(text, entities=entities, parse_mode=None)
    return result
