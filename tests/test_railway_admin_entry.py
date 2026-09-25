import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tgbot.data.config import BotConfig, BotTexts
from tgbot.data.filters import IsAdmin
from tgbot.handlers import adminRouter
from tgbot.handlers.admins.main_admins import admin_command


@pytest.mark.asyncio
async def test_admin_entry_renders_existing_sections():
    message = SimpleNamespace(answer=AsyncMock())
    state = SimpleNamespace(clear=AsyncMock())
    await admin_command(message, state, BotTexts.Ru)
    state.clear.assert_awaited_once()
    keyboard = message.answer.call_args.kwargs['reply_markup']
    callbacks = {button.callback_data for row in keyboard.inline_keyboard for button in row}
    assert {'main_settings', 'extra_settings', 'switchers', 'find', 'stats',
            'products_manage', 'payments', 'mandatory_channels', 'menu_banners',
            'digital_admin:home', 'contests_admin', 'ad_buttons'} <= callbacks


@pytest.mark.asyncio
async def test_admin_filter_retained(monkeypatch):
    monkeypatch.setattr(BotConfig, 'ADMINS', [1])
    assert await IsAdmin()(SimpleNamespace(from_user=SimpleNamespace(id=1)))
    assert not await IsAdmin()(SimpleNamespace(from_user=SimpleNamespace(id=2)))
    assert any(isinstance(item.callback, IsAdmin)
               for item in adminRouter.message._handler.filters)
    assert any(handler.callback is admin_command for handler in adminRouter.message.handlers)


def test_all_admin_modules_registered():
    modules = {handler.callback.__module__.rsplit('.', 1)[-1]
               for observer in adminRouter.observers.values() for handler in observer.handlers}
    assert {'main_admins', 'products', 'payments', 'contests', 'subscriptions', 'digital_shop'} <= modules


def test_railway_overrides_stale_local_bind():
    env = dict(os.environ, RAILWAY_ENVIRONMENT_ID='fixture', WEBAPP_HOST='127.0.0.1', PORT='9137')
    result = subprocess.run([sys.executable, '-c',
        'from tgbot.data.config import BotConfig; print(BotConfig.WEBAPP_HOST, BotConfig.WEBAPP_PORT)'],
        env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '0.0.0.0 9137'
