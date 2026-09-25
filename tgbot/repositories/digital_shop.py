from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select, text

from tgbot.utils import models


class DigitalShopRepository:
    async def product_enabled(self, product: str) -> bool:
        from tgbot.data.config import BotConfig
        if product not in {"stars", "premium", "gift"} or not BotConfig.DIGITAL_SHOP_ENABLED:
            return False
        field = "GIFTS" if product == "gift" else product.upper()
        default = "true" if getattr(BotConfig, f"DIGITAL_{field}_ENABLED") else "false"
        return (await self.get_setting(f"{product}_enabled", default)).lower() == "true"

    async def set_stars_enabled(self, enabled: bool, actor_id: int):
        from sqlalchemy.dialects.postgresql import insert
        from tgbot.data.config import BotConfig
        if actor_id not in BotConfig.ADMINS:
            raise PermissionError("Administrator required")
        async with models.async_session() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(724901, 1)"))
            previous = await session.scalar(select(models.DigitalSetting.value).where(
                models.DigitalSetting.key == "stars_enabled"))
            value = "true" if enabled else "false"
            statement = insert(models.DigitalSetting).values(
                key="stars_enabled", value=value, is_secret=False, updated_by=actor_id)
            await session.execute(statement.on_conflict_do_update(
                index_elements=[models.DigitalSetting.key],
                set_={"value": value, "updated_by": actor_id, "updated_at": func.now()},
            ))
            session.add(models.DigitalAuditLog(
                actor_id=actor_id, action="stars_availability", entity_type="digital_setting",
                entity_id="stars_enabled", before_data={"value": previous}, after_data={"value": value},
            ))

    async def get_setting(self, key: str, default: str = "") -> str:
        async with models.async_session() as session:
            value = await session.scalar(select(models.DigitalSetting.value).where(models.DigitalSetting.key == key))
            return default if value is None else str(value)

    async def set_setting(self, key: str, value: str, actor_id: int, *, secret: bool = False):
        from sqlalchemy.dialects.postgresql import insert
        stmt = insert(models.DigitalSetting).values(key=key, value=value, is_secret=secret, updated_by=actor_id)
        stmt = stmt.on_conflict_do_update(index_elements=[models.DigitalSetting.key], set_={
            "value": value, "is_secret": secret, "updated_by": actor_id, "updated_at": func.now(),
        })
        async with models.async_session() as session, session.begin():
            await session.execute(stmt)

    async def fulfillment_mode(self, product: str) -> str:
        if product not in {"stars", "premium"}:
            raise ValueError("Unsupported product")
        value = await self.get_setting(f"{product}_fulfillment_mode", "manual")
        return value if value in {"manual", "auto"} else "manual"

    async def create_balance_order(self, *, user_id: int, product_type: str, recipient: str, quantity: int,
                                   base_amount: Decimal, markup_percent: Decimal,
                                   markup_amount: Decimal, total_amount: Decimal,
                                   charge_by_currency: dict[str, float], mode: str) -> models.DigitalOrder:
        if product_type not in {"stars", "premium"}:
            raise ValueError("Unsupported product")
        if mode not in {"manual", "auto"}:
            raise ValueError("Unsupported fulfillment mode")
        now = datetime.utcnow()
        async with models.async_session() as session, session.begin():
            from tgbot.data.config import BotConfig
            if not BotConfig.DIGITAL_SHOP_ENABLED:
                raise ValueError("Цифровой магазин отключён")
            if product_type == "stars":
                await session.execute(text("SELECT pg_advisory_xact_lock(724901, 1)"))
            enabled = await session.scalar(select(models.DigitalSetting.value).where(
                models.DigitalSetting.key == f"{product_type}_enabled"))
            default = getattr(BotConfig, f"DIGITAL_{product_type.upper()}_ENABLED")
            if not (default if enabled is None else enabled.lower() == "true"):
                raise ValueError("Продажа этого товара отключена администратором")
            user = await session.scalar(
                select(models.User).where(models.User.user_id == user_id).with_for_update()
            )
            if user is None or user.is_ban:
                raise ValueError("Пользователь недоступен")
            for code, charge in charge_by_currency.items():
                field = f"balance_{code}"
                balance = round(float(getattr(user, field) or 0), 2)
                if balance < round(float(charge), 2):
                    raise ValueError("Недостаточно средств на балансе")
            for code, charge in charge_by_currency.items():
                field = f"balance_{code}"
                setattr(user, field, round(float(getattr(user, field) or 0) - round(float(charge), 2), 2))
            status = "paid" if mode == "manual" else "processing"
            order = models.DigitalOrder(
                public_id=f"D-{uuid4().hex[:16].upper()}",
                user_id=user_id,
                product_type=product_type,
                recipient=recipient,
                quantity=quantity,
                currency="RUB",
                base_amount=base_amount,
                markup_percent=markup_percent,
                markup_amount=markup_amount,
                total_amount=total_amount,
                payment_provider="balance",
                external_reference="bot_balance",
                status=status,
                idempotency_key=f"balance:{user_id}:{uuid4().hex}",
                paid_at=now,
                processing_at=now if mode == "auto" else None,
                order_metadata={"fulfillment_mode": mode, "charge_by_currency": charge_by_currency},
            )
            session.add(order)
            await session.flush()
            return order

    async def complete_manual_order(self, public_id: str, actor_id: int) -> models.DigitalOrder | None:
        async with models.async_session() as session, session.begin():
            order = await session.scalar(
                select(models.DigitalOrder).where(models.DigitalOrder.public_id == public_id).with_for_update()
            )
            if order is None or order.status not in {"paid", "fulfillment_failed"}:
                return None
            before = {"status": order.status}
            order.status = "completed"
            order.completed_at = func.now()
            order.error_code = None
            order.error_message = None
            session.add(models.DigitalAuditLog(
                actor_id=actor_id, action="manual_complete", entity_type="digital_order",
                entity_id=public_id, before_data=before, after_data={"status": "completed"},
            ))
            return order

    async def fail_manual_order(self, public_id: str, actor_id: int, reason: str = "manual_reject") -> models.DigitalOrder | None:
        async with models.async_session() as session, session.begin():
            order = await session.scalar(
                select(models.DigitalOrder).where(models.DigitalOrder.public_id == public_id).with_for_update()
            )
            if order is None or order.status not in {"paid", "processing", "fulfillment_failed"}:
                return None
            before = {"status": order.status}
            order.status = "fulfillment_failed"
            order.failed_at = func.now()
            order.error_code = reason[:64]
            order.error_message = "Manual fulfillment rejected by admin"
            session.add(models.DigitalAuditLog(
                actor_id=actor_id, action="manual_reject", entity_type="digital_order",
                entity_id=public_id, before_data=before, after_data={"status": "fulfillment_failed"},
            ))
            return order

    async def stats(self) -> dict[str, int]:
        async with models.async_session() as session:
            total = await session.scalar(select(func.count()).select_from(models.DigitalOrder))
            completed = await session.scalar(
                select(func.count()).select_from(models.DigitalOrder).where(models.DigitalOrder.status == "completed")
            )
            failed = await session.scalar(
                select(func.count()).select_from(models.DigitalOrder).where(
                    models.DigitalOrder.status == "fulfillment_failed"
                )
            )
            return {"total": int(total or 0), "completed": int(completed or 0), "failed": int(failed or 0)}

    async def list_admin_orders(self, *, errors_only: bool = False, limit: int = 20):
        statement = select(models.DigitalOrder).order_by(models.DigitalOrder.created_at.desc()).limit(max(1, min(limit, 50)))
        if errors_only:
            statement = statement.where(models.DigitalOrder.status.in_(["fulfillment_failed", "refund_pending"]))
        async with models.async_session() as session:
            return (await session.execute(statement)).scalars().all()

    async def list_user_orders(self, user_id: int, limit: int = 10):
        async with models.async_session() as session:
            result = await session.execute(
                select(models.DigitalOrder)
                .where(models.DigitalOrder.user_id == user_id)
                .order_by(models.DigitalOrder.created_at.desc())
                .limit(max(1, min(limit, 50)))
            )
            return result.scalars().all()


digital_shop_repository = DigitalShopRepository()
