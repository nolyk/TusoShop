from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tgbot.utils import models
from tgbot.data.config import DB, BotTexts
from tgbot.handlers.admins import main_admins as admin

@pytest.mark.asyncio
async def test_atomic_credit_preserves_fractions_and_other_user(monkeypatch):
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(models.User.__table__.create)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(models,'async_session',sessions)
    async with sessions() as session:
        session.add_all([models.User(user_id=123,total_refill=0.25),models.User(user_id=456)])
        await session.commit()
    for _ in range(2):
        await DB.credit_manual_refill(123,{'rub':10.5,'amd':1000})
    async with sessions() as session:
        user=await session.get(models.User,123);other=await session.get(models.User,456)
        assert (user.count_refills,user.total_refill,user.balance_rub,user.balance_amd)==(2,21.25,21,2000)
        assert other.count_refills==0 and other.balance_rub==0
    with pytest.raises(ValueError):
        await DB.credit_manual_refill(999,{'rub':1})
    await engine.dispose()

@pytest.mark.asyncio
@pytest.mark.parametrize('text',['abc',None,'-5','0','nan','inf'])
async def test_invalid_add_does_not_write(monkeypatch,text):
    credit=AsyncMock();monkeypatch.setattr(DB,'credit_manual_refill',credit)
    state=Obj(get_data=AsyncMock(return_value={'action':'add_balance'}),clear=AsyncMock())
    msg=Obj(text=text,reply=AsyncMock())
    await admin.enter_new_balance(msg,state,BotTexts.Ru)
    credit.assert_not_awaited();state.clear.assert_not_awaited();msg.reply.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize('action',['add_balance','minus_balance','edit_balance'])
async def test_only_add_credits_counter(monkeypatch,action):
    user=Obj(user_id=123,balance_rub=50,full_name='Fixture',is_ban=False)
    state=Obj(get_data=AsyncMock(return_value={'action':action,'user':user}),clear=AsyncMock())
    msg=Obj(text='10',reply=AsyncMock(),from_user=Obj(mention_html=lambda:'admin'))
    monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(currency=Obj(value='rub'))))
    monkeypatch.setattr(DB,'get_user',AsyncMock(return_value=user))
    monkeypatch.setattr(DB,'update_user',AsyncMock())
    monkeypatch.setattr(DB,'credit_manual_refill',AsyncMock())
    monkeypatch.setattr(admin.utils,'get_currency_amounts',AsyncMock(return_value={'rub':10}))
    monkeypatch.setattr(admin.utils,'send_admins',AsyncMock())
    monkeypatch.setattr(admin,'get_user_profile',AsyncMock(return_value='profile'))
    await admin.enter_new_balance(msg,state,BotTexts.Ru)
    if action=='add_balance':
        DB.credit_manual_refill.assert_awaited_once_with(123,{'rub':10});DB.update_user.assert_not_awaited()
    else:
        DB.credit_manual_refill.assert_not_awaited()
        assert 'count_refills' not in DB.update_user.call_args.kwargs
