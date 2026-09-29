from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tgbot.data.config import DB, BotConfig, BotTexts
from tgbot.utils import models
from tgbot.utils.mini_app_menu import toggle_mini_app_menu, sync_mini_app_menu
from tgbot.keyboards.users import ReplyButtons
from tgbot.handlers.admins.main_admins import mini_app_menu_toggle
from tgbot.data.loader import adminRouter

@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['Reply','Inline'])
async def test_menu_cycle(monkeypatch,kind):
    monkeypatch.setattr(BotConfig,'WEBAPP_URL','https://fixture.example/app')
    monkeypatch.setattr(DB,'get_ad_buttons',AsyncMock(return_value=[Obj(name='Реклама',button_id=9)]))
    for enabled in (True,False,True):
        monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(mini_app_menu_enabled=enabled,keyboard=Obj(value=kind),faq='-',contests_is_on=False)))
        kb=await ReplyButtons().main_menu(BotTexts.Hy,1,[])
        rows=kb.keyboard if kind=='Reply' else kb.inline_keyboard
        assert any(getattr(b,'web_app',None) for row in rows for b in row)==enabled
        ad=next(b for row in rows for b in row if b.text=='Գովազդ')
        assert ad.icon_custom_emoji_id=='6181448263913187012'

@pytest.mark.asyncio
async def test_persistence_and_restart(monkeypatch):
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(models.Settings.__table__.create)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(models,'async_session',sessions)
    async with sessions() as session:
        session.add(models.Settings(settings='main'))
        await session.commit()
    bot=Obj(set_chat_menu_button=AsyncMock())
    assert (await DB.get_settings()).mini_app_menu_enabled is True
    assert await toggle_mini_app_menu(DB,bot,'https://fixture.example') is False
    assert (await DB.get_settings()).mini_app_menu_enabled is False
    assert bot.set_chat_menu_button.call_args.kwargs['menu_button'].type=='commands'
    restarted=Obj(set_chat_menu_button=AsyncMock())
    await sync_mini_app_menu(restarted,await DB.get_settings(),'https://fixture.example')
    assert restarted.set_chat_menu_button.call_args.kwargs['menu_button'].type=='commands'
    assert await toggle_mini_app_menu(DB,restarted,'https://fixture.example') is True
    assert restarted.set_chat_menu_button.call_args.kwargs['menu_button'].type=='web_app'
    await engine.dispose()

@pytest.mark.asyncio
async def test_invalid_url_no_write():
    db=Obj(get_settings=AsyncMock(return_value=Obj(mini_app_menu_enabled=False)),update_settings=AsyncMock())
    bot=Obj(set_chat_menu_button=AsyncMock())
    with pytest.raises(ValueError):
        await toggle_mini_app_menu(db,bot,'http://fixture.example')
    db.update_settings.assert_not_awaited()
    bot.set_chat_menu_button.assert_not_awaited()

@pytest.mark.asyncio
async def test_telegram_failure_restores_setting():
    db=Obj(get_settings=AsyncMock(return_value=Obj(mini_app_menu_enabled=True)),update_settings=AsyncMock())
    bot=Obj(set_chat_menu_button=AsyncMock(side_effect=RuntimeError('fixture unavailable')))
    with pytest.raises(RuntimeError):
        await toggle_mini_app_menu(db,bot,'https://fixture.example')
    assert [c.kwargs for c in db.update_settings.call_args_list]==[{'mini_app_menu_enabled':False},{'mini_app_menu_enabled':True}]

@pytest.mark.asyncio
async def test_admin_route_and_filter():
    handler=next(h for h in adminRouter.callback_query.handlers if h.callback is mini_app_menu_toggle)
    ok,_=await handler.check(Obj(data='mini_app_menu:toggle'))
    assert ok
    assert adminRouter.callback_query._handler.filters
    admin_filter=adminRouter.callback_query._handler.filters[0].callback
    assert await admin_filter(Obj(from_user=Obj(id=-123456))) is False

def test_migration_and_startup():
    assert 'ADD COLUMN IF NOT EXISTS mini_app_menu_enabled BOOLEAN NOT NULL DEFAULT true' in Path('tgbot/utils/models.py').read_text(encoding='utf-8')
    assert 'await sync_mini_app_menu(bot, await DB.get_settings(), BotConfig.WEBAPP_URL)' in Path('run.py').read_text(encoding='utf-8')
