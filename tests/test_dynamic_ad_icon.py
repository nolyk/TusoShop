from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from aiogram.methods import SendMessage
from tgbot.data.config import BotConfig, BotTexts, DB
from tgbot.data.loader import bot
from tgbot.keyboards.users import ReplyButtons

@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['Reply','Inline'])
@pytest.mark.parametrize('name',['Ալիք #1','Канал #1','Sponsor custom'])
async def test_custom_ad_name_gets_requested_icon(monkeypatch,kind,name):
    monkeypatch.setattr(BotConfig,'WEBAPP_URL','https://fixture.example')
    monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(keyboard=Obj(value=kind),faq='-',contests_is_on=False,mini_app_menu_enabled=True)))
    monkeypatch.setattr(DB,'get_ad_buttons',AsyncMock(return_value=[Obj(name=name,button_id=9)]))
    keyboard=await ReplyButtons().main_menu(BotTexts.Hy,1,[])
    method=SendMessage(chat_id=1,text='test',reply_markup=keyboard)
    await bot.session.middleware.wrap_middlewares(AsyncMock())(bot,method)
    rows=keyboard.keyboard if kind=='Reply' else keyboard.inline_keyboard
    button=rows[-1][0]
    assert button.text==name
    assert button.icon_custom_emoji_id=='6181448263913187012'
    if kind=='Inline':
        assert button.callback_data=='ad_button_open:9'
