import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from cryptography.fernet import Fernet
from tonsdk.crypto import mnemonic_new
from tgbot.services.digital_shop.wallet_secret import encrypt_mnemonic, wallet_cipher
from tgbot.data.config import BotConfig
from tgbot.repositories.digital_shop import DigitalShopRepository


def test_wallet_requires_separate_key(monkeypatch):
    monkeypatch.delenv('WALLET_ENCRYPTION_KEY', raising=False)
    with pytest.raises(ValueError):
        wallet_cipher()


def test_mnemonic_encrypted_roundtrip_and_replacement(monkeypatch):
    monkeypatch.setenv('WALLET_ENCRYPTION_KEY', Fernet.generate_key().decode())
    phrase = ' '.join(mnemonic_new())
    cipher = encrypt_mnemonic(phrase)
    assert phrase not in cipher
    assert wallet_cipher().decrypt(cipher.encode()).decode() == phrase
    assert encrypt_mnemonic(phrase) != cipher
    with pytest.raises(ValueError):
        encrypt_mnemonic('down town hello')


@pytest.mark.asyncio
@pytest.mark.parametrize('stars,premium', [('auto','manual'),('manual','auto'),('auto','auto'),('manual','manual')])
async def test_independent_modes(stars, premium):
    repo = DigitalShopRepository()
    values = {'stars_fulfillment_mode': stars, 'premium_fulfillment_mode': premium}
    repo.get_setting = AsyncMock(side_effect=lambda key, default: values.get(key, default))
    assert await repo.fulfillment_mode('stars') == stars
    assert await repo.fulfillment_mode('premium') == premium
    with pytest.raises(ValueError):
        await repo.fulfillment_mode('invalid')


def test_custom_stars_and_optional_bot_purchase():
    js = Path('tgbot/webapp/static/app.js').read_text(encoding='utf-8')
    assert 'id="stars-quantity"' in js
    assert 'Number.isInteger(quantity) && quantity >= 50 && quantity <= 4999' in js
    assert "button: 'Գնել'" in js
    assert "send-product-bot" not in js


def test_private_admin_guard():
    from types import SimpleNamespace
    from tgbot.handlers.admins.digital_shop import private_admin
    assert not private_admin(SimpleNamespace(from_user=SimpleNamespace(id=-1), chat=SimpleNamespace(type='private')))



def test_message_body_is_never_logged_by_middleware():
    source = Path('tgbot/middlewares/exists_user.py').read_text(encoding='utf-8-sig')
    assert 'update.message.text' not in source
    assert 'Incoming message user_id=' in source
