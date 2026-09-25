import asyncio
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from tgbot.data.config import BotConfig
from tgbot.repositories.digital_shop import DigitalShopRepository, digital_shop_repository as repo
from tgbot.webapp import app as web
from tgbot.handlers.users import digital_shop as users
from tgbot.handlers.admins import digital_shop as admins


@pytest.mark.asyncio
async def test_stars_default_and_database_override(monkeypatch):
    monkeypatch.setattr(BotConfig, 'DIGITAL_SHOP_ENABLED', True)
    monkeypatch.setattr(BotConfig, 'DIGITAL_STARS_ENABLED', False)
    storage = {}
    monkeypatch.setattr(repo, 'get_setting', AsyncMock(side_effect=lambda key, default: storage.get(key, default)))
    assert not await repo.product_enabled('stars')
    storage['stars_enabled'] = 'true'
    assert await repo.product_enabled('stars')
    storage['stars_enabled'] = 'false'
    assert not await repo.product_enabled('stars')
    monkeypatch.setattr(BotConfig, 'DIGITAL_SHOP_ENABLED', False)
    storage['stars_enabled'] = 'true'
    assert not await repo.product_enabled('stars')


@pytest.mark.asyncio
async def test_disabled_stars_hidden_in_catalog_and_bot(monkeypatch):
    monkeypatch.setattr(repo, 'product_enabled', AsyncMock(side_effect=lambda product: product == 'premium'))
    monkeypatch.setattr(web.DB, 'get_settings', AsyncMock(return_value=Obj(is_buy=False)))
    result = await web.digital_products()
    assert [p['id'] for p in result['products']] == ['premium']
    keyboard = await users.digital_home_keyboard()
    assert 'digital:stars' not in [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert 'digital:premium' in [b.callback_data for row in keyboard.inline_keyboard for b in row]


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['digital_stars', 'digital_stars_custom', 'digital_stars_amount'])
async def test_stale_stars_buttons_blocked(monkeypatch, name):
    monkeypatch.setattr(repo, 'product_enabled', AsyncMock(return_value=False))
    call = Obj(data='digital:stars_amount:50', answer=AsyncMock())
    state = Obj(clear=AsyncMock())
    await getattr(users, name)(call, state)
    call.answer.assert_awaited_once()
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_stale_payment_blocked_before_balance_access(monkeypatch):
    monkeypatch.setattr(repo, 'product_enabled', AsyncMock(return_value=False))
    get_user = AsyncMock(side_effect=AssertionError('Balance must not be read'))
    monkeypatch.setattr(users.DB, 'get_user', get_user)
    state = Obj(clear=AsyncMock(), get_data=AsyncMock(return_value={
        'digital_product': 'stars', 'digital_quantity': 50, 'digital_recipient': 'fixture',
        'digital_base_amount': '100', 'digital_markup_percent': '0',
        'digital_total_amount': '100', 'digital_fulfillment_mode': 'manual',
    }))
    call = Obj(answer=AsyncMock())
    await users.digital_payment_balance(call, state)
    get_user.assert_not_awaited()
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_quote_returns_503_without_provider(monkeypatch):
    monkeypatch.setattr(BotConfig, 'DIGITAL_SHOP_ENABLED', True)
    monkeypatch.setattr(repo, 'product_enabled', AsyncMock(return_value=False))
    monkeypatch.setattr(web.DB, 'get_settings', AsyncMock(return_value=Obj(is_buy=True, is_work=False)))
    with pytest.raises(HTTPException) as caught:
        await web.digital_quote(web.DigitalQuoteRequest(
            product='stars', quantity=50, recipient_mode='self'), Obj(is_ban=False))
    assert caught.value.status_code == 503


@pytest.mark.asyncio
async def test_toggle_requires_private_admin(monkeypatch):
    monkeypatch.setattr(BotConfig, 'ADMINS', [1])
    save = AsyncMock()
    monkeypatch.setattr(repo, 'set_stars_enabled', save)
    call = Obj(from_user=Obj(id=2), chat=Obj(type='private'), answer=AsyncMock())
    await admins.set_stars_availability(call)
    save.assert_not_awaited()
    call.answer.assert_awaited_once_with('Нет доступа', show_alert=True)
    with pytest.raises(PermissionError):
        await DigitalShopRepository().set_stars_enabled(False, 2)


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['0', '1'])
async def test_admin_callback_saves_explicit_state(monkeypatch, value):
    monkeypatch.setattr(admins, 'private_admin', lambda event: True)
    save = AsyncMock()
    monkeypatch.setattr(repo, 'set_stars_enabled', save)
    monkeypatch.setattr(admins, 'stars_availability', AsyncMock())
    call = Obj(data=f'digital_stars_enabled:{value}', from_user=Obj(id=1), answer=AsyncMock())
    await admins.set_stars_availability(call)
    save.assert_awaited_once_with(value == '1', 1)


@pytest.mark.asyncio
async def test_http_static_assets():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=web.app), base_url='http://test') as client:
        for path in ('/', '/static/app.js', '/static/styles.css', '/static/stars-logo.webp'):
            response = await client.get(path)
            assert response.status_code == 200
            assert response.content


@pytest.mark.asyncio
async def test_runtime_cancels_bot_on_web_shutdown():
    from run import supervise
    stopped = asyncio.Event()
    class Server:
        should_exit = False
        async def serve(self):
            await asyncio.sleep(0.02)
    async def worker():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
    await supervise(Server(), worker)
    assert stopped.is_set()


@pytest.mark.asyncio
async def test_runtime_exits_if_bot_fails():
    from run import supervise
    class Server:
        should_exit = False
        async def serve(self):
            while not self.should_exit:
                await asyncio.sleep(0.01)
    async def worker():
        raise RuntimeError('fixture bot failure')
    with pytest.raises(RuntimeError, match='fixture bot failure'):
        await supervise(Server(), worker)


def test_railway_config():
    import tomllib
    config = tomllib.loads(Path('railway.toml').read_text())
    assert config['deploy']['startCommand'] == 'python run.py'
    assert config['deploy']['healthcheckPath'] == '/health'
    assert config['deploy']['numReplicas'] == 1
    assert '.env.*' in Path('.dockerignore').read_text()


def test_runtime_requires_admin_and_https(monkeypatch):
    from run import validate_environment
    monkeypatch.setattr(BotConfig, 'ADMINS', [])
    with pytest.raises(RuntimeError, match='BOT_ADMINS'):
        validate_environment()
    monkeypatch.setattr(BotConfig, 'ADMINS', [1])
    monkeypatch.setattr(BotConfig, 'WEBAPP_URL', 'http://localhost')
    with pytest.raises(RuntimeError, match='HTTPS'):
        validate_environment()
