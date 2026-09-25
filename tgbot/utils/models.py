from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import (
    BigInteger, String, Boolean, Integer, Enum, Float, Column,
    Numeric, DateTime, JSON, ForeignKey, UniqueConstraint, func,
)
from sqlalchemy import select, insert, text
from sqlalchemy.engine import URL, make_url

from tgbot.data.config import BotConfig

import enum
import time

# Инициализация асинхронного движка
database_url = make_url(BotConfig.DATABASE_URL) if BotConfig.DATABASE_URL else URL.create(
    "postgresql+asyncpg",
    username=BotConfig.DATABASE_USERNAME,
    password=BotConfig.DATABASE_PASSWORD,
    host=BotConfig.DATABASE_HOST,
    port=BotConfig.DATABASE_PORT,
    database=BotConfig.DATABASE_NAME,
)
if database_url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
    raise ValueError("DATABASE_URL must reference PostgreSQL")
engine = create_async_engine(database_url.set(drivername="postgresql+asyncpg"), pool_pre_ping=True)

# Создаем асинхронный фабричный метод для сессий
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Currencies(enum.Enum):
    rub = "rub"
    usd = "usd"
    eur = "eur"
    amd = "amd"
    

class Languages(enum.Enum):
    ru = "ru"
    en = "en"
    ua = "ua"


class Keyboards(enum.Enum):
    Reply = "Reply"
    Inline = "Inline"


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    is_ban = Column(Boolean, default=False)
    user_name = Column(String)
    full_name = Column(String)
    balance_rub = Column(Float, default=0)
    balance_usd = Column(Float, default=0)
    balance_eur = Column(Float, default=0)
    balance_amd = Column(Float, default=0)
    language: Mapped[Languages] = Column(Enum(Languages), default=Languages.ru)
    total_refill = Column(Float, default=0)
    count_refills = Column(Integer, default=0)
    reg_date = Column(String)
    reg_date_unix = Column(BigInteger)
    ref_lvl = Column(Integer, default=1)
    ref_id = Column(BigInteger)
    ref_user_name = Column(String)
    ref_full_name = Column(String)
    ref_count = Column(Integer, default=0)
    ref_earn_rub = Column(Float, default=0)
    ref_earn_usd = Column(Float, default=0)
    ref_earn_eur = Column(Float, default=0)
    ref_earn_amd = Column(Float, default=0)


class Settings(Base):
    __tablename__ = "settings"

    settings = Column(String, default="main", primary_key=True)
    is_work = Column(Boolean, default=True)
    is_refill = Column(Boolean, default=False)
    is_buy = Column(Boolean, default=False)
    is_ref = Column(Boolean, default=False)
    is_notify = Column(Boolean, default=True)
    is_sub = Column(Boolean, default=False)
    faq = Column(String)
    chat = Column(String)
    news = Column(String)
    support = Column(String)
    ref_percent_1 = Column(Float, default=0.0)
    ref_percent_2 = Column(Float, default=0.0)
    ref_percent_3 = Column(Float, default=0.0)
    ref_lvl_2 = Column(Integer, default=0)
    ref_lvl_3 = Column(Integer, default=0)
    profit_day = Column(Integer, default=0)
    profit_week = Column(Integer, default=0)
    currency: Mapped[Currencies] = Column(Enum(Currencies), default=Currencies.rub)
    keyboard: Mapped[Keyboards] = Column(Enum(Keyboards), default=Keyboards.Reply)
    multi_lang = Column(Boolean, default=True)
    default_lang: Mapped[Languages] = Column(Enum(Languages), default=Languages.ru)
    contests_is_on = Column(Boolean, default=False)
    custom_pay_method = Column(String, default="Idram/BankCard/Telcell")
    custom_pay_method_text = Column(String, default="Напишите менеджеру для оплаты через Idram / BankCard / Telcell. После перевода отправьте заявку на проверку.")
    custom_pay_method_min_amount = Column(Float, default=0.0)
    is_custom_pay_method_receipt_on = Column(Boolean, default=False)
    is_custom_pay_method_on = Column(Boolean, default=False)
    stars_amd_per_star = Column(Float, default=100.0)


class Refill(Base):
    __tablename__ = "refills"

    user_id = Column(BigInteger)
    amount = Column(Float)
    receipt = Column(String, primary_key=True)
    way = Column(String)
    date = Column(String)
    date_unix = Column(BigInteger)
    pay_url = Column(String)
    second_amount = Column(Float)
    currency = Column(Enum(Currencies))
    is_finish = Column(Boolean, default=False)
    under_date = Column(BigInteger)


class Rates(Base):
    __tablename__ = "rates"
    
    settings = Column(String, default="rates", primary_key=True)
    usd_rub = Column(Float, default=0.0)
    usd_eur = Column(Float, default=0.0)
    eur_rub = Column(Float, default=0.0)
    eur_usd = Column(Float, default=0.0)
    rub_usd = Column(Float, default=0.0)
    rub_eur = Column(Float, default=0.0)


class Purchase(Base):
    __tablename__ = "purchases"

    user_id = Column(BigInteger)
    receipt = Column(String, primary_key=True)
    count = Column(Integer)
    price_rub = Column(Float)
    price_usd = Column(Float)
    price_eur = Column(Float)
    price_amd = Column(Float)
    pos_id = Column(BigInteger)
    item = Column(String)
    date = Column(String)
    unix = Column(BigInteger)


class AdButton(Base):
    __tablename__ = "ad_buttons"

    button_id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String)
    text = Column(String)
    photo = Column(String)
    links = Column(String, default=None)


class MenuBanner(Base):
    __tablename__ = "menu_banners"

    menu_key = Column(String(64), primary_key=True)
    photo_url = Column(String(2048), nullable=False)


class Position(Base):
    __tablename__ = "positions"

    pos_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String)
    price_rub  = Column(Float)
    price_usd  = Column(Float)
    price_eur  = Column(Float)
    price_amd  = Column(Float)
    description = Column(String)
    photo = Column(String)
    cat_id = Column(BigInteger)
    sub_cat_id = Column(BigInteger)
    is_infinity = Column(Boolean)
    item_type = Column(String, default="text")


class SubCategory(Base):
    __tablename__ = "sub_categories"

    sub_cat_id = Column(BigInteger, primary_key=True, autoincrement=True)
    cat_id = Column(BigInteger)
    name = Column(String)


class Promocode(Base):
    __tablename__ = "promocodes"

    name = Column(String, primary_key=True)
    uses = Column(Integer)
    discount_rub = Column(Float)
    discount_usd = Column(Float)
    discount_eur = Column(Float)
    discount_amd = Column(Float)


class PaymentConfig(Base):
    __tablename__ = "payments_config"

    payment_id = Column(String)
    text = Column(String)
    field = Column(String, primary_key=True)
    value = Column(String)


class Payment(Base):
    __tablename__ = "payments"

    settings = Column(String, default="payments", primary_key=True)
    cryptoBot = Column(Boolean, default=False)
    xrocket = Column(Boolean, default=False)
    yoomoney = Column(Boolean, default=False)
    lolz = Column(Boolean, default=False)
    lava = Column(Boolean, default=False)
    aaio = Column(Boolean, default=False)
    cryptomus = Column(Boolean, default=False)
    stars = Column(Boolean, default=False)


class CustomPayCard(Base):
    __tablename__ = "custom_pay_cards"

    card_id = Column(Integer, autoincrement=True, primary_key=True)
    bank_name = Column(String(128), nullable=False)
    holder_name = Column(String(255), nullable=False)
    card_number = Column(String(64), nullable=False)
    note = Column(String(1024), default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at_unix = Column(BigInteger, default=lambda: int(time.time()), nullable=False)


class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    channel_id = Column(BigInteger, primary_key=True)
    title = Column(String(255), nullable=False)
    invite_link = Column(String(2048), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)


class MailButton(Base):
    __tablename__ = "mail_buttons"

    button_id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String)
    button_type = Column(String)
    

class Item(Base):
    __tablename__ = "items"

    item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    data = Column(String)
    pos_id = Column(BigInteger)
    cat_id = Column(BigInteger)
    date = Column(String)
    file_id = Column(String)


class ContestsSettings(Base):
    __tablename__ = "contests_settings"

    settings = Column(String, default="main", primary_key=True)
    winners_num = Column(Integer, default=1)
    prize = Column(Float, default=100)
    purchases_num = Column(Integer, default=0)
    refills_num = Column(Integer, default=0)
    channels_ids = Column(String)
    members_num = Column(Integer, default=10)
    end_time = Column(BigInteger)


class ContestMember(Base):
    __tablename__ = "contests_members"

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer)
    user_id = Column(BigInteger)


class Contest(Base):
    __tablename__ = "contests"

    contest_id = Column(Integer, autoincrement=True, primary_key=True)
    prize = Column(Float)
    currency: Mapped[Currencies] = Column(Enum(Currencies), default=Currencies.rub)
    members_num = Column(Integer)
    end_time = Column(BigInteger)
    winners_num = Column(Integer)
    channels_ids = Column(String)
    refills_num = Column(Integer, default=0)
    purchases_num = Column(Integer, default=0)


class Category(Base):
    __tablename__ = "categories"

    cat_id = Column(BigInteger, primary_key=True)
    name = Column(String)


class ActivePromocode(Base):
    __tablename__ = "active_promocodes"

    use_id = Column(Integer, autoincrement=True, primary_key=True)
    promocode_name = Column(String, primary_key=True)
    user_id = Column(BigInteger)


class DigitalWallet(Base):
    """Stars balance owned by an existing AutoShop user."""

    __tablename__ = "digital_wallets"

    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    stars_balance = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DigitalOrder(Base):
    """Immutable-price order for Stars, Premium, or a Telegram gift."""

    __tablename__ = "digital_orders"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_digital_orders_idempotency_key"),
        UniqueConstraint("provider_invoice_id", name="uq_digital_orders_provider_invoice_id"),
    )

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    public_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    product_type = Column(String(32), nullable=False, index=True)
    recipient = Column(String(64), nullable=False)
    quantity = Column(Numeric(14, 3), nullable=False)
    currency = Column(String(8), nullable=False, default="RUB")
    base_amount = Column(Numeric(18, 4), nullable=False)
    markup_percent = Column(Numeric(8, 3), nullable=False, default=0)
    markup_amount = Column(Numeric(18, 4), nullable=False, default=0)
    total_amount = Column(Numeric(18, 4), nullable=False)
    payment_provider = Column(String(32))
    provider_invoice_id = Column(String(128))
    external_reference = Column(String(256))
    status = Column(String(32), nullable=False, default="created", index=True)
    idempotency_key = Column(String(128), nullable=False)
    fulfillment_attempts = Column(Integer, nullable=False, default=0)
    error_code = Column(String(64))
    error_message = Column(String(1000))
    order_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paid_at = Column(DateTime(timezone=True))
    processing_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))


class DigitalSetting(Base):
    __tablename__ = "digital_settings"

    key = Column(String(128), primary_key=True)
    value = Column(String(4096), nullable=False)
    is_secret = Column(Boolean, nullable=False, default=False)
    updated_by = Column(BigInteger)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DigitalLedger(Base):
    __tablename__ = "digital_ledger"

    ledger_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    operation = Column(String(64), nullable=False)
    reference = Column(String(128))
    idempotency_key = Column(String(128), unique=True, nullable=False)
    created_by = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DigitalAuditLog(Base):
    __tablename__ = "digital_audit_log"

    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128))
    before_data = Column(JSON)
    after_data = Column(JSON)
    ip_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


payments_configs = [
    {
        "payment_id": "cryptomus",
        "text": "[Cryptomus] Merchant ID",
        "field": "merchant_id"
    },
    {
        "payment_id": "cryptomus",
        "text": "[Cryptomus] API Key",
        "field": "payment_api_key"
    },
    {
        "payment_id": "cryptoBot",
        "text": "[CryptoBot] Token",
        "field": "crypto_token"
    },
    {
        "payment_id": "xrocket",
        "text": "[xRocket] API token",
        "field": "xrocket_token"
    },
    {
        "payment_id": "xrocket",
        "text": "[xRocket] Asset (USDT/TONCOIN)",
        "field": "xrocket_asset"
    },
    {
        "payment_id": "yoomoney",
        "text": "[ЮMoney] Token",
        "field": "yoomoney_token"
    },
    {
        "payment_id": "yoomoney",
        "text": "[ЮMoney] Number",
        "field": "yoomoney_number"
    },
    {
        "payment_id": "aaio",
        "text": "[Aaio] API Key",
        "field": "aaio_api_key"
    },
    {
        "payment_id": "aaio",
        "text": "[Aaio] Shop ID",
        "field": "aaio_shop_id"
    },
    {
        "payment_id": "aaio",
        "text": "[Aaio] Secret key 1",
        "field": "aaio_secret_key_1"
    },
    {
        "payment_id": "lava",
        "text": "[Lava] Project ID",
        "field": "lava_project_id"
    },
    {
        "payment_id": "lava",
        "text": "[Lava] Secret Key",
        "field": "lava_secret_key"
    },
    {
        "payment_id": "lolz",
        "text": "[Lolzteam] Merchant ID",
        "field": "lolz_merchant_id"
    },
    {
        "payment_id": "lolz",
        "text": "[Lolzteam] Token",
        "field": "lolz_token"
    },
]


async def async_main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TYPE currencies ADD VALUE IF NOT EXISTS 'amd';"))
    async with engine.begin() as conn:
        # Create all tables first
        await conn.run_sync(Base.metadata.create_all)
        
        # Then perform schema updates
        info = await conn.execute(text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'active_promocodes'"))
        if info.fetchone()[0] == 2:
            await conn.execute(text('ALTER TABLE active_promocodes DROP CONSTRAINT active_promocodes_pkey;'))
            await conn.execute(text("ALTER TABLE active_promocodes ADD COLUMN use_id SERIAL PRIMARY KEY;"))
        
        # Update payment config field name
        await conn.execute(text("UPDATE payments_config SET field = 'yoomoney_token' WHERE field = 'cryptoyoomoney_token_token';"))
        payment_column = await conn.execute(text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'payments' AND column_name = 'xrocket'"))
        if payment_column.fetchone()[0] == 0:
            await conn.execute(text('ALTER TABLE payments ADD COLUMN xrocket BOOLEAN DEFAULT false;'))
        migrations = (
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_amd DOUBLE PRECISION DEFAULT 0;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_earn_amd DOUBLE PRECISION DEFAULT 0;",
            "ALTER TABLE positions ADD COLUMN IF NOT EXISTS price_amd DOUBLE PRECISION DEFAULT 0;",
            "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS price_amd DOUBLE PRECISION DEFAULT 0;",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS discount_amd DOUBLE PRECISION DEFAULT 0;",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS stars BOOLEAN DEFAULT false;",
            "ALTER TABLE settings ADD COLUMN IF NOT EXISTS stars_amd_per_star DOUBLE PRECISION DEFAULT 100;",
            "CREATE TABLE IF NOT EXISTS custom_pay_cards ("
            "card_id SERIAL PRIMARY KEY, "
            "bank_name VARCHAR(128) NOT NULL, "
            "holder_name VARCHAR(255) NOT NULL, "
            "card_number VARCHAR(64) NOT NULL, "
            "note VARCHAR(1024) DEFAULT '', "
            "is_active BOOLEAN NOT NULL DEFAULT true, "
            "created_at_unix BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT"
            ");",
            "UPDATE settings SET custom_pay_method = 'Idram/BankCard/Telcell' "
            "WHERE custom_pay_method IS NULL OR custom_pay_method = 'Custom Pay Method';",
            "UPDATE settings SET is_sub = true "
            "WHERE EXISTS (SELECT 1 FROM mandatory_channels WHERE enabled = true);",
        )
        for statement in migrations:
            await conn.execute(text(statement))

        if len((await conn.execute(select(Rates))).scalars().all()) == 0:
            await conn.execute(insert(Rates))
        if len((await conn.execute(select(Settings))).scalars().all()) == 0:
            await conn.execute(insert(Settings).values(
                profit_day=int(time.time()),
                profit_week=int(time.time())
            ))
        existing_payment_fields = set((await conn.execute(select(PaymentConfig.field))).scalars().all())
        for paymentConfig in payments_configs:
            if paymentConfig["field"] not in existing_payment_fields:
                await conn.execute(insert(PaymentConfig).values(**paymentConfig))
        if len((await conn.execute(select(Payment))).scalars().all()) == 0:
            await conn.execute(insert(Payment).values())
        if len((await conn.execute(select(ContestsSettings))).scalars().all()) == 0:
            await conn.execute(insert(ContestsSettings).values(
                channels_ids="-",
                end_time=0,
            ))
                
        await conn.commit()

