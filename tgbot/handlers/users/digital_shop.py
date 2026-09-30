from tgbot.utils.catalog_emoji import catalog_name
from decimal import Decimal
from html import escape
import json
import telyx as tx

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from tgbot.data.config import BotConfig, BotTexts as BTs, DB
from tgbot.data.loader import userRouter
from tgbot.utils import utils
from tgbot.integrations.marketapp import MarketAppError, marketapp
from tgbot.repositories.digital_shop import digital_shop_repository
from tgbot.services.digital_shop.pricing import calculate_quote
from tgbot.states.digital_shop import DigitalPurchase
from tgbot.utils.digital_emoji import (
    GIFTS_MENU_EMOJI_ID,
    PREMIUM_BUY_EMOJI_ID,
    PREMIUM_EMOJI,
    STARS_BUY_EMOJI_ID,
    STARS_EMOJI,
    emoji_button,
)
from tgbot.utils.menu import edit_menu, send_menu


def telyx_button(text: str, callback_data: str, **kwargs) -> InlineKeyboardButton:
    action_icon = (tx.arrow_left if callback_data.startswith("back_") or text == "Հետ" else
                   tx.credit_card if callback_data == "digital:payment" else
                   tx.pencil if callback_data in {"digital:recipient:input", "digital:stars_custom"} else
                   tx.user if callback_data == "digital:recipient:self" else tx.package)
    return InlineKeyboardButton(**action_icon.button(text, callback_data=callback_data), **kwargs)


async def digital_home_keyboard() -> InlineKeyboardMarkup:
    rows = []
    if await digital_shop_repository.product_enabled("stars"):
        rows.append([emoji_button(text="Գնել Stars", callback_data="digital:stars", emoji_id="6181597355112932310")])
    if await digital_shop_repository.product_enabled("premium"):
        rows.append([emoji_button(text="Գնել Premium", callback_data="digital:premium", emoji_id="6181700898184503901")])
    if await digital_shop_repository.product_enabled("gift"):
        rows.append([emoji_button(text="Telegram նվերներ", callback_data="digital:gifts", emoji_id=GIFTS_MENU_EMOJI_ID)])
    rows.append([emoji_button(text="Իմ պատվերները", callback_data="digital:orders", emoji_id="6181208703522317605")])
    rows.append([telyx_button(text="Գլխավոր ընտրացանկ", callback_data="back_to_user_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


DIGITAL_HOME_TEXT = (
    f"<tg-emoji emoji-id='6181365645922281493'>⭐</tg-emoji> Գնեք <b>Telegram Stars</b> և <b>Premium</b> հատուկ, անվտանգ բաժնում։\n\n"
    "Գինը ֆիքսվում է պատվերը ստեղծելիս և վճարումից հետո չի փոխվում։\n\n"
    "<b>Ընտրեք ապրանքը՝</b>"
)


@userRouter.message(F.text.in_({"⭐ Stars & Premium", "Stars & Premium"}))
async def digital_home_message(message: Message, state: FSMContext):
    await state.clear()
    if not BotConfig.DIGITAL_SHOP_ENABLED:
        return await message.answer("Թվային խանութը ժամանակավորապես անջատված է։")
    await send_menu(message, DIGITAL_HOME_TEXT, await digital_home_keyboard(), "main")


@userRouter.message(F.web_app_data)
async def digital_webapp_data(
    message: Message,
    state: FSMContext,
    BotTexts: BTs.Ru | BTs.En | BTs.Ua,
):
    """Continue a product selected inside the Mini App in the bot checkout flow."""
    try:
        payload = json.loads(message.web_app_data.data)
        action = str(payload.get("action") or "")
        if action == "shop_open":
            position_id = int(payload["position_id"])
            settings = await DB.get_settings()
            position = await DB.get_position(pos_id=position_id)
            if not settings.is_buy or position is None:
                return await message.answer("Этот товар сейчас недоступен.")
            if not position.is_infinity and not await DB.get_items(pos_id=position_id):
                return await message.answer("Этот товар закончился.")
            price = float(getattr(position, f"price_{settings.currency.value}") or 0)
            await state.clear()
            return await message.answer(
                f"<b>{catalog_name(position)}</b>\n"
                f"Цена: <b>{price:g} {BotConfig.CURRENCIES[settings.currency.value]['sign']}</b>\n\n"
                f"{escape(position.description or '')}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [telyx_button(text="Купить", callback_data=f"buy_position:{position_id}")],
                ]),
            )
        if action == "refill":
            method = str(payload["method"])
            amount = float(payload["amount"])
            settings = await DB.get_settings()
            enabled = await DB.get_enabled_payments()
            if not settings.is_refill or method not in enabled or method not in {"cryptoBot", "stars", "custom_pay_method"}:
                return await message.answer("Этот способ пополнения отключён администратором.")
            if not 5 <= amount <= 100000:
                return await message.answer("Сумма пополнения должна быть от 5 до 100 000.")
            await state.clear()
            from tgbot.handlers.users.refill import send_crypto_refill_invoice, send_stars_refill_invoice, send_custom_refill_invoice

            sender = send_stars_refill_invoice if method == "stars" else send_custom_refill_invoice if method == "custom_pay_method" else send_crypto_refill_invoice
            return await sender(message, BotTexts, f"{amount:g}")
        if action != "digital_select":
            raise ValueError
        product = str(payload["product"])
        quantity = int(payload["quantity"])
        if not BotConfig.DIGITAL_SHOP_ENABLED:
            return await message.answer("Stars & Premium բաժինը ժամանակավորապես անջատված է։")
        if product == "stars" and not await digital_shop_repository.product_enabled("stars"):
            return await message.answer("Stars-ի գնումը ժամանակավորապես անջատված է։")
        if product == "premium" and not await digital_shop_repository.product_enabled("premium"):
            return await message.answer("Premium-ի գնումը ժամանակավորապես անջատված է։")
        if product == "stars" and not 50 <= quantity <= 4999:
            raise ValueError
        if product == "premium" and quantity not in {3, 6, 12}:
            raise ValueError
        if product not in {"stars", "premium"}:
            raise ValueError
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return await message.answer("Չհաջողվեց կարդալ Mini App-ի ընտրությունը։ Բացեք այն նորից։")

    await state.clear()
    await state.update_data(digital_product=product, digital_quantity=quantity)
    supplied_username = str(payload.get("username") or "").strip().lstrip("@")
    recipient_mode = str(payload.get("recipient_mode") or "")
    if supplied_username and recipient_mode in {"self", "other"}:
        try:
            text = await build_confirmation(state, supplied_username)
        except (MarketAppError, ValueError):
            return await message.answer("Ստացողը չի գտնվել կամ գինը ժամանակավորապես հասանելի չէ։ Ստուգեք username-ը։")
        await state.set_state(None)
        return await message.answer(text, reply_markup=confirmation_keyboard(product))
    label = f"{quantity} Stars" if product == "stars" else f"Premium՝ {quantity} ամսով"
    await message.answer(
        f"<b>Ստացող</b>\nԴուք ընտրել եք՝ <b>{label}</b>\n\nՈ՞ւմ պետք է ուղարկվի գնումը:",
        reply_markup=recipient_keyboard("digital:stars" if product == "stars" else "digital:premium"),
    )


@userRouter.callback_query(F.data == "digital:home")
async def digital_home_callback(call: CallbackQuery, state: FSMContext):
    await state.clear()
    if not BotConfig.DIGITAL_SHOP_ENABLED:
        return await call.answer("Թվային խանութը ժամանակավորապես անջատված է", show_alert=True)
    await edit_menu(call, DIGITAL_HOME_TEXT, await digital_home_keyboard(), "main")


def product_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [telyx_button(text="Հետ", callback_data="digital:home")]
    ])


@userRouter.callback_query(F.data == "digital:stars")
async def digital_stars(call: CallbackQuery, state: FSMContext):
    if not await digital_shop_repository.product_enabled("stars"):
        await state.clear()
        return await call.answer("Stars-ի գնումը ժամանակավորապես անջատված է։", show_alert=True)
    await state.clear()
    await state.update_data(digital_product="stars")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [emoji_button(text="50 Stars", callback_data="digital:stars_amount:50", emoji_id="6181597355112932310"),
         emoji_button(text="100 Stars", callback_data="digital:stars_amount:100", emoji_id="6181597355112932310")],
        [emoji_button(text="500 Stars", callback_data="digital:stars_amount:500", emoji_id="6181597355112932310"),
         emoji_button(text="Իմ քանակը", callback_data="digital:stars_custom", emoji_id="6183790833565705068")],
        [telyx_button(text="Հետ", callback_data="digital:home")],
    ])
    await edit_menu(
        call,
        f"<tg-emoji emoji-id='6181597355112932310'>⭐</tg-emoji> Գնեք <b>Telegram Stars</b> Ընտրեք քանակը կամ մուտքագրեք ձեր տարբերակը։\n\n"
        "Նվազագույնը՝ 50 <tg-emoji emoji-id='6181597355112932310'>⭐</tg-emoji>\nԱռավելագույնը՝ 4,999 <tg-emoji emoji-id='6181597355112932310'>⭐</tg-emoji>",
        keyboard, "main",
    )


@userRouter.callback_query(F.data == "digital:premium")
async def digital_premium(call: CallbackQuery, state: FSMContext):
    if not await digital_shop_repository.product_enabled("premium"):
        await state.clear()
        return await call.answer("Premium-ի գնումը ժամանակավորապես անջատված է։", show_alert=True)
    await state.clear()
    await state.update_data(digital_product="premium")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [emoji_button(text="3 ամիս", callback_data="digital:premium_period:3", emoji_id="6181389547415282170")],
        [emoji_button(text="6 ամիս", callback_data="digital:premium_period:6", emoji_id="6181713619877634683")],
        [emoji_button(text="12 ամիս", callback_data="digital:premium_period:12", emoji_id="6181253951002780793")],
        [telyx_button(text="Հետ", callback_data="digital:home")],
    ])
    await edit_menu(
        call,
        f"<tg-emoji emoji-id='6181700898184503901'>⭐</tg-emoji> <b>Telegram Premium</b> Ընտրեք բաժանորդագրության ժամկետը։\n\n"
        "Վերջնական գինը կհաշվարկվի ստացողին հաստատելուց հետո։",
        keyboard, "main",
    )


def recipient_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [emoji_button(text="Գնել ինձ համար", callback_data="digital:recipient:self", emoji_id="6181512409249750964")],
        [emoji_button(text="Մուտքագրել username", callback_data="digital:recipient:input", emoji_id="6181440610281464581")],
        [telyx_button(text="Հետ", callback_data=back_callback)],
    ])


async def show_recipient_step(call: CallbackQuery, state: FSMContext, product: str, quantity: int):
    if not await digital_shop_repository.product_enabled(product):
        await state.clear()
        return await call.answer("Ապրանքն անջատված է", show_alert=True)
    await state.update_data(digital_product=product, digital_quantity=quantity)
    back = "digital:stars" if product == "stars" else "digital:premium"
    label = f"{quantity} Stars" if product == "stars" else f"Premium՝ {quantity} ամսով"
    await edit_menu(
        call,
        f"<b>Ստացող</b>\nԴուք ընտրել եք՝ <b>{label}</b>\n\nՈ՞ւմ պետք է ուղարկվի գնումը:",
        recipient_keyboard(back), "main",
    )


@userRouter.callback_query(F.data.startswith("digital:stars_amount:"))
async def digital_stars_amount(call: CallbackQuery, state: FSMContext):
    amount = int(call.data.rsplit(":", 1)[1])
    if amount not in {50, 100, 500}:
        return await call.answer("Անվավեր քանակ", show_alert=True)
    await show_recipient_step(call, state, "stars", amount)


@userRouter.callback_query(F.data == "digital:stars_custom")
async def digital_stars_custom(call: CallbackQuery, state: FSMContext):
    if not await digital_shop_repository.product_enabled("stars"):
        await state.clear()
        return await call.answer("Stars-ի գնումը ժամանակավորապես անջատված է։", show_alert=True)
    await state.set_state(DigitalPurchase.stars_amount)
    await edit_menu(
        call,
        f"{STARS_EMOJI} Աստղերի իմ քանակը\n\nՈւղարկեք <b>50</b>-ից <b>4 999</b> միջակայքում գտնվող ամբողջ թիվ։",
        product_keyboard(), "main",
    )


@userRouter.message(DigitalPurchase.stars_amount)
async def digital_stars_custom_value(message: Message, state: FSMContext):
    if not await digital_shop_repository.product_enabled("stars"):
        await state.clear()
        return await message.answer("Stars-ի գնումը ժամանակավորապես անջատված է։")
    raw = (message.text or "").replace(" ", "").strip()
    if not raw.isdigit() or not 50 <= int(raw) <= 4999:
        return await message.answer("Մուտքագրեք 50-ից 4 999 միջակայքում գտնվող ամբողջ թիվ։")
    await state.update_data(digital_product="stars", digital_quantity=int(raw))
    await state.set_state(None)
    await message.answer(
        f"<b>Ստացող</b>\nԴուք ընտրել եք՝ <b>{int(raw)} Stars</b>\n\nՈ՞ւմ պետք է ուղարկվի գնումը:",
        reply_markup=recipient_keyboard("digital:stars"),
    )


@userRouter.callback_query(F.data.startswith("digital:premium_period:"))
async def digital_premium_period(call: CallbackQuery, state: FSMContext):
    months = int(call.data.rsplit(":", 1)[1])
    if months not in {3, 6, 12}:
        return await call.answer("Անվավեր ժամկետ", show_alert=True)
    await show_recipient_step(call, state, "premium", months)


@userRouter.callback_query(F.data == "digital:recipient:input")
async def digital_recipient_input(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("digital_product") not in {"stars", "premium"} or not data.get("digital_quantity"):
        return await call.answer("Ընտրությունն այլևս վավեր չէ։ Սկսեք նորից։", show_alert=True)
    await state.set_state(DigitalPurchase.recipient)
    await edit_menu(
        call,
        "<b>Ստացող</b>\n\nՈւղարկեք Telegram username-ն առանց հղման, օրինակ՝ <code>durov</code>.",
        product_keyboard(), "main",
    )


async def build_confirmation(state: FSMContext, username: str) -> str:
    data = await state.get_data()
    product = str(data["digital_product"])
    if not await digital_shop_repository.product_enabled(product):
        raise ValueError("Ապրանքն անջատված է")
    quantity = int(data["digital_quantity"])
    clean_username = username.strip().lstrip("@")
    if len(clean_username) < 3:
        raise ValueError("Անվավեր username")
    recipient = await marketapp.recipient(product, clean_username)
    name = str(recipient.get("name") or clean_username)
    rate = await marketapp.ton_rub_rate()
    markup_default = "0" if product == "stars" else "7"
    markup = Decimal(await digital_shop_repository.get_setting(f"{product}_markup_percent", markup_default))
    if product == "stars":
        total_ton = await marketapp.stars_price_ton(quantity)
        label = f"{quantity} Stars"
    else:
        total_ton = await marketapp.premium_price_ton(quantity)
        label = f"Premium՝ {quantity} ամսով"
    quote = calculate_quote(
        product_type=product,
        quantity=quantity,
        unit_price=(total_ton * rate / Decimal(quantity)),
        markup_percent=markup,
    )
    mode = await digital_shop_repository.fulfillment_mode(product)
    await state.update_data(
        digital_fulfillment_mode=mode,
        digital_recipient=clean_username,
        digital_recipient_name=name,
        digital_base_amount=str(quote.base_amount),
        digital_markup_percent=str(quote.markup_percent),
        digital_total_amount=str(quote.total_amount),
    )
    return (
        "<b>✅ Գնման հաստատում</b>\n\n"
        f"Ապրանք՝ <b>{label}</b>\n"
        f"Առաքում՝ {'ավտոմատ' if mode == 'auto' else 'ձեռքով՝ ադմինիստրատորի կողմից'}\n"
        f"Ստացող՝ <b>{escape(name)}</b> (@{escape(clean_username)})\n"
        f"Հիմնական գին՝ <b>{quote.base_amount:.2f} ₽</b>\n"
        f"Հավելավճար՝ <b>{quote.markup_percent:g}%</b>\n"
        f"Վճարման ենթակա՝ <b>{quote.total_amount:.2f} ₽</b>\n\n"
        "<i>Վճարումը կհանվի ներքին բալանսից, ձեռքով ռեժիմում ադմինը կփակի պատվերը։</i>"
    )


def confirmation_keyboard(product: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [telyx_button(text="Անցնել վճարմանը", callback_data="digital:payment")],
        [telyx_button(text="Փոխել ստացողին", callback_data="digital:recipient:input")],
        [telyx_button(text="Հետ", callback_data=f"digital:{product}")],
    ])


@userRouter.callback_query(F.data == "digital:recipient:self")
async def digital_recipient_self(call: CallbackQuery, state: FSMContext):
    if not call.from_user.username:
        return await call.answer("Սահմանեք username կամ մուտքագրեք ստացողին ձեռքով", show_alert=True)
    data = await state.get_data()
    product = str(data.get("digital_product") or "stars")
    await call.answer("Ստուգում ենք ստացողին և գինը…")
    try:
        text = await build_confirmation(state, call.from_user.username)
    except (MarketAppError, ValueError):
        return await call.answer("Չհաջողվեց ստուգել ստացողին կամ ստանալ գինը", show_alert=True)
    await state.set_state(None)
    await edit_menu(call, text, confirmation_keyboard(product), "main")


@userRouter.message(DigitalPurchase.recipient)
async def digital_recipient_value(message: Message, state: FSMContext):
    data = await state.get_data()
    product = str(data.get("digital_product") or "stars")
    try:
        text = await build_confirmation(state, message.text or "")
    except (MarketAppError, ValueError):
        return await message.answer("Ստացողը չի գտնվել կամ գինը ժամանակավորապես հասանելի չէ։ Ստուգեք username-ը։")
    await state.set_state(None)
    await message.answer(text, reply_markup=confirmation_keyboard(product))


@userRouter.callback_query(F.data == "digital:payment")
async def digital_payment_balance(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        product = str(data["digital_product"])
        quantity = int(data["digital_quantity"])
        recipient = str(data["digital_recipient"])
        base_amount = Decimal(str(data["digital_base_amount"]))
        markup_percent = Decimal(str(data["digital_markup_percent"]))
        total_amount = Decimal(str(data["digital_total_amount"]))
        mode = str(data.get("digital_fulfillment_mode") or await digital_shop_repository.fulfillment_mode(product))
    except (KeyError, TypeError, ValueError):
        return await call.answer("Ընտրությունը հնացել է։ Սկսեք նորից։", show_alert=True)
    if not await digital_shop_repository.product_enabled(product):
        await state.clear()
        return await call.answer("Ապրանքն անջատված է", show_alert=True)
    user = await DB.get_user(user_id=call.from_user.id)
    if user is None or user.is_ban:
        return await call.answer("Հաշիվը հասանելի չէ։", show_alert=True)
    charges = await utils.get_currency_amounts(float(total_amount), "rub")
    if any(round(float(getattr(user, f"balance_{code}") or 0), 2) < round(float(charge), 2) for code, charge in charges.items()):
        return await call.answer("Բալանսը չի բավարարում։ Լիցքավորեք հաշիվը։", show_alert=True)
    markup_amount = total_amount - base_amount
    try:
        order = await digital_shop_repository.create_balance_order(
            user_id=call.from_user.id,
            product_type=product,
            recipient=recipient,
            quantity=quantity,
            base_amount=base_amount,
            markup_percent=markup_percent,
            markup_amount=markup_amount,
            total_amount=total_amount,
            charge_by_currency={code: round(float(value), 2) for code, value in charges.items()},
            mode=mode,
        )
    except ValueError as exc:
        return await call.answer(str(exc), show_alert=True)
    await state.clear()
    label = f"{quantity} Stars" if product == "stars" else f"Premium՝ {quantity} ամսով"
    await call.message.answer(
        f"<b>Պատվերը ստեղծված է</b>\n\nID՝ <code>{escape(order.public_id)}</code>\n"
        f"Ապրանք՝ <b>{label}</b>\nՍտացող՝ @{escape(recipient)}\n"
        f"Վճարված է բալանսից՝ <b>{total_amount:.2f} ₽</b>\n"
        f"Կարգավիճակ՝ <b>{'ձեռքով հաստատում' if mode == 'manual' else 'մշակվում է'}</b>"
    )
    if BotConfig.ADMINS:
        from tgbot.data.loader import bot
        admin_text = (
            f"<b>🛠 Ձեռքով выдача Stars/Premium</b>\n\n"
            f"ID: <code>{escape(order.public_id)}</code>\n"
            f"User: <a href='tg://user?id={call.from_user.id}'>{escape(call.from_user.full_name)}</a>\n"
            f"Product: <b>{escape(label)}</b>\n"
            f"Recipient: @{escape(recipient)}\n"
            f"Paid: <b>{total_amount:.2f} ₽</b>\n"
            f"Balance checked and charged."
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Выдано", callback_data=f"digital_manual:complete:{order.public_id}"),
            InlineKeyboardButton(text="❌ Ошибка", callback_data=f"digital_manual:fail:{order.public_id}"),
        ]])
        await bot.send_message(BotConfig.LOGS_CHANNEL or BotConfig.ADMINS[0], admin_text, reply_markup=markup)


@userRouter.callback_query(F.data == "digital:gifts")
async def digital_gifts(call: CallbackQuery):
    await call.answer("Նվերների բաժինը շուտով հասանելի կլինի", show_alert=True)


@userRouter.callback_query(F.data == "digital:orders")
async def digital_orders(call: CallbackQuery):
    orders = await digital_shop_repository.list_user_orders(call.from_user.id)
    if not orders:
        text = "<b>Իմ պատվերները</b>\n\nՊատվերներ դեռ չկան։"
    else:
        lines = ["<b>Իմ պատվերները</b>", ""]
        for order in orders:
            lines.append(
                f"<code>{order.public_id}</code> · {order.product_type} · "
                f"{order.quantity:g} · <b>{order.status}</b>"
            )
        text = "\n".join(lines)
    await edit_menu(call, text, product_keyboard(), "main")

