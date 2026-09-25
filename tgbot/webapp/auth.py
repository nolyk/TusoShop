import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


def verify_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = 900) -> dict:
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise TelegramAuthError("Telegram authorization is required")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise TelegramAuthError("Invalid Telegram authorization")
    try:
        auth_date = int(values.get("auth_date", "0"))
    except ValueError as exc:
        raise TelegramAuthError("Invalid authorization date") from exc
    now = int(time.time())
    if not auth_date or auth_date > now + 30 or now - auth_date > max_age_seconds:
        raise TelegramAuthError("Telegram authorization expired")
    try:
        user = json.loads(values.get("user", "{}"))
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("Invalid Telegram user") from exc
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise TelegramAuthError("Telegram user ID is required")
    return user
