from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import BigInteger, String, Boolean, Integer, Enum, Float, Column, insert, select
from sqlalchemy.engine import URL
import sqlite3
import asyncio
import os
import time
import enum

PATH_DATABASE = "database.db"
DATABASE_HOST = os.environ.get("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.environ.get("DATABASE_PORT", "5432"))
DATABASE_USERNAME = os.environ.get("DATABASE_USERNAME", "postgres")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "autoshop")

engine = create_async_engine(URL.create(
    "postgresql+asyncpg",
    username=DATABASE_USERNAME,
    password=DATABASE_PASSWORD,
    host=DATABASE_HOST,
    port=DATABASE_PORT,
    database=DATABASE_NAME,
))
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

BATCH_SIZE = 200

def dict_factory(cursor, row):
    save_dict = {}
    for idx, col in enumerate(cursor.description):
        save_dict[col[0]] = row[idx]
    return save_dict


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Currencies(enum.Enum):
    rub = "rub"
    usd = "usd"
    eur = "eur"


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
    ref_percent_1 = Column(Float, default=0)
    ref_percent_2 = Column(Float, default=0)
    ref_percent_3 = Column(Float, default=0)
    ref_lvl_2 = Column(Integer, default=0)
    ref_lvl_3 = Column(Integer, default=0)
    profit_day = Column(Integer, default=0)
    profit_week = Column(Integer, default=0)
    currency: Mapped[Currencies] = Column(Enum(Currencies), default=Currencies.rub)
    keyboard: Mapped[Keyboards] = Column(Enum(Keyboards), default=Keyboards.Reply)
    multi_lang = Column(Boolean, default=True)
    default_lang: Mapped[Languages] = Column(Enum(Languages), default=Languages.ru)
    contests_is_on = Column(Boolean, default=False)
    custom_pay_method = Column(String, default="Custom Pay Method")
    custom_pay_method_text = Column(String, default="Transfer to card <code>123456789</code> to top up your balance.")
    custom_pay_method_min_amount = Column(Float, default=0.0)
    is_custom_pay_method_receipt_on = Column(Boolean, default=False)
    is_custom_pay_method_on = Column(Boolean, default=False)


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


class Position(Base):
    __tablename__ = "positions"
    pos_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String)
    price_rub  = Column(Float)
    price_usd  = Column(Float)
    price_eur  = Column(Float)
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


class CustomPayCard(Base):
    __tablename__ = "custom_pay_cards"
    card_id = Column(Integer, autoincrement=True, primary_key=True)
    bank_name = Column(String(128), nullable=False)
    holder_name = Column(String(255), nullable=False)
    card_number = Column(String(64), nullable=False)
    note = Column(String(1024), default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at_unix = Column(BigInteger, default=lambda: int(time.time()), nullable=False)


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
    promocode_name = Column(String, primary_key=True)
    user_id = Column(BigInteger)
    

# ------------------ payments_configs ------------------

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
        "field": "cryptoyoomoney_token_token"
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

# ----------------- BATCH INSERT FUNCTIONS -----------------

BATCH_SIZE = 200  # Можно менять на больше/меньше по желанию

async def batch_insert(conn, table, data_list, batch_size=BATCH_SIZE, key_columns=None):
    """
    Универсальная пакетная вставка
    conn - connection object
    table - SQLAlchemy Table class
    data_list - list of dicts
    batch_size - размер батча (по сколько строк за раз)
    key_columns - если нужно ON CONFLICT DO NOTHING (например для users, active_promocodes и т.п.)
    """
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i+batch_size]
        if not batch:
            continue
        if key_columns:
            stmt = pg_insert(table).values(batch).on_conflict_do_nothing(index_elements=key_columns)
            await conn.execute(stmt)
        else:
            await conn.execute(insert(table), batch)
            
            
async def rebuild_db():
    try:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            
            cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("❌ SQLite database is empty or doesn't have migration data.")
                print("✅ PostgreSQL database will be initialized with empty tables.")
                print("   To migrate data, ensure database.db has valid data first.")
                
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    
                    # Initialize default records
                    if len((await conn.execute(select(Rates))).scalars().all()) == 0:
                        await conn.execute(insert(Rates))
                    if len((await conn.execute(select(Settings))).scalars().all()) == 0:
                        await conn.execute(insert(Settings).values(
                            is_work=True,
                            is_refill=False,
                            is_buy=False,
                            is_ref=False,
                            is_notify=True,
                            is_sub=False,
                            faq="No FAQ set",
                            chat="No chat set",
                            news="No news set",
                            support="No support set",
                            ref_percent_1=0.0,
                            ref_percent_2=0.0,
                            ref_percent_3=0.0,
                            ref_lvl_2=0,
                            ref_lvl_3=0,
                            profit_day=int(time.time()),
                            profit_week=int(time.time()),
                            currency='rub',
                            keyboard='Reply',
                            multi_lang=True,
                            default_lang='ru',
                            contests_is_on=False,
                        ))
                    
                    await conn.commit()
                
                print("✅ PostgreSQL database initialized successfully!")
                return

        users = con.execute("SELECT * FROM users").fetchall()
        settings = con.execute("SELECT * FROM settings").fetchone()
        refills = con.execute("SELECT * from refills").fetchall()
        rates = con.execute("SELECT * FROM rates").fetchone()
        purchases = con.execute("SELECT * FROM purchases").fetchall()
        pr_buttons = con.execute("SELECT * FROM pr_buttons").fetchall()
        positions = con.execute('SELECT * FROM positions').fetchall()
        pod_categories = con.execute("SELECT * FROM pod_categories").fetchall()
        payments = con.execute("SELECT * FROM payments").fetchone()
        mail_buttons = con.execute("SELECT * FROM mail_buttons").fetchall()
        items = con.execute("SELECT * FROM items").fetchall()
        coupons = con.execute("SELECT * FROM coupons").fetchall()
        contests_settings = con.execute("SELECT * FROM contests_settings").fetchone()
        contests_members = con.execute("SELECT * FROM contests_members").fetchall()
        contests = con.execute("SELECT * FROM contests").fetchall()
        categories = con.execute("SELECT * FROM categories").fetchall()
        activ_coupons = con.execute("SELECT * FROM activ_coupons").fetchall()
    except Exception:
        raise

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        print("Перенос таблицы Settings")
        await conn.execute(insert(Settings).values(
            is_work=True if settings['is_work'] == "True" else False,
            is_refill=True if settings['is_refill'] == "True" else False,
            is_buy=True if settings['is_buy'] == "True" else False,
            is_ref=True if settings['is_ref'] == "True" else False,
            is_notify=True if settings['is_notify'] == "True" else False,
            is_sub=True if settings['is_sub'] == "True" else False,
            faq=settings['faq'],
            chat=settings['chat'],
            news=settings['news'],
            support=settings['support'],
            ref_percent_1=settings['ref_percent_1'],
            ref_percent_2=settings['ref_percent_2'],
            ref_percent_3=settings['ref_percent_3'],
            ref_lvl_2=settings['ref_lvl_2'],
            ref_lvl_3=settings['ref_lvl_3'],
            profit_day=settings['profit_day'],
            profit_week=settings['profit_week'],
            currency=settings['currency'],
            keyboard=settings['keyboard'],
            multi_lang=True if settings['multi_lang'] == "True" else False,
            default_lang=settings['default_lang'],
            contests_is_on=True if settings['contests_is_on'] == "True" else False,
        ))

        print("Перенос таблицы Rates")
        await conn.execute(insert(Rates).values(**rates))
        print("Перенос таблицы ContestsSettings")
        await conn.execute(insert(ContestsSettings).values(**contests_settings))
        print("Перенос таблицы Payment")
        await conn.execute(insert(Payment).values(
            cryptoBot=True if payments['pay_crypto'] == "True" else False,
            xrocket=False,
            yoomoney=True if payments['pay_yoomoney'] == "True" else False,
            lolz=True if payments['pay_lolz'] == "True" else False,
            lava=True if payments['pay_lava'] == "True" else False,
            aaio=True if payments['pay_aaio'] == "True" else False,
        ))

        print("Перенос таблицы PaymentConfig")
        await batch_insert(conn, PaymentConfig, payments_configs, key_columns=['field'])
        print(f"[PaymentConfig] {len(payments_configs)}/{len(payments_configs)}")

        # USERS (batch with ON CONFLICT DO NOTHING)
        print(f"Перенос пользователей ({len(users)} шт.)")
        user_batch = []
        for user in users:
            user_batch.append({
                'user_id': user['id'],
                'is_ban': True if user['is_ban'] == "True" else False,
                'user_name': user['user_name'],
                'full_name': user['first_name'],
                'balance_rub': user['balance_rub'],
                'balance_usd': user['balance_dollar'],
                'balance_eur': user['balance_euro'],
                'language': user['language'],
                'total_refill': user['total_refill'],
                'count_refills': user['count_refills'],
                'reg_date': user['reg_date'],
                'reg_date_unix': user['reg_date_unix'],
                'ref_lvl': user['ref_lvl'],
                'ref_id': user['ref_id'],
                'ref_user_name': user['ref_user_name'],
                'ref_full_name': user['ref_first_name'],
                'ref_count': user['ref_count'],
                'ref_earn_rub': user['ref_earn_rub'],
                'ref_earn_usd': user['ref_earn_dollar'],
                'ref_earn_eur': user['ref_earn_euro'],
            })
        await batch_insert(conn, User, user_batch, key_columns=['user_id'])
        print(f"[users] {len(users)}/{len(users)}")

        print(f"Перенос пополнений ({len(refills)} шт.)")
        refill_batch = []
        for refill in refills:
            refill_batch.append({
                'user_id': refill['user_id'],
                'amount': refill['amount'],
                'receipt': refill['receipt'],
                'way': refill['way'],
                'date': refill['date'],
                'date_unix': refill['date_unix'],
                'pay_url': None,
                'second_amount': None,
                'currency': 'rub',
                'is_finish': True,
                'under_date': None,
            })
        await batch_insert(conn, Refill, refill_batch)
        print(f"[refills] {len(refills)}/{len(refills)}")

        print(f"Перенос покупок ({len(purchases)} шт.)")
        purchases_batch = []
        for purchase in purchases:
            purchases_batch.append({
                'user_id': purchase['user_id'],
                'receipt': purchase['receipt'],
                'count': purchase['count'],
                'price_rub': purchase['price_rub'],
                'price_usd': purchase['price_dollar'],
                'price_eur': purchase['price_euro'],
                'pos_id': purchase['position_id'],
                'item': purchase['item'],
                'date': purchase['date'],
                'unix': purchase['unix'],
            })
        await batch_insert(conn, Purchase, purchases_batch)
        print(f"[purchases] {len(purchases)}/{len(purchases)}")

        print(f"Перенос рекламных кнопок ({len(pr_buttons)} шт.)")
        pr_buttons_batch = []
        for pr_button in pr_buttons:
            pr_buttons_batch.append({
                'button_id': pr_button['id'],
                'name': pr_button['name'],
                'text': pr_button['txt'],
                'photo': pr_button['phot'],
                'links': "-",
            })
        await batch_insert(conn, AdButton, pr_buttons_batch)
        print(f"[ad_buttons] {len(pr_buttons)}/{len(pr_buttons)}")

        print(f"Перенос позиций ({len(positions)} шт.)")
        positions_batch = []
        for position in positions:
            positions_batch.append({
                'pos_id': position['id'],
                'name': position['name'],
                'price_rub': position['price_rub'],
                'price_usd': position['price_dollar'],
                'price_eur': position['price_euro'],
                'description': position['description'],
                'photo': position['photo'],
                'cat_id': position['category_id'],
                'sub_cat_id': position['pod_category_id'],
                'is_infinity': True if position['infinity'] == "True" else False,
                'item_type': position['type'],
            })
        await batch_insert(conn, Position, positions_batch)
        print(f"[positions] {len(positions)}/{len(positions)}")

        print(f"Перенос подкатегорий ({len(pod_categories)} шт.)")
        pod_categories_batch = []
        for pod_category in pod_categories:
            pod_categories_batch.append({
                'sub_cat_id': pod_category['id'],
                'cat_id': pod_category['cat_id'],
                'name': pod_category['name'],
            })
        await batch_insert(conn, SubCategory, pod_categories_batch)
        print(f"[sub_categories] {len(pod_categories)}/{len(pod_categories)}")

        print(f"Перенос почтовых кнопок ({len(mail_buttons)} шт.)")
        mail_buttons_batch = []
        for mail_button in mail_buttons:
            mail_buttons_batch.append({
                'button_id': mail_button['id'],
                'name': mail_button['name'],
                'button_type': mail_button['type'],
            })
        await batch_insert(conn, MailButton, mail_buttons_batch)
        print(f"[mail_buttons] {len(mail_buttons)}/{len(mail_buttons)}")

        print(f"Перенос items ({len(items)} шт.)")
        items_batch = []
        for item in items:
            items_batch.append({
                'item_id': item['id'],
                'data': item['data'],
                'pos_id': item['position_id'],
                'cat_id': item['category_id'],
                'date': item['date'],
                'file_id': item['file_id'],
            })
        await batch_insert(conn, Item, items_batch)
        print(f"[items] {len(items)}/{len(items)}")

        print(f"Перенос coupons ({len(coupons)} шт.)")
        coupons_batch = []
        for coupon in coupons:
            coupons_batch.append({
                'name': coupon['coupon'],
                'uses': coupon['uses'],
                'discount_rub': coupon['discount_rub'],
                'discount_usd': coupon['discount_dollar'],
                'discount_eur': coupon['discount_euro'],
            })
        await batch_insert(conn, Promocode, coupons_batch)
        print(f"[promocodes] {len(coupons)}/{len(coupons)}")

        print(f"Перенос участников конкурсов ({len(contests_members)} шт.)")
        contests_members_batch = []
        for contest_member in contests_members:
            contests_members_batch.append({
                'contest_id': contest_member['contest_id'],
                'user_id': contest_member['user_id'],
            })
        await batch_insert(conn, ContestMember, contests_members_batch)
        print(f"[contests_members] {len(contests_members)}/{len(contests_members)}")

        print(f"Перенос конкурсов ({len(contests)} шт.)")
        contests_batch = []
        for contest in contests:
            contests_batch.append({
                'contest_id': contest['id'],
                'prize': contest['prize'],
                'currency': settings['currency'],
                'members_num': contest['members_num'],
                'end_time': contest['end_time'],
                'winners_num': contest['winners_num'],
                'channels_ids': contest['channels_ids'],
                'refills_num': contest['refills_num'],
                'purchases_num': contest['purchases_num'],
            })
        await batch_insert(conn, Contest, contests_batch)
        print(f"[contests] {len(contests)}/{len(contests)}")

        print(f"Перенос категорий ({len(categories)} шт.)")
        categories_batch = []
        for category in categories:
            categories_batch.append({
                'cat_id': category['id'],
                'name': category['name'],
            })
        await batch_insert(conn, Category, categories_batch)
        print(f"[categories] {len(categories)}/{len(categories)}")

        print(f"Перенос активных купонов ({len(activ_coupons)} шт.)")
        active_promos_batch = []
        for activ_coupon in activ_coupons:
            active_promos_batch.append({
                'promocode_name': activ_coupon['coupon_name'],
                'user_id': activ_coupon['user_id'],
            })
        await batch_insert(conn, ActivePromocode, active_promos_batch, key_columns=['promocode_name'])
        print(f"[active_promocodes] {len(activ_coupons)}/{len(activ_coupons)}")

        await conn.commit()

    print("База данных успешно перенесена!")

# ---- Вызов ----
if __name__ == "__main__":
    asyncio.run(rebuild_db())
