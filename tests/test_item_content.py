import asyncio
import sys
import types
import unittest

try:
    from aiogram.types import MessageEntity
except ImportError:
    aiogram = types.ModuleType("aiogram")
    aiogram_types = types.ModuleType("aiogram.types")

    class MessageEntity:
        def __init__(self, **values):
            self.values = values

        def model_dump(self, exclude_none=True):
            return self.values

        @classmethod
        def model_validate(cls, values):
            return cls(**values)

    aiogram_types.MessageEntity = MessageEntity
    sys.modules["aiogram"] = aiogram
    sys.modules["aiogram.types"] = aiogram_types

from tgbot.utils import item_content


class FakeMessage:
    def __init__(self):
        self.calls = []

    async def answer(self, text, **kwargs):
        self.calls.append(("text", text, kwargs))

    async def answer_photo(self, photo, **kwargs):
        self.calls.append(("photo", photo, kwargs))

    async def answer_document(self, document, **kwargs):
        self.calls.append(("document", document, kwargs))


class ContentTests(unittest.TestCase):
    def test_text_preserves_entities_without_html(self):
        entities = [MessageEntity(type="bold", offset=0, length=5),
                    MessageEntity(type="custom_emoji", offset=6, length=2,
                                  custom_emoji_id="123456")]
        payload = item_content.encode_item("text", "Привет 😎", entities)
        self.assertNotIn("<b>", payload)
        decoded = item_content.decode_item(payload)
        self.assertEqual(decoded["text"], "Привет 😎")
        self.assertEqual(decoded["entities"][1]["custom_emoji_id"], "123456")
        result = FakeMessage()
        asyncio.run(item_content.deliver(result, payload))
        self.assertEqual(result.calls[0][0], "text")
        self.assertIsNone(result.calls[0][2]["parse_mode"])
        self.assertEqual(result.calls[0][2]["entities"][0].model_dump()["type"], "bold")

    def test_mixed_purchase_and_caption(self):
        photo = item_content.encode_item("photo", "Жирный 😎", [
            MessageEntity(type="bold", offset=0, length=6)], "file-123")
        document = item_content.encode_item("document", "Файл", [], "doc-123")
        stored = item_content.encode_purchase([photo, document])
        result = FakeMessage()
        for payload in item_content.decode_purchase(stored):
            asyncio.run(item_content.deliver(result, payload))
        self.assertEqual([call[0] for call in result.calls], ["photo", "document"])
        self.assertEqual(result.calls[0][2]["caption"], "Жирный 😎")
        self.assertIsNone(result.calls[0][2]["parse_mode"])

    def test_legacy_caption_does_not_show_html_tags(self):
        payload = item_content.legacy_media_item(
            "photo", '<b>Жирно</b> <tg-emoji emoji-id="123">😎</tg-emoji>', "old-photo")
        decoded = item_content.decode_item(payload)
        self.assertEqual(decoded["text"], "Жирно 😎")
        self.assertEqual([entity["type"] for entity in decoded["entities"]],
                         ["bold", "custom_emoji"])
        result = FakeMessage()
        asyncio.run(item_content.deliver(result, payload))
        self.assertEqual(result.calls[0][2]["caption"], "Жирно 😎")


if __name__ == "__main__":
    unittest.main()
