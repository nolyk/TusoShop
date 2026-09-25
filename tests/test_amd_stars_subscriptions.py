"""Static integration checks for AMD, Telegram Stars, and managed subscriptions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def run():
    models = read("tgbot/utils/models.py")
    config = read("tgbot/data/config.py")
    refill = read("tgbot/handlers/users/refill.py")
    subscriptions = read("tgbot/handlers/admins/subscriptions.py")
    switchers = read("tgbot/middlewares/switchers.py")
    admin_keyboard = read("tgbot/keyboards/admins.py")
    db = read("tgbot/utils/db.py")
    admin_payments = read("tgbot/handlers/admins/payments.py")

    assert 'amd = "amd"' in models and '"sign": "֏"' in config
    for field in ("balance_amd", "price_amd", "discount_amd", "ref_earn_amd"):
        assert field in models
    assert "stars = Column(Boolean" in models
    assert 'currency="XTR"' in refill and "F.successful_payment" in refill
    assert "stars_pre_checkout" in refill and "stars_amd_per_star" in refill
    assert "class MandatoryChannel" in models
    assert "get_mandatory_channels(enabled_only=True)" in switchers
    assert "mandatory_channel:add" in admin_keyboard
    assert "add_mandatory_channel" in subscriptions
    assert "toggle_mandatory_channel" in subscriptions
    assert "delete_mandatory_channel" in subscriptions
    assert 'settings = await session.get_one(models.Settings, "main")' in db
    assert 'for method in ("cryptoBot", "xrocket", "yoomoney", "lolz", "lava", "aaio", "cryptomus", "stars")' in db
    assert 'if cryptoBot is None:' in admin_payments
    assert '"currency_code", "currency", "asset"' in admin_payments
    assert '"available", "balance", "amount"' in admin_payments
    print("AMD_STARS_SUBSCRIPTIONS PASS amd=PASS stars=PASS channels=PASS")


if __name__ == "__main__":
    run()
