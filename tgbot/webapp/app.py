import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from aiogram.types import LabeledPrice
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from jwt import PyJWTError
from pydantic import BaseModel, StrictInt
from sqlalchemy import select, text

from tgbot.data.config import BotConfig, DB
from tgbot.data.loader import bot
from tgbot.repositories.digital_shop import digital_shop_repository
from tgbot.services.shop_checkout import (
    ShopCheckoutError, public_items, purchase_position, redeliver_purchase,
)
from tgbot.utils import models, payments, utils
from tgbot.webapp.auth import TelegramAuthError, verify_telegram_init_data

from AsyncPayments.aaio import AsyncAaio
from AsyncPayments.cryptomus import AsyncCryptomus
from AsyncPayments.cryptomus.models import InvoiceStatuses
from AsyncPayments.lolz import AsyncLolzteamMarketPayment


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="ԹույնShop Mini App", version="1.0.0", docs_url=None, redoc_url=None)
if BotConfig.WEBAPP_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(BotConfig.WEBAPP_ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TelegramAuthRequest(BaseModel):
    init_data: str


class ShopPurchaseRequest(BaseModel):
    position_id: int
    quantity: int
    idempotency_key: str
    expected_unit_price: float
    expected_currency: str


class RefillCreateRequest(BaseModel):
    method: str
    amount: float


class RefillCheckRequest(BaseModel):
    method: str
    receipt: str
    amount: float
    second_amount: float


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    async with models.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": "autoshop-miniapp"}


@app.get("/api/digital/products")
async def digital_products():
    products = []
    settings = await DB.get_settings()
    categories = {}
    subcategories = {}
    if settings.is_buy:
        currency = settings.currency.value if settings.currency else "rub"
        for position in await DB.get_all_positions():
            available = position.is_infinity or bool(await DB.get_items(pos_id=position.pos_id))
            if not available:
                continue
            cat_id = getattr(position, "cat_id", None)
            sub_id = getattr(position, "sub_cat_id", None)
            if cat_id is not None and cat_id not in categories:
                category = await DB.get_category(cat_id=cat_id)
                categories[cat_id] = category.name if category else "Այլ ապրանքներ"
            if sub_id is not None and sub_id not in subcategories:
                subcategory = await DB.get_subcategory(sub_cat_id=sub_id)
                subcategories[sub_id] = subcategory.name if subcategory else "Այլ ապրանքներ"
            photo = getattr(position, "photo", None)
            products.append({
                "category_id": str(cat_id) if cat_id is not None else "uncategorized",
                "category_name": categories.get(cat_id, "Այլ ապրանքներ"),
                "subcategory_id": str(sub_id) if sub_id is not None else None,
                "subcategory_name": subcategories.get(sub_id),
                "description": position.description or "",
                "max_quantity": 10,
                "id": f"shop:{position.pos_id}",
                "title": position.name or "ԹույնShop ապրանք",
                "subtitle": position.description or "Թվային ապրանք",
                "image": (photo if photo.startswith("https://") else f"/api/shop/products/{position.pos_id}/photo") if photo and photo != "-" else None,
                "price": round(float(getattr(position, f"price_{currency}") or 0), 2),
                "currency": currency.upper(),
                "currency_sign": BotConfig.CURRENCIES[currency]["sign"],
                "category": "goods",
            })
    if await digital_shop_repository.product_enabled("stars"):
        products.append({"id": "stars", "title": "Telegram Stars", "subtitle": "Սկսած 50 աստղից", "image": "/static/stars-logo.webp", "category": "telegram"})
    if await digital_shop_repository.product_enabled("premium"):
        products.append({"id": "premium", "title": "Telegram Premium", "subtitle": "3, 6 կամ 12 ամիս", "image": "/static/premium-logo.webp", "category": "telegram"})
    if await digital_shop_repository.product_enabled("gift"):
        products.append({"id": "gift", "title": "Telegram նվերներ", "subtitle": "Նվերներ ձեզ և ընկերներին", "image": "/static/stars-logo.webp", "category": "telegram"})
    return {"enabled": BotConfig.DIGITAL_SHOP_ENABLED, "products": products}


@app.post("/api/auth/telegram")
async def telegram_auth(payload: TelegramAuthRequest):
    if not BotConfig.JWT_SECRET:
        raise HTTPException(status_code=503, detail="Mini App authentication is not configured")
    try:
        user = verify_telegram_init_data(payload.init_data, BotConfig.BOT_TOKEN)
    except TelegramAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user_id = int(user["id"])
    existing = await DB.get_user(user_id=user_id)
    full_name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
    if existing is None:
        await DB.register_user(user_id, user.get("username"), full_name)
    else:
        await DB.update_user(user_id, user_name=user.get("username"), full_name=full_name)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=30)},
        BotConfig.JWT_SECRET,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": 1800}


ORDER_STATUS_LABELS = {
    "created": "Ստեղծված է",
    "awaiting_payment": "Սպասում է վճարմանը",
    "paid": "Վճարված է",
    "processing": "Մշակվում է",
    "completed": "Կատարված է",
    "cancelled": "Չեղարկված է",
    "fulfillment_failed": "Առաքման սխալ",
    "refund_pending": "Վերադարձը պահանջված է",
    "refunded": "Վերադարձ",
}

PRODUCT_TYPE_LABELS = {
    "stars": "Telegram Stars",
    "premium": "Telegram Premium",
    "gift": "Telegram նվեր",
}

LANGUAGE_LABELS = {
    "ru": "Ռուսերեն",
    "en": "English",
    "ua": "Ուկրաիներեն",
}

PAYMENT_METHODS = {
    "lolz": {
        "title": "Lolzteam",
        "subtitle": "Վճարում Lolzteam Market-ով",
        "icon": "wallet",
    },
    "aaio": {
        "title": "Aaio",
        "subtitle": "Քարտեր և էլեկտրոնային վճարումներ",
        "icon": "card",
    },
    "yoomoney": {
        "title": "ЮMoney",
        "subtitle": "Վճարում ЮMoney հաշիվով",
        "icon": "wallet",
    },
    "lava": {
        "title": "Lava",
        "subtitle": "Վճարում Lava հաշիվով",
        "icon": "card",
    },
    "cryptoBot": {
        "title": "Crypto Bot",
        "subtitle": "Կրիպտոարժույթ և բանկային քարտեր",
        "icon": "crypto",
    },
    "xrocket": {
        "title": "xRocket",
        "subtitle": "Վճարում xRocket-ով",
        "icon": "rocket",
    },
    "cryptomus": {
        "title": "Cryptomus",
        "subtitle": "Կրիպտո վճարում Cryptomus-ով",
        "icon": "crypto",
    },
    "stars": {
        "title": "Telegram Stars",
        "subtitle": "Վճարում աստղերով Telegram-ում",
        "icon": "stars",
    },
    "custom_pay_method": {
        "title": "Idram/BankCard/Telcell",
        "subtitle": "Վճարում մենեջերի միջոցով",
        "icon": "manager",
    },
}


async def _enabled_payment_ids(settings=None) -> list[str]:
    settings = settings or await DB.get_settings()
    payments_state = await DB.get_payments()
    if not settings.is_refill:
        return []
    return [
        method_id
        for method_id in PAYMENT_METHODS
        if bool(payments_state.get(method_id))
    ]


async def _init_refill_payments():
    payment_config = await DB.get_payments_config()
    clients = {
        "lolz": None,
        "aaio": None,
        "cryptoBot": None,
        "xrocket": None,
        "lava": None,
        "yoomoney": None,
        "cryptomus": None,
    }
    try:
        try:
            clients["lolz"] = AsyncLolzteamMarketPayment(payment_config.get("lolz_token", ""))
        except (ValueError, AttributeError, IndexError):
            pass
        try:
            clients["aaio"] = AsyncAaio(
                payment_config.get("aaio_api_key", ""),
                payment_config.get("aaio_shop_id", ""),
                payment_config.get("aaio_secret_key_1", ""),
            )
        except ValueError:
            pass
        try:
            clients["cryptoBot"] = payments.CryptoPay(payment_config.get("crypto_token") or "")
        except (ValueError, Exception):
            pass
        try:
            clients["xrocket"] = payments.XRocketPay(
                payment_config.get("xrocket_token") or "",
                payment_config.get("xrocket_asset") or "USDT",
            )
        except (ValueError, Exception):
            pass
        try:
            clients["cryptomus"] = AsyncCryptomus(
                payment_config.get("payment_api_key", ""),
                payment_config.get("merchant_id", ""),
                "None",
            )
        except Exception:
            pass
        try:
            clients["lava"] = payments.Lava(
                payment_config.get("lava_project_id", ""),
                payment_config.get("lava_secret_key", ""),
            )
        except Exception:
            pass
        try:
            clients["yoomoney"] = payments.YooMoney(
                payment_config.get("yoomoney_token", ""),
                payment_config.get("yoomoney_number", ""),
            )
        except Exception:
            pass
    except Exception:
        pass
    return clients


def _texts_for_user(user: models.User):
    language = user.language.value if user.language else "ru"
    from tgbot.data.config import BotTexts
    return {
        "hy": BotTexts.Hy,
        "en": BotTexts.En,
        "ua": BotTexts.Ua,
        "ru": BotTexts.Ru,
    }.get(language, BotTexts.Ru)


def _validate_refill_amount(amount: float, min_amount: float, max_amount: float):
    if amount <= 0 or not min_amount <= amount <= max_amount:
        raise HTTPException(
            status_code=422,
            detail=f"Գումարը պետք է լինի {min_amount}-ից մինչև {max_amount}",
        )


async def _refill_limits(settings, method_id: str) -> tuple[float, float]:
    currency = settings.currency
    min_amount = 5 if currency == models.Currencies.rub else await utils.get_exchange(5, "RUB", currency.value.upper())
    max_amount = 100000 if currency == models.Currencies.rub else await utils.get_exchange(100000, "RUB", currency.value.upper())
    if method_id == "custom_pay_method":
        min_amount = max(float(settings.custom_pay_method_min_amount or 0), float(min_amount))
    return float(min_amount), float(max_amount)


def _first_existing_attr(value, *names):
    for name in names:
        candidate = getattr(value, name, None)
        if candidate:
            return candidate
    return None


def _custom_card_marker(card_id) -> str:
    return f"custom_card:{int(card_id)}"


async def _custom_pay_instruction_text(card_id=None) -> tuple[models.CustomPayCard | None, str]:
    card = await DB.get_custom_pay_card(card_id) if card_id else None
    if not card:
        card = await DB.get_random_custom_pay_card()
    if not card:
        return None, "Փոխանցման քարտերը դեռ կարգավորված չեն։ Դիմեք աջակցությանը։"
    note = f"\n<b>Նշում՝</b> {card.note}" if card.note else ""
    return card, (
        "<b>🏦 Փոխանցման տվյալներ</b>\n\n"
        f"<b>Բանկ՝</b> <code>{card.bank_name}</code>\n"
        f"<b>Ստացող՝</b> <code>{card.holder_name}</code>\n"
        f"<b>Քարտ՝</b> <code>{card.card_number}</code>{note}\n\n"
        "Փոխանցումից հետո սեղմեք ստուգման կոճակը։"
    )


async def _finish_refill_from_webapp(user: models.User, method_id: str, receipt: str, pay_amount: float) -> dict:
    texts = _texts_for_user(user)
    settings = await DB.get_settings()
    refill = await DB.get_refill(receipt)
    if not refill or refill.user_id != user.user_id:
        raise HTTPException(404, "Լիցքավորումը չի գտնվել")
    if await DB.get_refill(receipt=receipt, is_finished=True):
        raise HTTPException(409, "Հաշվեկշիռն արդեն լիցքավորված է")
    amounts = await utils.get_currency_amounts(pay_amount, refill.currency.value)
    await utils.send_admins(
        "refill_log",
        user_mention=f"<a href='tg://user?id={user.user_id}'>{user.full_name}</a>",
        user_id=user.user_id,
        pay_amount=pay_amount,
        curr=BotConfig.CURRENCIES[refill.currency.value]["sign"],
        pay_id=receipt,
        way=texts.TEXTS.payments_names.get(method_id, PAYMENT_METHODS[method_id]["title"])
        if method_id != "custom_pay_method" else settings.custom_pay_method,
    )
    await DB.update_refill(receipt, is_finish=1)
    await DB.update_user(
        user_id=user.user_id,
        total_refill=int(user.total_refill or 0) + float(amounts["rub"]),
        count_refills=int(user.count_refills or 0) + 1,
        **{
            f"balance_{code}": round(float(getattr(user, f"balance_{code}") or 0) + float(value), 2)
            for code, value in amounts.items()
        },
    )
    return {
        "status": "paid",
        "receipt": receipt,
        "amount": pay_amount,
        "currency": refill.currency.value.upper(),
        "currency_sign": BotConfig.CURRENCIES[refill.currency.value]["sign"],
    }


def _decode_token(authorization: str) -> int:
    if not BotConfig.JWT_SECRET:
        raise HTTPException(status_code=503, detail="Mini App authentication is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token_value = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token_value, BotConfig.JWT_SECRET, algorithms=["HS256"])
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc


async def get_current_user(authorization: str = Header(default="")) -> models.User:
    user_id = _decode_token(authorization)
    user = await DB.get_user(user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/me")
async def profile(user: models.User = Depends(get_current_user)):
    settings = await DB.get_settings()
    currency = settings.currency.value if settings.currency else "rub"
    return {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "full_name": user.full_name or "",
        "language": (user.language.value if user.language else "ru"),
        "language_label": LANGUAGE_LABELS.get(user.language.value if user.language else "ru", "Ռուսերեն"),
        "reg_date": user.reg_date or "",
        "balance": {
            "rub": round(float(user.balance_rub or 0), 2),
            "usd": round(float(user.balance_usd or 0), 2),
            "eur": round(float(user.balance_eur or 0), 2),
            "amd": round(float(user.balance_amd or 0), 2),
        },
        "total_refill": round(float(user.total_refill or 0), 2),
        "count_refills": int(user.count_refills or 0),
        "ref_count": int(user.ref_count or 0),
        "ref_id": user.ref_id,
        "ref_level": int(user.ref_lvl or 1),
        "currency": currency.upper(),
        "currency_sign": BotConfig.CURRENCIES[currency]["sign"],
        "is_admin": user.user_id in BotConfig.ADMINS,
    }


@app.get("/api/payment-methods")
async def payment_methods(user: models.User = Depends(get_current_user)):
    del user
    settings = await DB.get_settings()
    currency = settings.currency.value if settings.currency else "rub"
    enabled_ids = await _enabled_payment_ids(settings)
    limits = [await _refill_limits(settings, method_id) for method_id in enabled_ids]
    methods = []
    for method_id in enabled_ids:
        if method_id not in PAYMENT_METHODS:
            continue
        item = {"id": method_id, **PAYMENT_METHODS[method_id]}
        if method_id == "custom_pay_method":
            item["title"] = settings.custom_pay_method or "Idram/BankCard/Telcell"
            item["subtitle"] = "Վճարում մենեջերի միջոցով"
        methods.append(item)
    return {
        "enabled": bool(settings.is_refill and methods),
        "methods": methods,
        "currency": currency.upper(),
        "currency_sign": BotConfig.CURRENCIES[currency]["sign"],
        "min_amount": min([amount for amount, _ in limits], default=5),
        "max_amount": max([amount for _, amount in limits], default=100000),
    }


@app.post("/api/refill")
async def create_refill(payload: RefillCreateRequest, user: models.User = Depends(get_current_user)):
    settings = await DB.get_settings()
    method_id = payload.method
    enabled_ids = await _enabled_payment_ids(settings)
    if method_id not in enabled_ids:
        raise HTTPException(403, "Վճարման այս եղանակը հասանելի չէ")
    amount = round(float(payload.amount), 2)
    min_amount, max_amount = await _refill_limits(settings, method_id)
    _validate_refill_amount(amount, min_amount, max_amount)

    unfinished = await DB.get_unfinished_user_refill(user.user_id)
    if unfinished and utils.get_unix() <= unfinished.under_date:
        return {
            "status": "existing",
            "method": unfinished.way,
            "receipt": unfinished.receipt,
            "pay_url": unfinished.pay_url if unfinished.pay_url != "-" else "",
            "amount": unfinished.amount,
            "second_amount": unfinished.second_amount,
            "currency": unfinished.currency.value.upper(),
            "currency_sign": BotConfig.CURRENCIES[unfinished.currency.value]["sign"],
            "under_date": datetime.fromtimestamp(unfinished.under_date).strftime("%d.%m.%Y %H:%M:%S"),
            "instructions": (await _custom_pay_instruction_text(
                unfinished.pay_url.split(":", 1)[1]
                if unfinished.pay_url and unfinished.pay_url.startswith("custom_card:") else None
            ))[1] if unfinished.way == "custom_pay_method" else "",
            "checkable": unfinished.way not in {"stars", "custom_pay_method"},
        }
    if unfinished:
        await DB.delete_refill(unfinished.receipt)

    currency = settings.currency
    currency_code = currency.value.upper()
    bot_name = (await bot.get_me()).username
    user_name = user.full_name or user.user_name or str(user.user_id)
    comment = _texts_for_user(user).TEXTS.payment_comment_api.format(
        user_name=user_name,
        bot_name=bot_name,
        curr=BotConfig.CURRENCIES[currency.value]["sign"],
        pay_amount=amount,
    )
    success_url = BotConfig.WEBAPP_URL or f"https://t.me/{bot_name}"
    amount_rub = amount if currency == models.Currencies.rub else await utils.get_exchange(amount, currency_code, "RUB")
    pay_url = ""
    receipt = str(utils.get_unix(True))
    checkable = True
    invoice_stars = None

    clients = await _init_refill_payments()
    try:
        if method_id == "custom_pay_method":
            card, instructions = await _custom_pay_instruction_text()
            if not card:
                raise HTTPException(503, instructions)
            pay_url = _custom_card_marker(card.card_id)
            checkable = False
        elif method_id == "stars":
            amount_amd = amount if currency == models.Currencies.amd else await utils.get_exchange(amount, currency_code, "AMD")
            rate = float(settings.stars_amd_per_star or 100)
            if rate <= 0:
                raise HTTPException(503, "Stars փոխարժեքը կարգավորված չէ")
            invoice_stars = max(1, math.ceil(float(amount_amd) / rate))
            receipt = f"stars:{user.user_id}:{amount}:{currency.value}:{receipt}"
            pay_url = await bot.create_invoice_link(
                title="ԹույնShop",
                description=f"Հաշվեկշռի լիցքավորում՝ {amount}{BotConfig.CURRENCIES[currency.value]['sign']}",
                payload=receipt,
                currency="XTR",
                prices=[LabeledPrice(label="Telegram Stars", amount=invoice_stars)],
            )
            checkable = False
        elif method_id == "cryptoBot":
            crypto_bot = clients["cryptoBot"]
            if crypto_bot is None:
                raise HTTPException(503, "Crypto Bot կարգավորված չէ")
            invoice_amount = amount
            invoice_currency = currency_code
            if currency == models.Currencies.amd:
                invoice_amount = await utils.get_exchange(amount, "AMD", "USD")
                invoice_currency = "USD"
            payment = await crypto_bot.create_invoice(
                invoice_amount,
                fiat=invoice_currency,
                description=comment,
                success_url=success_url,
                payload=f"refill:{user.user_id}:{receipt}",
            )
            receipt = str(payment.get("invoice_id"))
            pay_url = payment.get("bot_invoice_url") or payment.get("pay_url") or payment.get("mini_app_invoice_url") or ""
        elif method_id == "xrocket":
            xrocket = clients["xrocket"]
            if xrocket is None:
                raise HTTPException(503, "xRocket ХЇХЎЦЂХЈХЎХѕХёЦЂХѕХЎХ® Х№Х§")
            invoice_amount = amount if currency != models.Currencies.rub else await utils.get_exchange(amount, "RUB", "USD")
            payment = await xrocket.create_invoice(
                invoice_amount,
                comment,
                f"refill:{user.user_id}:{receipt}",
                success_url,
            )
            receipt = str(payment.get("id") or payment.get("invoice_id") or payment.get("invoiceId") or payment.get("uuid") or receipt)
            links = payment.get("links") if isinstance(payment.get("links"), dict) else {}
            pay_url = str(
                payment.get("link")
                or payment.get("payLink")
                or payment.get("paymentLink")
                or payment.get("url")
                or links.get("telegramBotLink")
                or links.get("web")
                or ""
            )
        elif method_id == "lava":
            lava = clients["lava"]
            if lava is None:
                raise HTTPException(503, "Lava կարգավորված չէ")
            payment = await lava.create_invoice(amount_rub, success_url, comment)
            data = payment.get("data", payment)
            receipt = str(data.get("id") or data.get("invoice_id") or data.get("invoiceId") or receipt)
            pay_url = str(data.get("url") or data.get("paymentUrl") or data.get("payment_url") or "")
        elif method_id == "yoomoney":
            yoomoney = clients["yoomoney"]
            if yoomoney is None:
                raise HTTPException(503, "ЮMoney կարգավորված չէ")
            payment = yoomoney.create_yoomoney_link(amount_rub, receipt)
            pay_url = payment["link"]
        elif method_id == "lolz":
            lolz = clients["lolz"]
            if lolz is None:
                raise HTTPException(503, "Lolzteam կարգավորված չէ")
            payment = await lolz.create_invoice(amount=amount_rub, comment=comment)
            receipt = str(_first_existing_attr(payment, "invoice_id", "id") or receipt)
            pay_url = str(_first_existing_attr(payment, "url", "pay_url", "link") or "")
        elif method_id == "aaio":
            aaio = clients["aaio"]
            if aaio is None:
                raise HTTPException(503, "Aaio կարգավորված չէ")
            payment = await aaio.create_payment(amount=amount_rub, order_id=receipt, desc=comment, currency="RUB")
            receipt = str(_first_existing_attr(payment, "order_id", "id") or receipt)
            pay_url = str(_first_existing_attr(payment, "url", "pay_url", "payment_url") or "")
        elif method_id == "cryptomus":
            cryptomus = clients["cryptomus"]
            if cryptomus is None:
                raise HTTPException(503, "Cryptomus կարգավորված չէ")
            payment = await cryptomus.create_payment(amount=str(amount_rub), currency="RUB", order_id=receipt, url_return=success_url)
            receipt = str(_first_existing_attr(payment, "order_id", "uuid") or receipt)
            pay_url = str(_first_existing_attr(payment, "url", "payment_url") or "")
        else:
            raise HTTPException(422, "Վճարման եղանակը դեռ չունի հաշվի ստեղծիչ")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Չհաջողվեց ստեղծել վճարման հաշիվ: {exc}") from exc

    if method_id != "stars":
        await DB.add_refill(float(amount_rub), method_id, user.user_id, receipt, pay_url or "-", float(amount), currency)

    return {
        "status": "created",
        "method": method_id,
        "method_title": settings.custom_pay_method if method_id == "custom_pay_method" else PAYMENT_METHODS[method_id]["title"],
        "receipt": receipt,
        "pay_url": "" if pay_url == "-" else pay_url,
        "amount": amount_rub,
        "second_amount": amount,
        "currency": currency_code,
        "currency_sign": BotConfig.CURRENCIES[currency.value]["sign"],
        "under_date": datetime.fromtimestamp(utils.get_unix() + 3600).strftime("%d.%m.%Y %H:%M:%S"),
        "instructions": instructions if method_id == "custom_pay_method" else "",
        "checkable": checkable,
        "invoice_stars": invoice_stars,
    }


@app.post("/api/refill/check")
async def check_refill(payload: RefillCheckRequest, user: models.User = Depends(get_current_user)):
    refill = await DB.get_refill(payload.receipt)
    if not refill or refill.user_id != user.user_id:
        raise HTTPException(404, "Լիցքավորումը չի գտնվել")
    if refill.is_finish:
        return {"status": "paid", "receipt": refill.receipt}
    clients = await _init_refill_payments()
    method_id = payload.method
    try:
        if method_id == "cryptoBot":
            if clients["cryptoBot"] is None:
                raise HTTPException(503, "Crypto Bot ХЇХЎЦЂХЈХЎХѕХёЦЂХѕХЎХ® Х№Х§")
            status = await clients["cryptoBot"].is_paid(payload.receipt)
        elif method_id == "xrocket":
            if clients["xrocket"] is None:
                raise HTTPException(503, "xRocket ХЇХЎЦЂХЈХЎХѕХёЦЂХѕХЎХ® Х№Х§")
            status = await clients["xrocket"].is_paid(payload.receipt)
        elif method_id == "lava":
            status = await clients["lava"].status_invoice(payload.receipt)
        elif method_id == "lolz":
            status = (await clients["lolz"].get_invoice(invoice_id=payload.receipt)).status == "paid"
        elif method_id == "yoomoney":
            status = clients["yoomoney"].check_yoomoney_payment(payload.receipt)
        elif method_id == "aaio":
            status = (await clients["aaio"].get_order_info(payload.receipt)).status in ["success", "hold"]
        elif method_id == "cryptomus":
            status = (await clients["cryptomus"].payment_info(order_id=payload.receipt)).status in [
                InvoiceStatuses.PAID,
                InvoiceStatuses.PAID_OVER,
            ]
        else:
            raise HTTPException(422, "Այս եղանակը Mini App-ում ձեռքով չի ստուգվում")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Չհաջողվեց ստուգել վճարումը: {exc}") from exc
    if not status:
        return {"status": "pending", "receipt": payload.receipt}
    return await _finish_refill_from_webapp(user, method_id, payload.receipt, payload.second_amount)


@app.get("/api/orders")
async def orders(user: models.User = Depends(get_current_user)):
    settings = await DB.get_settings()
    currency = settings.currency.value if settings.currency else "rub"
    digital_orders = await digital_shop_repository.list_user_orders(user.user_id, limit=50)
    digital_items = []
    for order in digital_orders:
        created = order.created_at
        digital_items.append(
            {
                "kind": "digital",
                "id": order.public_id,
                "title": PRODUCT_TYPE_LABELS.get(order.product_type, order.product_type),
                "detail": _digital_order_detail(order),
                "status": order.status,
                "status_label": ORDER_STATUS_LABELS.get(order.status, order.status),
                "amount": str(order.total_amount or 0),
                "currency": (order.currency or "RUB").upper(),
                "unix": int(created.timestamp()) if created else 0,
            }
        )
    purchases = await DB.get_last_purchases(user.user_id, 50)
    shop_items = []
    for purchase in purchases:
        position = await DB.get_position(pos_id=purchase.pos_id)
        shop_items.append(
            {
                "kind": "shop",
                "id": purchase.receipt,
                "title": position.name if position else f"Ապրանք #{purchase.pos_id}",
                "detail": f"{purchase.count} հատ",
                "status": "completed",
                "status_label": "Կատարված է",
                "amount": str(getattr(purchase, f"price_{currency}") or 0),
                "currency": currency.upper(),
                "unix": int(purchase.unix or 0),
            }
        )
    merged = sorted(digital_items + shop_items, key=lambda item: item["unix"], reverse=True)
    return {"orders": merged}


@app.get("/api/orders/{kind}/{order_id}")
async def order_detail(kind: str, order_id: str, user: models.User = Depends(get_current_user)):
    if kind == "shop":
        purchase = await DB.get_purchase(user_id=user.user_id, receipt=order_id)
        if purchase is None:
            raise HTTPException(status_code=404, detail="Պատվերը չի գտնվել")
        position = await DB.get_position(pos_id=purchase.pos_id)
        settings = await DB.get_settings()
        currency = settings.currency.value if settings.currency else "rub"
        return {"kind": "shop", "id": purchase.receipt,
                "title": position.name if position else f"Ապրանք #{purchase.pos_id}",
                "status": "completed", "status_label": "Կատարված է",
                "quantity": purchase.count, "amount": str(getattr(purchase, f"price_{currency}") or 0),
                "currency": currency.upper(), "unix": int(purchase.unix or 0),
                "items": public_items(purchase)}
    if kind == "digital":
        async with models.async_session() as session:
            order = await session.scalar(select(models.DigitalOrder).where(
                models.DigitalOrder.public_id == order_id,
                models.DigitalOrder.user_id == user.user_id,
            ))
        if order is None:
            raise HTTPException(status_code=404, detail="Պատվերը չի գտնվել")
        return {"kind": "digital", "id": order.public_id,
                "title": PRODUCT_TYPE_LABELS.get(order.product_type, order.product_type),
                "status": order.status,
                "status_label": ORDER_STATUS_LABELS.get(order.status, order.status),
                "quantity": str(order.quantity), "recipient": order.recipient,
                "amount": str(order.total_amount), "currency": order.currency.upper(),
                "unix": int(order.created_at.timestamp()) if order.created_at else 0,
                "completed_unix": int(order.completed_at.timestamp()) if order.completed_at else 0,
                "detail": _digital_order_detail(order)}
    raise HTTPException(status_code=404, detail="Պատվերը չի գտնվել")


@app.post("/api/shop/purchase")
async def shop_purchase(payload: ShopPurchaseRequest, user: models.User = Depends(get_current_user)):
    try:
        return await purchase_position(user.user_id, payload.position_id, payload.quantity,
                                       payload.idempotency_key, payload.expected_unit_price,
                                       payload.expected_currency)
    except ShopCheckoutError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/orders/shop/{receipt}/deliver")
async def deliver_shop_order(receipt: str, user: models.User = Depends(get_current_user)):
    try:
        sent = await redeliver_purchase(user.user_id, receipt)
    except ShopCheckoutError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not sent:
        raise HTTPException(status_code=503, detail="Չհաջողվեց ուղարկել ապրանքը զրույցին։ Փորձեք ավելի ուշ։")
    return {"sent": True}


def _digital_order_detail(order: models.DigitalOrder) -> str:
    product_type = order.product_type
    quantity = str(order.quantity).rstrip("0").rstrip(".") if order.quantity is not None else ""
    if product_type == "stars":
        return f"{quantity} Stars"
    if product_type == "premium":
        return f"{quantity} ամիս"
    if product_type == "gift":
        return order.recipient or "Նվեր"
    return f"Քանակ՝ {quantity}"


@app.get("/api/shop/products/{position_id}/photo")
async def product_photo(position_id: int):
    """Only public product cover images, never purchased content or bot token URLs."""
    from io import BytesIO
    from aiogram import Bot
    settings = await DB.get_settings()
    position = await DB.get_position(pos_id=position_id)
    photo = getattr(position, "photo", None)
    if not settings.is_buy or not photo or photo == "-" or "://" in photo:
        raise HTTPException(404, "Լուսանկարը բացակայում է")
    bot = Bot(BotConfig.BOT_TOKEN)
    try:
        file = await bot.get_file(photo)
        if not file.file_path or not file.file_size or file.file_size > 8 * 1024 * 1024:
            raise HTTPException(413, "Լուսանկարը չափազանց մեծ է")
        content = BytesIO()
        await bot.download_file(file.file_path, destination=content, timeout=15)
        data = content.getvalue()
        if data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            raise HTTPException(415, "Լուսանկարի ձևաչափը չի աջակցվում")
        return Response(data, media_type=mime, headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Լուսանկարը ժամանակավորապես հասանելի չէ") from None
    finally:
        await bot.session.close()


class DigitalQuoteRequest(BaseModel):
    product: str
    quantity: StrictInt
    recipient_mode: str
    username: str = ""


@app.post("/api/digital/quote")
async def digital_quote(payload: DigitalQuoteRequest, user: models.User = Depends(get_current_user)):
    import re
    from decimal import Decimal, InvalidOperation
    from tgbot.integrations.marketapp import marketapp, MarketAppError
    from tgbot.services.digital_shop.pricing import calculate_quote
    if user.is_ban:
        raise HTTPException(403, "Հաշիվն արգելափակված է")
    settings = await DB.get_settings()
    if not settings.is_buy or settings.is_work or not BotConfig.DIGITAL_SHOP_ENABLED:
        raise HTTPException(503, "Գնումները ժամանակավորապես անջատված են")
    if payload.product not in {"stars", "premium"}:
        raise HTTPException(422, "Անհայտ ապրանք")
    if (payload.product == "stars" and not 50 <= payload.quantity <= 4999) or (payload.product == "premium" and payload.quantity not in {3, 6, 12}):
        raise HTTPException(422, "Անվավեր քանակ")
    if not await digital_shop_repository.product_enabled(payload.product):
        raise HTTPException(503, "Ապրանքն անջատված է")
    if payload.recipient_mode not in {"self", "other"}:
        raise HTTPException(422, "Ընտրեք ստացողին")
    username = ((user.user_name or "") if payload.recipient_mode == "self" else payload.username).strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,31}", username):
        raise HTTPException(422, "Նշեք ստացողի Telegram username-ը։ Ձեզ համար գնելու համար սահմանեք username Telegram-ում։")
    try:
        recipient = await marketapp.recipient(payload.product, username)
        amount = await (marketapp.stars_price_ton(payload.quantity) if payload.product == "stars" else marketapp.premium_price_ton(payload.quantity))
        rate = await marketapp.ton_rub_rate()
        markup = Decimal(await digital_shop_repository.get_setting(f"{payload.product}_markup_percent", "0" if payload.product == "stars" else "7"))
        if not amount.is_finite() or not rate.is_finite() or not markup.is_finite() or amount <= 0 or rate <= 0:
            raise ValueError("Invalid quote")
        quote = calculate_quote(product_type=payload.product, quantity=payload.quantity, unit_price=amount * rate / Decimal(payload.quantity), markup_percent=markup)
    except (MarketAppError, ValueError, InvalidOperation):
        raise HTTPException(503, "Չհաջողվեց ստուգել ստացողին և գինը։ Փորձեք ավելի ուշ։") from None
    return {"recipient": username, "recipient_name": str(recipient.get("name") or username), "quantity": payload.quantity,
            "total": str(quote.total_amount), "currency": "RUB", "payment_enabled": True,
            "payment_message": "Վճարումը կստեղծվի բոտի զրույցում՝ ադմինի ձեռքով հաստատումով։"}
