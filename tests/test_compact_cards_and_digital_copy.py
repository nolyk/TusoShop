from unittest.mock import AsyncMock
from types import SimpleNamespace
from pathlib import Path
import pytest
from tgbot.data.config import BotConfig
from tgbot.handlers.users import digital_shop as shop


@pytest.mark.asyncio
async def test_requested_armenian_digital_messages(monkeypatch):
    monkeypatch.setattr(shop.digital_shop_repository, 'product_enabled', AsyncMock(return_value=True))
    edit = AsyncMock()
    monkeypatch.setattr(shop, 'edit_menu', edit)
    state = AsyncMock()
    call = SimpleNamespace()
    assert 'Գնեք <b>Telegram Stars</b> և <b>Premium</b>' in shop.DIGITAL_HOME_TEXT
    assert 'Գինը ֆիքսվում է պատվերը ստեղծելիս' in shop.DIGITAL_HOME_TEXT
    await shop.digital_stars(call, state)
    text = edit.call_args.args[1]
    assert 'Ընտրեք քանակը կամ մուտքագրեք ձեր տարբերակը։' in text
    assert 'Նվազագույնը՝ 50' in text and 'Առավելագույնը՝ 4,999' in text
    await shop.digital_stars_custom(call, state)
    assert 'Աստղերի իմ քանակը' in edit.call_args.args[1]
    assert '<b>50</b>-ից <b>4 999</b>' in edit.call_args.args[1]
    await shop.digital_premium(call, state)
    assert 'Վերջնական գինը կհաշվարկվի ստացողին հաստատելուց հետո։' in edit.call_args.args[1]
    await shop.show_recipient_step(call, state, 'premium', 12)
    assert 'Premium՝ 12 ամսով' in edit.call_args.args[1]
    assert 'Ո՞ւմ պետք է ուղարկվի գնումը:' in edit.call_args.args[1]
    state.update_data.assert_awaited_with(digital_product='premium', digital_quantity=12)


def test_mobile_products_remain_compact():
    css = Path('tgbot/webapp/static/styles.css').read_text(encoding='utf-8')
    assert '.product-grid{grid-template-columns:1fr}' not in css
    assert '#products.product-grid{grid-template-columns:repeat(2,minmax(0,1fr))' in css
    assert '#products .catalog-cover{height:100px' in css
    assert '#products .product-summary{display:none}' in css


def test_stars_buttons_use_telyx_and_keep_callbacks():
    from tgbot.handlers.users.digital_shop import recipient_keyboard, confirmation_keyboard, product_keyboard
    for markup in (recipient_keyboard('digital:stars'), confirmation_keyboard('stars'), product_keyboard()):
        for row in markup.inline_keyboard:
            for button in row:
                assert button.icon_custom_emoji_id
                assert button.callback_data.startswith('digital:')
                assert not any('А' <= ch <= 'я' for ch in button.text)


@pytest.mark.asyncio
async def test_admin_orders_no_longer_placeholder(monkeypatch):
    from tgbot.handlers.admins import digital_shop as admin
    monkeypatch.setattr(admin, 'private_admin', lambda call: True)
    listing = AsyncMock(return_value=[])
    monkeypatch.setattr(admin.digital_shop_repository, 'list_admin_orders', listing)
    edit = AsyncMock()
    monkeypatch.setattr(admin, 'edit_menu', edit)
    await admin.digital_admin_orders(SimpleNamespace(data='digital_admin:errors'))
    listing.assert_awaited_once_with(errors_only=True)
    assert 'Записей пока нет.' in edit.call_args.args[1]
