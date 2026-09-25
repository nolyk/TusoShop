"""Atomic balance checkout for AutoShop positions opened in the Mini App."""

from datetime import datetime
from math import isfinite
import logging
from uuid import UUID

from aiogram import Bot
from aiogram.types import MessageEntity
from sqlalchemy import delete, select

from tgbot.data.config import BotConfig
from tgbot.utils import item_content, models


log = logging.getLogger(__name__)


class ShopCheckoutError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _receipt(key: str) -> str:
    try:
        value = UUID(key)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ShopCheckoutError("Некорректный ключ покупки") from exc
    if value.version != 4:
        raise ShopCheckoutError("Некорректный ключ покупки")
    return f"W-{value.hex}"


def _stored_item(item: models.Item) -> str:
    if item_content.decode_item(item.data):
        return item.data
    if item.file_id:
        kind, file_id = item.file_id.split(":", 1)
        if kind not in {"photo", "file", "document", "video", "audio", "animation", "voice"}:
            raise ShopCheckoutError("Формат товара не поддерживается в Mini App")
        return item_content.legacy_media_item(
            "document" if kind == "file" else kind, item.data or "", file_id
        )
    return item.data or ""


def public_items(purchase: models.Purchase) -> list[dict]:
    """Expose purchased text, never Telegram file IDs or HTML from stock."""
    stored = item_content.decode_purchase(purchase.item)
    if stored is None:
        stored = [purchase.item or ""]
    result = []
    for value in stored:
        parsed = item_content.decode_item(value)
        if parsed is None:
            result.append({"kind": "text", "text": value})
        elif parsed["kind"] == "text":
            result.append({"kind": "text", "text": parsed.get("text") or ""})
        else:
            result.append({"kind": "media", "type": parsed["kind"], "caption": parsed.get("text") or ""})
    return result


async def _deliver(user_id: int, values: list[str]) -> bool:
    """Delivery is best-effort after the database commit; order remains recoverable."""
    bot = None
    try:
        bot = Bot(BotConfig.BOT_TOKEN)
        for value in values:
            parsed = item_content.decode_item(value)
            if parsed is None:
                await bot.send_message(user_id, value, parse_mode=None)
                continue
            kind = parsed["kind"]
            text = parsed.get("text") or ""
            entities = [MessageEntity.model_validate(entity) for entity in parsed.get("entities") or []]
            if kind == "text":
                await bot.send_message(user_id, text, entities=entities or None, parse_mode=None)
            elif kind in {"photo", "document", "video", "audio", "animation", "voice"}:
                method = getattr(bot, f"send_{kind}")
                await method(user_id, parsed["file_id"], caption=text or None,
                             caption_entities=entities or None, parse_mode=None)
            else:
                return False
        return True
    except Exception:
        log.exception("Mini App order delivery failed for user %s", user_id)
        return False
    finally:
        if bot is not None:
            await bot.session.close()


async def purchase_position(user_id: int, position_id: int, quantity: int, key: str,
                            expected_unit_price: float, expected_currency: str) -> dict:
    if not 1 <= quantity <= 10:
        raise ShopCheckoutError("Количество должно быть от 1 до 10")
    receipt = _receipt(key)
    values = []
    created = False
    async with models.async_session() as session:
        async with session.begin():
            user = await session.scalar(
                select(models.User).where(models.User.user_id == user_id).with_for_update()
            )
            if user is None or user.is_ban:
                raise ShopCheckoutError("Пользователь недоступен", 403)
            existing = await session.scalar(
                select(models.Purchase).where(models.Purchase.receipt == receipt)
            )
            if existing is not None:
                if existing.user_id != user_id or existing.pos_id != position_id or existing.count != quantity:
                    raise ShopCheckoutError("Ключ покупки уже использован", 409)
                purchase = existing
            else:
                settings = await session.scalar(
                    select(models.Settings).where(models.Settings.settings == "main")
                )
                if settings is None or not settings.is_buy or settings.is_work:
                    raise ShopCheckoutError("Покупки сейчас отключены", 403)
                currency = settings.currency.value if settings.currency else "rub"
                position = await session.scalar(
                    select(models.Position).where(models.Position.pos_id == position_id).with_for_update()
                )
                if position is None:
                    raise ShopCheckoutError("Товар не найден", 404)
                unit = round(float(getattr(position, f"price_{currency}") or 0), 2)
                if (not isfinite(expected_unit_price) or round(expected_unit_price, 2) != unit
                        or expected_currency.lower() != currency):
                    raise ShopCheckoutError("Цена или валюта изменились. Обновите каталог и попробуйте снова.", 409)
                amount = round(unit * quantity, 2)
                if amount < 0:
                    raise ShopCheckoutError("Цена товара некорректна")
                if round(float(getattr(user, f"balance_{currency}") or 0), 2) < amount:
                    raise ShopCheckoutError("Недостаточно средств на балансе", 409)
                stock_count = 1 if position.is_infinity else quantity
                stock = (await session.execute(
                    select(models.Item)
                    .where(models.Item.pos_id == position_id)
                    .order_by(models.Item.item_id)
                    .limit(stock_count)
                    .with_for_update(skip_locked=True)
                )).scalars().all()
                if len(stock) != stock_count:
                    raise ShopCheckoutError("Товар закончился или сейчас покупается", 409)
                values = [_stored_item(stock[0])] * quantity if position.is_infinity else [
                    _stored_item(item) for item in stock
                ]
                if not position.is_infinity:
                    await session.execute(delete(models.Item).where(
                        models.Item.item_id.in_([item.item_id for item in stock])
                    ))
                # AutoShop stores equivalent balances in all currencies; mirror its bot checkout.
                for code in ("rub", "usd", "eur", "amd"):
                    field = f"balance_{code}"
                    charge = round(float(getattr(position, f"price_{code}") or 0) * quantity, 2)
                    setattr(user, field, round(float(getattr(user, field) or 0) - charge, 2))
                purchase = models.Purchase(
                    user_id=user_id,
                    receipt=receipt,
                    count=quantity,
                    price_rub=round(float(position.price_rub or 0) * quantity, 2),
                    price_usd=round(float(position.price_usd or 0) * quantity, 2),
                    price_eur=round(float(position.price_eur or 0) * quantity, 2),
                    price_amd=round(float(position.price_amd or 0) * quantity, 2),
                    pos_id=position_id,
                    item=item_content.encode_purchase(values),
                    date=datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    unix=int(datetime.now().timestamp()),
                )
                session.add(purchase)
                created = True
    delivered = await _deliver(user_id, values) if created else None
    return {"receipt": purchase.receipt, "items": public_items(purchase),
            "delivery_status": "sent" if delivered else "not_sent" if created else "already_purchased"}


async def redeliver_purchase(user_id: int, receipt: str) -> bool:
    async with models.async_session() as session:
        purchase = await session.scalar(select(models.Purchase).where(
            models.Purchase.user_id == user_id, models.Purchase.receipt == receipt,
        ))
    if purchase is None:
        raise ShopCheckoutError("Заказ не найден", 404)
    values = item_content.decode_purchase(purchase.item)
    if values is None:
        values = [purchase.item or ""]
    return await _deliver(user_id, values)
