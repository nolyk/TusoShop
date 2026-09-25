from pathlib import Path
from types import SimpleNamespace

import pytest

from tgbot.webapp import app as webapp


def test_mini_app_is_in_main_menu_and_digital_shop_is_renamed():
    keyboard = Path("tgbot/keyboards/users.py").read_text(encoding="utf-8")
    handler = Path("tgbot/handlers/users/digital_shop.py").read_text(encoding="utf-8")
    assert 'text="Mini App"' in keyboard
    assert "web_app=WebAppInfo" in keyboard
    assert 'text="Stars & Premium"' in keyboard
    assert "⭐ Stars & Premium" in handler
    assert "Цифровые товары" not in keyboard


def test_mini_app_controls_have_real_handlers():
    html = Path("tgbot/webapp/static/index.html").read_text(encoding="utf-8")
    javascript = Path("tgbot/webapp/static/app.js").read_text(encoding="utf-8")
    handler = Path("tgbot/handlers/users/digital_shop.py").read_text(encoding="utf-8")
    for control in ('id="topup"', 'id="categories"', 'data-tab="history"', 'id="sheet-continue"'):
        assert control in html
    assert "openProduct" in javascript
    assert "tg.sendData" in javascript
    assert '/api/digital/quote' in javascript
    assert "F.web_app_data" in handler


def test_favicon_is_embedded_without_extra_request():
    html = Path("tgbot/webapp/static/index.html").read_text(encoding="utf-8")
    assert 'rel="icon" href="data:image/svg+xml' in html


def test_profile_and_admin_controlled_topup_are_connected():
    html = Path("tgbot/webapp/static/index.html").read_text(encoding="utf-8")
    javascript = Path("tgbot/webapp/static/app.js").read_text(encoding="utf-8")
    api = Path("tgbot/webapp/app.py").read_text(encoding="utf-8")
    handler = Path("tgbot/handlers/users/digital_shop.py").read_text(encoding="utf-8")
    for field in ("profile-id", "profile-referrer", "stat-refills", "profile-balances"):
        assert f'id="{field}"' in html
    assert "/api/payment-methods" in javascript
    assert '@app.get("/api/payment-methods")' in api
    assert "DB.get_enabled_payments()" in api
    assert "settings.is_refill" in api
    assert "action: 'refill'" in javascript
    assert 'action == "refill"' in handler


def test_professional_ui_has_motion_and_accessibility_fallback():
    css = Path("tgbot/webapp/static/styles.css").read_text(encoding="utf-8")
    assert "@keyframes sheetUp" in css
    assert "@keyframes reveal" in css
    assert "prefers-reduced-motion" in css
    assert ".wallet-card" in css
    assert ".profile-card" in css


def test_dark_montserrat_and_local_lucide_assets():
    static = Path("tgbot/webapp/static")
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "styles.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    icons = (static / "icons.js").read_text(encoding="utf-8")
    assert '--bg:#05060a' in css
    assert 'font-family:Montserrat' in css
    assert (static / "fonts/Montserrat[wght].ttf").stat().st_size > 100_000
    assert (static / "fonts/Montserrat-OFL.txt").exists()
    assert (static / "fonts/LUCIDE-LICENSE.txt").exists()
    assert 'src="/static/icons.js' in html
    assert 'data-icon="house"' in html
    assert 'data-icon="user-round"' in html
    assert 'window.MiniIcons.hydrate()' in javascript
    assert 'const LUCIDE_PATHS' in icons
    assert 'stroke="currentColor"' in icons


@pytest.mark.asyncio
async def test_catalog_combines_active_autoshop_goods_and_telegram(monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(webapp.digital_shop_repository, 'product_enabled', AsyncMock(return_value=True))
    async def settings_on():
        return SimpleNamespace(is_buy=True, currency=SimpleNamespace(value="rub"))

    async def positions():
        return [SimpleNamespace(pos_id=7, name="Test item", description="Digital delivery", is_infinity=True, price_rub=125)]

    monkeypatch.setattr(webapp.DB, "get_settings", settings_on)
    monkeypatch.setattr(webapp.DB, "get_all_positions", positions)
    result = await webapp.digital_products()
    assert any(item["id"] == "shop:7" and item["price"] == 125 for item in result["products"])
    assert any(item["id"] == "stars" for item in result["products"])


@pytest.mark.asyncio
async def test_payment_methods_follow_admin_switches(monkeypatch):
    async def settings_on():
        return SimpleNamespace(is_refill=True, currency=SimpleNamespace(value="rub"))

    async def enabled_methods():
        return ["cryptoBot", "stars", "xrocket"]

    monkeypatch.setattr(webapp.DB, "get_settings", settings_on)
    monkeypatch.setattr(webapp.DB, "get_enabled_payments", enabled_methods)
    result = await webapp.payment_methods(SimpleNamespace())
    assert result["enabled"] is True
    assert [item["id"] for item in result["methods"]] == ["cryptoBot", "stars"]

    async def settings_off():
        return SimpleNamespace(is_refill=False, currency=SimpleNamespace(value="rub"))

    monkeypatch.setattr(webapp.DB, "get_settings", settings_off)
    result = await webapp.payment_methods(SimpleNamespace())
    assert result["enabled"] is False
    assert result["methods"] == []
