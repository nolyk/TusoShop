from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from tgbot.data.texts import en, hy, ru, ua
from tgbot.services import shop_checkout
from tgbot.utils import item_content
from tgbot.utils.premium_emoji import strip_tg_emoji
from tgbot.webapp import app as webapp


PROMPT = "📰 Բոտից օգտվելուց առաջ անհրաժեշտ է բաժանորդագրվել մեր ալիքին։"


def test_subscription_prompt_is_used_for_new_users_and_recheck():
    for language in (ru, en, hy, ua):
        rendered = language.Language.Texts.channels_error.format(urls_txt="канал")
        expected = PROMPT.replace("📰", "⚠", 1) if language is hy else PROMPT
        assert strip_tg_emoji(rendered).startswith(f"<b>{expected}</b>")
        assert "канал" not in rendered
    middleware = Path("tgbot/middlewares/switchers.py").read_text(encoding="utf-8")
    handler = Path("tgbot/handlers/users/main_users.py").read_text(encoding="utf-8")
    assert "BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt)" in middleware
    assert "BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt)" in handler


def test_miniapp_refill_uses_shop_payment_methods_and_registers_invoice():
    api = Path("tgbot/webapp/app.py").read_text(encoding="utf-8")
    js = Path("tgbot/webapp/static/app.js").read_text(encoding="utf-8")
    for method in ("lolz", "aaio", "yoomoney", "lava", "cryptoBot",
                   "xrocket", "cryptomus", "stars", "custom_pay_method"):
        assert f'"{method}"' in api
    assert '@app.post("/api/refill")' in api
    assert '@app.post("/api/refill/check")' in api
    assert "await DB.add_refill" in api
    assert "await _finish_refill_from_webapp" in api
    assert "api('/api/refill'" in js
    assert "api('/api/refill/check'" in js
    assert "sendToBot({action: 'refill'" not in js


def test_checkout_ui_and_order_details_are_wired():
    js = Path("tgbot/webapp/static/app.js").read_text(encoding="utf-8")
    assert "'/api/shop/purchase'" in js
    assert "idempotency_key: purchaseKey" in js
    assert "data-order-id" in js
    assert "showOrder(button.dataset.orderKind, button.dataset.orderId)" in js
    assert "formatDateTime(order.unix)" in js
    assert "Открыть товар в боте" not in js
    assert "redeliver-order" in js


def test_purchase_key_requires_uuid4():
    key = str(uuid4())
    assert shop_checkout._receipt(key) == f"W-{key.replace('-', '')}"
    with pytest.raises(shop_checkout.ShopCheckoutError):
        shop_checkout._receipt("not-a-uuid")


def test_public_items_never_exposes_media_file_id():
    value = item_content.encode_item("photo", "Подпись", file_id="secret-telegram-file-id")
    purchase = SimpleNamespace(item=item_content.encode_purchase(["код <test>", value]))
    assert shop_checkout.public_items(purchase) == [
        {"kind": "text", "text": "код <test>"},
        {"kind": "media", "type": "photo", "caption": "Подпись"},
    ]


@pytest.mark.asyncio
async def test_checkout_rejects_reused_key_with_different_order(monkeypatch):
    user_id = 111
    key = str(uuid4())
    existing = SimpleNamespace(user_id=user_id, pos_id=12, count=1)

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        def begin(self): return self
        async def scalar(self, query):
            self.calls = getattr(self, "calls", 0) + 1
            return SimpleNamespace(is_ban=False) if self.calls == 1 else existing

    monkeypatch.setattr(shop_checkout.models, "async_session", Session)
    with pytest.raises(shop_checkout.ShopCheckoutError) as error:
        await shop_checkout.purchase_position(user_id, 99, 1, key, 25.0, "RUB")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_checkout_charges_once_and_returns_purchased_text(monkeypatch):
    user = SimpleNamespace(user_id=111, is_ban=False, balance_rub=100.0,
                           balance_usd=100.0, balance_eur=100.0, balance_amd=100.0)
    settings = SimpleNamespace(is_buy=True, is_work=False,
                               currency=SimpleNamespace(value="rub"))
    position = SimpleNamespace(pos_id=12, price_rub=25.0, price_usd=1.0,
                               price_eur=1.0, price_amd=10.0, is_infinity=False)
    stock = SimpleNamespace(item_id=7, data="CODE-123", file_id=None)
    saved = []

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        def begin(self): return self
        async def scalar(self, query):
            self.calls = getattr(self, "calls", 0) + 1
            return [user, saved[0] if saved else None, settings, position][self.calls - 1]
        async def execute(self, query):
            if query.is_select:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [stock]))
            return None
        def add(self, value): saved.append(value)

    async def delivered(user_id, values):
        assert user_id == 111 and values == ["CODE-123"]
        return True

    monkeypatch.setattr(shop_checkout.models, "async_session", Session)
    monkeypatch.setattr(shop_checkout, "_deliver", delivered)
    key = str(uuid4())
    first = await shop_checkout.purchase_position(111, 12, 1, key, 25.0, "RUB")
    assert first == {"receipt": shop_checkout._receipt(key),
                     "items": [{"kind": "text", "text": "CODE-123"}],
                     "delivery_status": "sent"}
    assert user.balance_rub == 75.0
    assert len(saved) == 1
    second = await shop_checkout.purchase_position(111, 12, 1, key, 25.0, "RUB")
    assert second["delivery_status"] == "already_purchased"
    assert user.balance_rub == 75.0
    assert len(saved) == 1


@pytest.mark.asyncio
async def test_checkout_refuses_changed_price_before_stock_or_balance_mutation(monkeypatch):
    user = SimpleNamespace(user_id=111, is_ban=False, balance_rub=100.0)
    settings = SimpleNamespace(is_buy=True, is_work=False,
                               currency=SimpleNamespace(value="rub"))
    position = SimpleNamespace(pos_id=12, price_rub=30.0)

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        def begin(self): return self
        async def scalar(self, query):
            self.calls = getattr(self, "calls", 0) + 1
            return [user, None, settings, position][self.calls - 1]
        async def execute(self, query):
            raise AssertionError("Stock must not be touched after a price mismatch")

    monkeypatch.setattr(shop_checkout.models, "async_session", Session)
    with pytest.raises(shop_checkout.ShopCheckoutError) as error:
        await shop_checkout.purchase_position(111, 12, 1, str(uuid4()), 25.0, "RUB")
    assert error.value.status_code == 409
    assert user.balance_rub == 100.0


@pytest.mark.asyncio
async def test_order_detail_denies_other_users_purchase(monkeypatch):
    async def missing_purchase(**kwargs):
        assert kwargs == {"user_id": 111, "receipt": "W-other"}
        return None

    monkeypatch.setattr(webapp.DB, "get_purchase", missing_purchase)
    with pytest.raises(HTTPException) as error:
        await webapp.order_detail("shop", "W-other", SimpleNamespace(user_id=111))
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_redelivery_denies_other_users_purchase(monkeypatch):
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def scalar(self, query): return None

    monkeypatch.setattr(shop_checkout.models, "async_session", Session)
    with pytest.raises(shop_checkout.ShopCheckoutError) as error:
        await shop_checkout.redeliver_purchase(111, "W-other")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_delivery_sends_text_to_own_telegram_chat(monkeypatch):
    sent = []

    class FakeBot:
        def __init__(self, token):
            self.session = self
        async def send_message(self, user_id, text, **kwargs):
            sent.append((user_id, text, kwargs))
        async def close(self): pass

    monkeypatch.setattr(shop_checkout, "Bot", FakeBot)
    assert await shop_checkout._deliver(111, ["CODE-123"]) is True
    assert sent == [(111, "CODE-123", {"parse_mode": None})]
