from string import Formatter
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from tgbot.data.config import BotTexts,DB
from tgbot.keyboards.users import InlineButtons
from tgbot.utils import utils

def test_contest_text_ids_and_dynamic_fields():
    text=BotTexts.Hy.TEXTS.contest_text
    ids=['6181273677787571937','6183559145849890138','6181377573046461008','6183460812573646969','6181512409249750964']
    for id in ids: assert text.count(id)==1
    assert {name for _,name,_,_ in Formatter().parse(text) if name}=={'contest_id','prize','cur','end_time','winners_num','winners','members_num','members'}
    result=text.format(contest_id=27,prize='432.10',cur='֏',end_time='2 օր',winners_num=3,winners='հաղթող',members_num=42,members='մասնակից')
    for value in ['Խաղարկություն #27','432.10֏','2 օր','3 հաղթող','42 մասնակից']:assert value in result
    assert '6181220201149768417' in BotTexts.Hy.TEXTS.conditions
    assert '6181208703522317605' in BotTexts.Hy.TEXTS.conditions_refills
    assert '5472189467869619770' in BotTexts.Hy.TEXTS.conditions_purchases

@pytest.mark.parametrize('status',['OK','NO'])
def test_condition_status_preserved(status):
    assert f'1000 լիցքավորում — {status}' in BotTexts.Hy.TEXTS.conditions_refills.format(num=1000,refills='լիցքավորում',status=status)
    assert f'1 գնում — {status}' in BotTexts.Hy.TEXTS.conditions_purchases.format(num=1,purchases='գնում',status=status)

@pytest.mark.asyncio
@pytest.mark.parametrize('refills,purchases,expected',[(0,0,'NONE'),(0,1,'NONE'),(1000,0,'NONE'),(1000,1,'contest_enter:6')])
async def test_contest_conditions_and_warning_icon(monkeypatch,refills,purchases,expected):
    monkeypatch.setattr(DB,'get_purchases_stats_for_user',AsyncMock(return_value={'count_purchases':purchases}))
    contest=Obj(contest_id=6,refills_num=1000,purchases_num=1,channels_ids='')
    user=Obj(user_id=1,count_refills=refills)
    menu=(await InlineButtons().contest_inl(BotTexts.Hy,contest,user)).as_markup()
    button=menu.inline_keyboard[0][0]
    assert button.callback_data==expected
    if expected=='NONE':
        assert button.icon_custom_emoji_id=='6181207762924478466'
        assert not button.text.startswith('❗')
        assert 'Դուք չեք կատարել բոլոր պայմանները' in button.text
    else:
        assert 'Մասնակցել' in button.text
    assert menu.inline_keyboard[-1][0].callback_data=='back_to_user_menu'
