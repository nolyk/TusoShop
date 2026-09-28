from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from tgbot.data.config import BotConfig, BotTexts, DB
from tgbot.keyboards.users import ReplyButtons
from tgbot.handlers import userRouter
from tgbot.handlers.users.digital_shop import digital_home_message
EXPECTED = {'Mini app': '6181221171812377434', 'Գնել': '6181477413856224769', 'Աջակցություն': '6183774199157367778', 'Լիցքավորել հաշվեկշիռը': '6181704819489644554', 'Իմ էջը': '6181512409249750964', 'Խաղարկություններ': '6184004370749726738', 'Գովազդ': '6183558664813550912', 'Stars & Premium': '6181597355112932310'}
@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['Reply','Inline'])
@pytest.mark.parametrize('admin',[False,True])
async def test_brand_buttons(monkeypatch,kind,admin):
    monkeypatch.setattr(BotConfig,'WEBAPP_URL','https://fixture.up.railway.app')
    monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(keyboard=Obj(value=kind),faq='-',contests_is_on=True)))
    monkeypatch.setattr(DB,'get_ad_buttons',AsyncMock(return_value=[Obj(name='Реклама',button_id=9)]))
    menu = await ReplyButtons().main_menu(BotTexts.Hy,1,[1] if admin else [])
    rows = menu.keyboard if kind == 'Reply' else menu.inline_keyboard
    buttons = {b.text:b for row in rows for b in row}
    for label,emoji in EXPECTED.items():
        assert buttons[label].model_dump()['icon_custom_emoji_id'] == emoji
    assert buttons['Mini app'].web_app.url == 'https://fixture.up.railway.app'
    assert (BotTexts.Hy.BUTTONS.admin_panel in buttons) == admin
    if kind == 'Inline':
        for label,action in {'Գնել':'buy','Իմ էջը':'profile','Աջակցություն':'support','Լիցքավորել հաշվեկշիռը':'refill','Խաղարկություններ':'contests','Գովազդ':'ad_button_open:9','Stars & Premium':'digital:home'}.items():
            assert buttons[label].callback_data == action

@pytest.mark.asyncio
@pytest.mark.parametrize('text',['Stars & Premium','⭐ Stars & Premium'])
async def test_stars_reply_filter_accepts_old_and_new(text):
    handler = next(h for h in userRouter.message.handlers if h.callback is digital_home_message)
    accepted,_ = await handler.check(Obj(text=text))
    assert accepted

def test_shop_brand():
    assert 'ԹույնShop' in BotTexts.Hy.TEXTS.main_menu
    html = Path('tgbot/webapp/static/index.html').read_text(encoding='utf-8')
    assert '<title>ԹույնShop</title>' in html
    assert 'AUTOSHOP' not in html

@pytest.mark.asyncio
@pytest.mark.parametrize('text',['Խաղարկություններ','🎁 Խաղարկություններ'])
async def test_contest_reply_filter_accepts_old_and_new(text):
    from tgbot.handlers.users.contests import contests_user
    handlers = [h for h in userRouter.message.handlers if h.callback is contests_user]
    results = [await h.check(Obj(text=text)) for h in handlers]
    assert any(result[0] for result in results)
