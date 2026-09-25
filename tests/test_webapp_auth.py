import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from tgbot.webapp.auth import TelegramAuthError, verify_telegram_init_data


def signed_init_data(bot_token: str, user: dict, auth_date: int) -> str:
    values = {"auth_date": str(auth_date), "query_id": "test-query", "user": json.dumps(user, separators=(",", ":"))}
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_valid_telegram_init_data():
    token = "123456:TEST_TOKEN"
    payload = signed_init_data(token, {"id": 42, "first_name": "Test"}, int(time.time()))
    assert verify_telegram_init_data(payload, token)["id"] == 42


def test_tampered_telegram_init_data_is_rejected():
    token = "123456:TEST_TOKEN"
    payload = signed_init_data(token, {"id": 42}, int(time.time())).replace("42", "43")
    with pytest.raises(TelegramAuthError):
        verify_telegram_init_data(payload, token)


def test_expired_telegram_init_data_is_rejected():
    token = "123456:TEST_TOKEN"
    payload = signed_init_data(token, {"id": 42}, int(time.time()) - 3600)
    with pytest.raises(TelegramAuthError):
        verify_telegram_init_data(payload, token, max_age_seconds=900)
