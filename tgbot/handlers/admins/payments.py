from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tgbot.states.adminStates import AdminMainSettings
from tgbot.utils import payments, utils
from tgbot.utils.menu import safe_edit_text
from tgbot.data.config import BotButtons, BotConfig, DB
from tgbot.data.config import BotTexts as BTs
from tgbot.data.loader import adminRouter

from traceback import print_exc
from datetime import datetime 
from AsyncPayments.lolz import AsyncLolzteamMarketPayment
from AsyncPayments.aaio import AsyncAaio
from AsyncPayments.cryptoBot import AsyncCryptoBot
from AsyncPayments.cryptomus import AsyncCryptomus

async def initPayments():
    paymentConfig = await DB.get_payments_config()
    lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket = None, None, None, None, None, None, None
    try:
        try:
            lolz = AsyncLolzteamMarketPayment(paymentConfig.get('lolz_token', ''))
        except ValueError:
            pass
        except AttributeError:
            pass
        try:
            aaio = AsyncAaio(paymentConfig.get('aaio_api_key', ''), paymentConfig.get('aaio_shop_id', ''), paymentConfig.get('aaio_secret_key_1', ''))
        except ValueError:
            pass
        try:
            cryptoBot = payments.CryptoPay(paymentConfig.get('crypto_token') or '')
        except (ValueError, Exception):
            pass
        try:
            xrocket = payments.XRocketPay(paymentConfig.get('xrocket_token') or '', paymentConfig.get('xrocket_asset') or 'USDT')
        except (ValueError, Exception):
            pass
        try:
            cryptomus = AsyncCryptomus(paymentConfig.get('payment_api_key', ''), paymentConfig.get('merchant_id', ''), "None")
        except:
            pass
        try:
            lava = payments.Lava(paymentConfig.get('lava_project_id', ''), paymentConfig.get('lava_secret_key', ''))
        except:
            pass
        try:
            yoomoney = payments.YooMoney(paymentConfig.get('yoomoney_token', ''), paymentConfig.get('yoomoney_number', ''))
        except:
            pass
    except Exception:
        print("Error with init payments: ")
        print_exc()
    return lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket


def _payment_attr(value, *names, default=None):
    for name in names:
        if isinstance(value, dict) and value.get(name) is not None:
            return value[name]
        attr = getattr(value, name, None)
        if attr is not None:
            return attr
    return default


async def _custom_pay_preview_text(BotTexts, settings):
    card = await DB.get_random_custom_pay_card()
    if not card:
        details = getattr(BotTexts.TEXTS, "custom_pay_no_cards", settings.custom_pay_method_text)
    else:
        note = f"\n<b>Նշում՝</b> {card.note}" if card.note else ""
        details = getattr(
            BotTexts.TEXTS,
            "custom_pay_transfer_details",
            "<b>🏦 Փոխանցման տվյալներ</b>\n\n<b>Բանկ՝</b> <code>{bank}</code>\n<b>Ստացող՝</b> <code>{holder}</code>\n<b>Քարտ՝</b> <code>{number}</code>{note}\n\nՓոխանցումից հետո սեղմեք ստուգման կոճակը։",
        ).format(bank=card.bank_name, holder=card.holder_name, number=card.card_number, note=note)
    return BotTexts.TEXTS.create_refill_text_custom_pay_method.format(
        paymentMethod=settings.custom_pay_method,
        pay_amount=100,
        curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        pay_id="123456789",
        under_date=datetime.fromtimestamp(utils.get_unix()).strftime("%d.%m.%Y %H:%M:%S"),
        custom_pay_method_text=details,
    )


async def _custom_pay_info_text(BotTexts):
    settings = await DB.get_settings()
    return BotTexts.ADMIN_TEXTS.payment_info_custom_pay_method.format(
        method=settings.custom_pay_method,
        preview_refill=await _custom_pay_preview_text(BotTexts, settings),
        min=settings.custom_pay_method_min_amount,
        curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        status=BotTexts.ADMIN_TEXTS.payments_on_off[settings.is_custom_pay_method_on],
    )


def _format_custom_card(BotTexts, card):
    note = card.note if card.note else "-"
    return BotTexts.ADMIN_TEXTS.custom_pay_card_text.format(
        card_id=card.card_id,
        bank=card.bank_name,
        holder=card.holder_name,
        number=card.card_number,
        note=note,
        status="ON" if card.is_active else "OFF",
    )


@adminRouter.callback_query(F.data == "payments")
async def open_payments_menu(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_payment, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.payments_settings(BotTexts, await DB.get_payments())).as_markup())
    

@adminRouter.callback_query(F.data.startswith("payments:"))
async def payment_info_open(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    method = call.data.split(":")[1]
    if method == "custom_pay_method":
        settings = await DB.get_settings()
        return await safe_edit_text(call.message, await _custom_pay_info_text(BotTexts),
                                 reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, method, settings.is_custom_pay_method_on, settings.is_custom_pay_method_receipt_on).as_markup())
    payments = await DB.get_payments()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.payment_info.format(
        method=BotTexts.TEXTS.payments_names[method],
        status=BotTexts.ADMIN_TEXTS.payments_on_off[payments[method]]),
                                 reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, method, payments[method]).as_markup())


@adminRouter.callback_query(F.data == "custom_pay_cards")
async def custom_pay_cards_open(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    cards = await DB.get_custom_pay_cards()
    if cards:
        rows = [
            f"{'✅' if card.is_active else '❌'} #{card.card_id} · <code>{card.bank_name}</code> · <code>{card.holder_name}</code>"
            for card in cards
        ]
        text = BotTexts.ADMIN_TEXTS.custom_pay_cards_text.format(cards="\n".join(rows))
    else:
        text = BotTexts.ADMIN_TEXTS.custom_pay_cards_empty
    await safe_edit_text(
        call.message,
        text,
        reply_markup=BotButtons.ADMIN_INLINE.custom_pay_cards(BotTexts, cards).as_markup(),
    )


@adminRouter.callback_query(F.data.startswith("custom_pay_card:"))
async def custom_pay_card_action(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    parts = call.data.split(":")
    action = parts[1]
    if action == "add":
        await state.set_state(AdminMainSettings.enter_custom_pay_card)
        await state.update_data(card_id=None)
        return await safe_edit_text(
            call.message,
            BotTexts.ADMIN_TEXTS.enter_custom_pay_card,
            reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "custom_pay_cards").as_markup(),
        )
    card_id = int(parts[2])
    card = await DB.get_custom_pay_card(card_id)
    if not card:
        return await call.answer(BotTexts.TEXTS.incorrect_data, show_alert=True)
    if action == "view":
        return await safe_edit_text(
            call.message,
            _format_custom_card(BotTexts, card),
            reply_markup=BotButtons.ADMIN_INLINE.custom_pay_card_manage(BotTexts, card).as_markup(),
        )
    if action == "edit":
        await state.set_state(AdminMainSettings.enter_custom_pay_card)
        await state.update_data(card_id=card_id)
        return await safe_edit_text(
            call.message,
            BotTexts.ADMIN_TEXTS.enter_custom_pay_card,
            reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, f"custom_pay_card:view:{card_id}").as_markup(),
        )
    if action == "toggle":
        await DB.toggle_custom_pay_card(card_id)
        card = await DB.get_custom_pay_card(card_id)
        return await safe_edit_text(
            call.message,
            _format_custom_card(BotTexts, card),
            reply_markup=BotButtons.ADMIN_INLINE.custom_pay_card_manage(BotTexts, card).as_markup(),
        )
    if action == "delete":
        await DB.delete_custom_pay_card(card_id)
        cards = await DB.get_custom_pay_cards()
        return await safe_edit_text(
            call.message,
            BotTexts.ADMIN_TEXTS.custom_pay_card_deleted,
            reply_markup=BotButtons.ADMIN_INLINE.custom_pay_cards(BotTexts, cards).as_markup(),
        )


@adminRouter.callback_query(F.data.startswith("payment_action:"))
async def payment_actions(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    try:
        _, method, action, field = call.data.split(":")
    except ValueError:
        _, method, action = call.data.split(":")
    payments = await DB.get_payments()
    settings = await DB.get_settings()
    match action:
        case "rate":
            await safe_edit_text(
                call.message,
                BotTexts.ADMIN_TEXTS.stars_rate_text.format(rate=settings.stars_amd_per_star),
                reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "payments:stars").as_markup(),
            )
            await state.set_state(AdminMainSettings.enter_stars_rate)
        case "name":
            await safe_edit_text(call.message, 
                BotTexts.ADMIN_TEXTS.enter_new_name_for_custom_pay_method.format(name=settings.custom_pay_method),
                reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "payments:custom_pay_method").as_markup()
            )
            await state.set_state(AdminMainSettings.enter_new_value_custom_pay_method)
            await state.update_data(action="name")
        case "text":
            await safe_edit_text(call.message, 
                BotTexts.ADMIN_TEXTS.enter_new_text_for_custom_pay_method.format(text=settings.custom_pay_method_text),
                reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "payments:custom_pay_method").as_markup()
            )
            await state.set_state(AdminMainSettings.enter_new_value_custom_pay_method)
            await state.update_data(action="text")
        case "min":
            await safe_edit_text(call.message, 
                BotTexts.ADMIN_TEXTS.enter_new_min_for_custom_pay_method.format(min=settings.custom_pay_method_min_amount, 
                                                                                curr=BotConfig.CURRENCIES[settings.currency.value]['sign']),
                reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "payments:custom_pay_method").as_markup()
            )
            await state.set_state(AdminMainSettings.enter_new_value_custom_pay_method)
            await state.update_data(action="min")
        case "receipt":
            new_status = False if settings.is_custom_pay_method_receipt_on else True
            await DB.update_settings(is_custom_pay_method_receipt_on=new_status)
            return await safe_edit_text(call.message, await _custom_pay_info_text(BotTexts),
                                                reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, method, settings.is_custom_pay_method_on, new_status).as_markup())
        case "enable_or_disable":
            if method == "custom_pay_method":
                new_status = False if settings.is_custom_pay_method_on else True
                await DB.update_settings(is_custom_pay_method_on=new_status)
                return await safe_edit_text(call.message, await _custom_pay_info_text(BotTexts),
                            reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, method, new_status, settings.is_custom_pay_method_receipt_on).as_markup())
            payments.pop("custom_pay_method")
            new_payments = payments
            new_payments[method] = False if payments[method] else True
            await DB.update_payment(**new_payments)
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.payment_info.format(
                method=BotTexts.TEXTS.payments_names[method], 
                status=BotTexts.ADMIN_TEXTS.payments_on_off[new_payments[method]]),
                                         reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, method, new_payments[method]).as_markup())
        case "balance":
            lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket = await initPayments()
            balance = ""
            try:
                match method:
                    case "lolz":
                        info = await lolz.get_me()
                        balance = f"<b><code>{info.balance}₽</code> (<code>{info.hold}₽</code>)</b>"
                    case "aaio":
                        info = await aaio.get_balance()
                        balance = f"<b><code>{info.balance}₽</code> (<code>{info.hold}₽</code>)</b>"
                    case "yoomoney":
                        balance = yoomoney.get_balance()
                    case "lava":
                        info = await lava.get_balance()
                        balance = f"<b>{info['data']['balance']+info['data']['freeze_balance']}₽</code> (<code>{info['data']['freeze_balance']}₽</code></b>)"
                    case "cryptoBot":
                        if cryptoBot is None:
                            return await call.answer(BotTexts.ADMIN_TEXTS.get_balance_error)
                        info = await cryptoBot.get_balance()
                        for bal in info:
                            currency_code = _payment_attr(bal, "currency_code", "currency", "asset", default="UNKNOWN")
                            available = _payment_attr(bal, "available", "balance", "amount", default=0)
                            balance += f"<b>{currency_code}: <code>{round(float(available), 2)} {currency_code}</code></b>\n"
                        if not balance:
                            balance = "<b><code>0</code></b>"
                    case "xrocket":
                        if xrocket is None:
                            return await call.answer(BotTexts.ADMIN_TEXTS.get_balance_error)
                        info = await xrocket.get_balance()
                        for bal in info:
                            currency_code = _payment_attr(bal, "currency_code", "currency", "asset", default="UNKNOWN")
                            available = _payment_attr(bal, "available", "balance", "amount", default=0)
                            balance += f"<b>{currency_code}: <code>{round(float(available), 2)} {currency_code}</code></b>\n"
                        if not balance:
                            balance = "<b><code>0</code></b>"
                    case "cryptomus":
                        info = await cryptomus.get_balance()
                        balance += "Merchant:\n"
                        for bal in info.merchant:
                            balance += f"<b>{bal.currency_code}: <code>{bal.balance} {bal.currency_code}</code></b> ({bal.balance_usd}$)"
                        balance += "User:\n"
                        for bal in info.user:
                            balance += f"<b>{bal.currency_code}: <code>{bal.balance} {bal.currency_code}</code></b> ({bal.balance_usd}$)"
            except:
                return await call.answer(BotTexts.ADMIN_TEXTS.get_balance_error)
                        
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.balance_info.format(
                method=BotTexts.TEXTS.payments_names[method],
                balance=balance,
            ), reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, f"payments:{method}").as_markup())
        case "info":
            payment_config = await DB.get_config_for_payment(method)
            text = ""
            for cfg in payment_config:
                text += f"<b>{cfg.text}: <code>{cfg.value}</code></b> \n"

            refills_for_day, refills_for_week, refills_for_month, refills_for_all_time, refills_count_for_day, refills_count_for_week, refills_count_for_month, refills_count_for_all_time = await DB.get_payment_method_stats(method)
            
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.payment_information_text.format(
                method=BotTexts.TEXTS.payments_names[method], 
                configs=text,
                refills_count_for_day=refills_count_for_day,
                refills_count_for_week=refills_count_for_week,
                refills_count_for_month=refills_count_for_month,
                refills_count_for_all_time=refills_count_for_all_time,
                refills_for_day=refills_for_day,
                refills_for_week=refills_for_week,
                refills_for_month=refills_for_month,
                refills_for_all_time=refills_for_all_time,
                curr=BotConfig.CURRENCIES[(await DB.get_settings()).currency.value]['sign']
                ),
                reply_markup=BotButtons.ADMIN_INLINE.payments_info(BotTexts, payment_config, method).as_markup())
        case "edit_cfg":
            await state.set_state(AdminMainSettings.enter_new_value_payment)
            await state.update_data(field=field, method=method)
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_new_value_for.format(field=field),
                                         reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, f"payment_action:{method}:info").as_markup())


@adminRouter.message(StateFilter(AdminMainSettings.enter_custom_pay_card), F.text)
async def enter_custom_pay_card(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = await state.get_data()
    lines = [line.strip() for line in msg.html_text.splitlines() if line.strip()]
    if len(lines) < 3:
        return await msg.answer(BotTexts.ADMIN_TEXTS.custom_pay_card_bad_format)
    bank_name, holder_name, card_number = lines[:3]
    note = "\n".join(lines[3:]) if len(lines) > 3 else ""
    card_id = data.get("card_id")
    if card_id:
        await DB.update_custom_pay_card(
            card_id,
            bank_name=bank_name,
            holder_name=holder_name,
            card_number=card_number,
            note=note,
        )
    else:
        card_id = await DB.add_custom_pay_card(bank_name, holder_name, card_number, note)
    await state.clear()
    card = await DB.get_custom_pay_card(card_id)
    await msg.answer(
        BotTexts.ADMIN_TEXTS.custom_pay_card_saved,
        reply_markup=BotButtons.ADMIN_INLINE.custom_pay_card_manage(BotTexts, card).as_markup(),
    )
    await msg.answer(_format_custom_card(BotTexts, card))


@adminRouter.message(StateFilter(AdminMainSettings.enter_new_value_custom_pay_method))
async def enter_new_value_custom_pay_method(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    action = (await state.get_data())['action']
    if action == "min" and (not msg.text.isdigit() or not msg.text.replace(".", "").isdigit()):
        return await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_number)
    await state.clear()
    match action:
        case "name":
            await DB.update_settings(custom_pay_method=msg.text)
        case "min":
            await DB.update_settings(custom_pay_method_min_amount=float(msg.text))
        case "text":
            await DB.update_settings(custom_pay_method_text=msg.html_text)
    settings = await DB.get_settings()
    await msg.answer(await _custom_pay_info_text(BotTexts),
                     reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(BotTexts, "custom_pay_method", settings.is_custom_pay_method_on, settings.is_custom_pay_method_receipt_on).as_markup())


@adminRouter.message(StateFilter(AdminMainSettings.enter_new_value_payment))
async def enter_new_value_payment(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = await state.get_data()
    field, method = data['field'], data['method']
    await state.clear()
    await DB.update_payment_config(field, msg.text)
    await msg.reply(BotTexts.ADMIN_TEXTS.success)
    payment_config = await DB.get_config_for_payment(method)
    text = ""
    for cfg in payment_config:
        text += f"<b>{cfg.text}: <code>{cfg.value}</code></b> \n"

    refills_for_day, refills_for_week, refills_for_month, refills_for_all_time, refills_count_for_day, refills_count_for_week, refills_count_for_month, refills_count_for_all_time = await DB.get_payment_method_stats(method)
            
    await msg.answer(BotTexts.ADMIN_TEXTS.payment_information_text.format(
        method=BotTexts.TEXTS.payments_names[method], 
        configs=text,
        refills_count_for_day=refills_count_for_day,
        refills_count_for_week=refills_count_for_week,
        refills_count_for_month=refills_count_for_month,
        refills_count_for_all_time=refills_count_for_all_time,
        refills_for_day=refills_for_day,
        refills_for_week=refills_for_week,
        refills_for_month=refills_for_month,
        refills_for_all_time=refills_for_all_time,
        curr=BotConfig.CURRENCIES[(await DB.get_settings()).currency.value]['sign']
        ),
                    reply_markup=BotButtons.ADMIN_INLINE.payments_info(BotTexts, payment_config, method).as_markup())


@adminRouter.message(StateFilter(AdminMainSettings.enter_stars_rate))
async def enter_stars_rate(msg: Message, state: FSMContext, BotTexts: BTs.Ru):
    try:
        rate = float(msg.text.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except (AttributeError, ValueError):
        return await msg.answer(BotTexts.ADMIN_TEXTS.value_is_no_number)
    await DB.update_settings(stars_amd_per_star=rate)
    await state.clear()
    payments = await DB.get_payments()
    await msg.answer(
        BotTexts.ADMIN_TEXTS.payment_info.format(
            method=BotTexts.TEXTS.payments_names["stars"],
            status=BotTexts.ADMIN_TEXTS.payments_on_off[payments["stars"]],
        ),
        reply_markup=BotButtons.ADMIN_INLINE.payments_settings_info(
            BotTexts, "stars", payments["stars"]
        ).as_markup(),
    )


