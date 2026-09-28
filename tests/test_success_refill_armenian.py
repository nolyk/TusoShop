from string import Formatter
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from tgbot.data.config import BotTexts,DB
from tgbot.handlers.users import refill as r

def test_success_template_preserves_fields():
    text=BotTexts.Hy.TEXTS.success_refill_text
    assert {n for _,n,_,_ in Formatter().parse(text) if n}=={'amount','curr','way','receipt'}
    for id in ('6181423645160646167','6181612022426247965','6181523988481581415'):assert text.count(id)==1
    assert 'Ձեր հաշվեկշիռը հաջողությամբ լիցքավորվել է' in text
    assert 'Եղանակ՝' in text and 'Անդորրագիր՝' in text

@pytest.mark.asyncio
@pytest.mark.parametrize('way',['custom_pay_method','stars'])
async def test_russian_admin_cannot_change_customer_language(monkeypatch,way):
    monkeypatch.setattr(DB,'get_refill',AsyncMock(side_effect=lambda *a,**kw:None if kw.get('is_finished') else Obj(currency=Obj(value='rub'))))
    monkeypatch.setattr(DB,'get_user',AsyncMock(return_value=Obj(full_name='Fixture',total_refill=10,count_refills=1,balance_rub=20,ref_id=None)))
    monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(custom_pay_method='Bank',is_ref=False)))
    update=AsyncMock();monkeypatch.setattr(DB,'update_user',update)
    finish=AsyncMock();monkeypatch.setattr(DB,'update_refill',finish)
    monkeypatch.setattr(r.utils,'get_currency_amounts',AsyncMock(return_value={'rub':100}))
    monkeypatch.setattr(r.utils,'send_admins',AsyncMock())
    sender=AsyncMock();monkeypatch.setattr(r.bot,'send_message',sender)
    call=Obj(answer=AsyncMock(),message=Obj(delete=AsyncMock(),answer=AsyncMock()))
    await r.success_refill(BotTexts.Ru,call,way,100,'fixture-42',1,100)
    message=sender.call_args.args[1] if way=='custom_pay_method' else call.message.answer.call_args.args[0]
    assert 'Ձեր հաշվեկշիռը' in message and 'Вы успешно' not in message
    assert '100.0' in message and 'fixture-42' in message
    for id in ('6181423645160646167','6181612022426247965','6181523988481581415'):assert id in message
    update.assert_awaited_once_with(user_id=1,total_refill=110.0,count_refills=2,balance_rub=120)
    finish.assert_awaited_once_with('fixture-42',is_finish=1)

@pytest.mark.asyncio
async def test_already_finished_not_credited(monkeypatch):
    monkeypatch.setattr(DB,'get_refill',AsyncMock(return_value=Obj()))
    update=AsyncMock();monkeypatch.setattr(DB,'update_user',update)
    call=Obj(answer=AsyncMock())
    await r.success_refill(BotTexts.Ru,call,'custom_pay_method',100,'fixture-42',1,100)
    update.assert_not_awaited()
    call.answer.assert_awaited_once()
