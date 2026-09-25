from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from tgbot.data.config import BotConfig, BotTexts, DB
from tgbot.keyboards.users import ReplyButtons
from tgbot.utils.premium_emoji import storefront_ad_label


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['Reply', 'Inline'])
async def test_main_menu_top_and_clean_labels(monkeypatch, kind):
    monkeypatch.setattr(BotConfig, 'WEBAPP_URL', 'https://example.org/app')
    monkeypatch.setattr(DB, 'get_settings', AsyncMock(return_value=SimpleNamespace(
        keyboard=SimpleNamespace(value=kind), faq='yes', contests_is_on=True)))
    monkeypatch.setattr(DB, 'get_ad_buttons', AsyncMock(return_value=[SimpleNamespace(name='Реклама',button_id=9)]))
    menu = await ReplyButtons().main_menu(BotTexts.Hy, 1, [1])
    rows = menu.keyboard if kind == 'Reply' else menu.inline_keyboard
    assert len(rows[0]) == 1 and rows[0][0].text == 'Mini App'
    assert rows[0][0].web_app.url == 'https://example.org/app'
    assert any(b.text == 'Գովազդ' for row in rows for b in row)
    assert all(not b.text.startswith(('•','·','.')) for row in rows for b in row)
    if kind == 'Inline':
        assert rows[-1][0].callback_data == 'ad_button_open:9'


@pytest.mark.asyncio
async def test_translated_ad_still_opens_existing_record(monkeypatch):
    from tgbot.data.loader import ad_buttons_message
    ad = SimpleNamespace(name='Реклама', photo=None, text='Advertisement contents', links='')
    monkeypatch.setattr(DB, 'get_ad_button', AsyncMock(return_value=None))
    monkeypatch.setattr(DB, 'get_ad_buttons', AsyncMock(return_value=[ad]))
    message = SimpleNamespace(text='Գովազդ', answer=AsyncMock())
    await ad_buttons_message(message, BotTexts.Hy)
    message.answer.assert_awaited_once()
    assert message.answer.call_args.kwargs['text'] == ad.text
    assert ad.name == 'Реклама'


def test_ad_labels_remove_bullets_without_renaming_other_ads():
    assert storefront_ad_label('• Реклама') == 'Գովազդ'
    assert storefront_ad_label('Партнёры') == 'Партнёры'


@pytest.mark.asyncio
async def test_profile_armenian_short_labels_keep_actions(monkeypatch):
    from tgbot.keyboards.users import InlineButtons
    monkeypatch.setattr(DB, 'get_settings', AsyncMock(return_value=SimpleNamespace(is_ref=False)))
    menu = (await InlineButtons().profile_menu(BotTexts.Hy)).as_markup()
    buttons = {button.callback_data: button.text for row in menu.inline_keyboard for button in row}
    assert buttons['activate_promo'] == 'Պրոմոկոդ'
    assert buttons['purchases_history'] == 'Պատմություն'
