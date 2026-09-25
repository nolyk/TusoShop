from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

from tgbot.data.loader import bot, userRouter, adminRouter
from tgbot.data.config import BotButtons, BotConfig, BotImages , DB
from tgbot.data.config import BotTexts as BTs
from tgbot.utils import utils, payments, models
from tgbot.utils.menu import edit_menu
from tgbot.states.userStates import UserRefills

from AsyncPayments.lolz import AsyncLolzteamMarketPayment
from AsyncPayments.aaio import AsyncAaio
from AsyncPayments.cryptoBot import AsyncCryptoBot
from AsyncPayments.cryptomus import AsyncCryptomus
from AsyncPayments.cryptomus.models import InvoiceStatuses
from traceback import print_exc
from datetime import datetime
from random import randint
import math


class _MessageCallbackAdapter:
    def __init__(self, message):
        self.message = message
        self.from_user = message.from_user

    async def answer(self, text, *args, **kwargs):
        return await self.message.answer(text)


def _custom_card_marker(card_id) -> str:
    return f"custom_card:{int(card_id)}"


async def _custom_pay_instruction_text(BotTexts, card_id=None):
    settings = await DB.get_settings()
    card = None
    if card_id:
        card = await DB.get_custom_pay_card(card_id)
    if not card:
        card = await DB.get_random_custom_pay_card()
    if not card:
        return None, getattr(BotTexts.TEXTS, "custom_pay_no_cards", settings.custom_pay_method_text)
    note = f"\n<b>Նշում՝</b> {card.note}" if getattr(card, "note", None) else ""
    template = getattr(
        BotTexts.TEXTS,
        "custom_pay_transfer_details",
        "<b>🏦 Փոխանցման տվյալներ</b>\n\n<b>Բանկ՝</b> <code>{bank}</code>\n<b>Ստացող՝</b> <code>{holder}</code>\n<b>Քարտ՝</b> <code>{number}</code>{note}\n\nՓոխանցումից հետո սեղմեք ստուգման կոճակը։",
    )
    return card, template.format(
        bank=card.bank_name,
        holder=card.holder_name,
        number=card.card_number,
        note=note,
    )


async def success_refill(BotTexts, call: CallbackQuery, way, amount, p_id, user_id, pay_amount):
    try:
        if await DB.get_refill(receipt=p_id, is_finished=True):
            return await call.answer(BotTexts.TEXTS.error_refill)

        user = await DB.get_user(user_id=user_id)
        settings = await DB.get_settings()
        refill = await DB.get_refill(p_id)
        curr = refill.currency
        ref_percent, ref_amount = 0, 0

        pay_amount = float(pay_amount)

        amounts = await utils.get_currency_amounts(pay_amount, curr.value)
        amount_rub = amounts['rub']


        await utils.send_admins("refill_log",
            user_mention=f"<a href='tg://user?id={user_id}'>{user.full_name}</a>",
            user_id=user_id,
            pay_amount=pay_amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            pay_id=p_id,
            way=BotTexts.TEXTS.payments_names[way] if way != "custom_pay_method" else settings.custom_pay_method,

        )
        await DB.update_refill(p_id, is_finish=1)
        await DB.update_user(user_id=user_id, total_refill=int(user.total_refill) + float(amount_rub),
                             count_refills=int(user.count_refills) + 1,
                             **{f"balance_{code}": getattr(user, f"balance_{code}") + value
                                for code, value in amounts.items()})
    
        if way != 'custom_pay_method':
            await call.message.delete()
            await call.message.answer(BotTexts.TEXTS.success_refill_text.format(
                way=BotTexts.TEXTS.payments_names[way], 
                amount=pay_amount, 
                receipt=p_id, 
                curr=BotConfig.CURRENCIES[curr.value]['sign']))
        else:
            await bot.send_message(user_id, BotTexts.TEXTS.success_refill_text.format(
                way=settings.custom_pay_method, 
                amount=pay_amount, 
                receipt=p_id, 
                curr=BotConfig.CURRENCIES[curr.value]['sign']))

        if settings.is_ref:
            if user.ref_id is None:
                pass
            else:
                reffer_id = user.ref_id
                reffer = await DB.get_user(user_id=reffer_id)
                if reffer.ref_lvl == 1:
                    ref_percent = settings.ref_percent_1
                elif reffer.ref_lvl == 2:
                    ref_percent = settings.ref_percent_2
                else:
                    ref_percent = settings.ref_percent_3

                referral = {code: round(value / 100 * float(ref_percent), 2)
                            for code, value in amounts.items()}
                ref_amount = referral[settings.currency.value]
                updates = {}
                for code, value in referral.items():
                    updates[f"balance_{code}"] = round(getattr(reffer, f"balance_{code}") + value, 2)
                    updates[f"ref_earn_{code}"] = round(getattr(reffer, f"ref_earn_{code}") + value, 2)
                await DB.update_user(reffer_id, **updates)

                await bot.send_message(reffer_id, BotTexts.TEXTS.yes_refill_ref.format(
                    name=call.from_user.mention_html(), 
                    amount=amount,
                    ref_amount=round(ref_amount, 1),
                    cur=BotConfig.CURRENCIES[settings.currency.value]['sign']))
    except:
        print_exc()


async def initPayments():
    paymentConfig = await DB.get_payments_config()
    lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket = None, None, None, None, None, None, None
    try:
        lolz = AsyncLolzteamMarketPayment(paymentConfig.get('lolz_token') or '')
    except (ValueError, AttributeError, IndexError, Exception):
        pass
    try:
        aaio = AsyncAaio(paymentConfig.get('aaio_api_key') or '', paymentConfig.get('aaio_shop_id') or '', paymentConfig.get('aaio_secret_key_1') or '')
    except (ValueError, Exception):
        pass
    try:
        cryptoBot = payments.CryptoPay(paymentConfig.get('crypto_token') or '')
    except (ValueError, Exception):
        pass
    try:
        cryptomus = AsyncCryptomus(paymentConfig.get('payment_api_key') or '', paymentConfig.get('merchant_id') or '', "None")
    except Exception:
        pass
    try:
        lava = payments.Lava(paymentConfig.get('lava_project_id') or '', paymentConfig.get('lava_secret_key') or '')
    except Exception:
        pass
    try:
        yoomoney = payments.YooMoney(paymentConfig.get('yoomoney_token') or '', paymentConfig.get('yoomoney_number') or '')
    except Exception:
        pass
    try:
        xrocket = payments.XRocketPay(paymentConfig.get('xrocket_token') or '', paymentConfig.get('xrocket_asset') or 'USDT')
    except (ValueError, Exception):
        pass
    return lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket


async def send_crypto_refill_invoice(msg: Message, BotTexts: BTs.Ru | BTs.En | BTs.Ua, amount_text: str):
    settings = await DB.get_settings()
    enabled_payments = await DB.get_enabled_payments()
    if not settings.is_refill or "cryptoBot" not in enabled_payments:
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    unfinished_refill = await DB.get_unfinished_user_refill(msg.from_user.id)
    if unfinished_refill:
        if utils.get_unix() <= unfinished_refill.under_date:
            curr = unfinished_refill.currency
            check_amount = unfinished_refill.amount if curr == models.Currencies.rub else await utils.get_exchange(
                unfinished_refill.amount, 'RUB', curr.value.upper()
            )

            return await msg.answer(
                BotTexts.TEXTS.cancel_create_refill_text.format(
                    paymentMethod=BotTexts.TEXTS.payments_names[unfinished_refill.way],
                    pay_amount=unfinished_refill.second_amount,
                    curr=BotConfig.CURRENCIES[curr.value]['sign'],
                    pay_id=unfinished_refill.receipt,
                    under_date=datetime.fromtimestamp(unfinished_refill.under_date).strftime("%d.%m.%Y %H:%M:%S")
                ),
                reply_markup=BotButtons.USERS_INLINE.refill_inl(
                    BotTexts,
                    unfinished_refill.way,
                    check_amount,
                    unfinished_refill.pay_url,
                    unfinished_refill.receipt,
                    unfinished_refill.second_amount
                ).as_markup()
            )
        await DB.delete_refill(unfinished_refill.receipt)

    if not amount_text or not amount_text.replace(".", "").replace(",", "").isdigit():
        return await msg.answer(BotTexts.TEXTS.no_int_amount)

    curr = settings.currency
    _min = BotTexts.TEXTS.min_amount
    _max = BotTexts.TEXTS.max_amount
    min_amount = _min if curr == models.Currencies.rub else await utils.get_exchange(_min, 'RUB', curr.value.upper())
    max_amount = _max if curr == models.Currencies.rub else await utils.get_exchange(_max, 'RUB', curr.value.upper())

    amount = float(amount_text.replace(",", "."))
    if not min_amount <= amount <= max_amount:
        return await msg.answer(BotTexts.TEXTS.min_max_amount.format(
            min_amount=min_amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            max_amount=max_amount
        ))

    bot_name = (await bot.get_me()).username
    comment_for_api = BotTexts.TEXTS.payment_comment_api.format(
        user_name=msg.from_user.full_name,
        bot_name=bot_name,
        curr=BotConfig.CURRENCIES[curr.value]['sign'],
        pay_amount=amount
    )
    success_url = f"https://t.me/{bot_name}"
    _, _, cryptoBot, _, _, _, _ = await initPayments()
    if not cryptoBot:
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    invoice_currency = curr.value.upper()
    invoice_amount = amount
    if curr == models.Currencies.amd:
        invoice_currency = "USD"
        invoice_amount = await utils.get_exchange(amount, 'AMD', 'USD')
    payment_payload = f"refill:{msg.from_user.id}:{utils.get_unix(True)}"
    payment = await cryptoBot.create_invoice(
        invoice_amount,
        invoice_currency,
        description=comment_for_api,
        success_url=success_url,
        payload=payment_payload,
    )
    pay_url = payment.get("bot_invoice_url") or payment.get("pay_url") or payment.get("mini_app_invoice_url")
    pay_id = str(payment.get("invoice_id"))
    if not pay_url or not pay_id or pay_id == "None":
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())
    pay_amount = amount
    if curr != models.Currencies.rub:
        pay_amount = await utils.get_exchange(amount, curr.value.upper(), 'RUB')

    await msg.answer(
        BotTexts.TEXTS.create_refill_text.format(
            paymentMethod=BotTexts.TEXTS.payments_names["cryptoBot"],
            pay_amount=amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            pay_id=pay_id,
            under_date=datetime.fromtimestamp(utils.get_unix() + 3600).strftime("%d.%m.%Y %H:%M:%S")
        ),
        reply_markup=BotButtons.USERS_INLINE.refill_inl(
            BotTexts,
            "cryptoBot",
            pay_amount,
            pay_url,
            pay_id,
            amount
        ).as_markup()
    )
    await DB.add_refill(float(pay_amount), "cryptoBot", msg.from_user.id, str(pay_id), pay_url, float(amount), curr)


async def send_xrocket_refill_invoice(msg: Message, BotTexts: BTs.Ru | BTs.En | BTs.Ua, amount_text: str):
    settings = await DB.get_settings()
    enabled_payments = await DB.get_enabled_payments()
    if not settings.is_refill or "xrocket" not in enabled_payments:
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    unfinished_refill = await DB.get_unfinished_user_refill(msg.from_user.id)
    if unfinished_refill:
        if utils.get_unix() <= unfinished_refill.under_date:
            curr = unfinished_refill.currency
            check_amount = unfinished_refill.amount if curr == models.Currencies.rub else await utils.get_exchange(
                unfinished_refill.amount, 'RUB', curr.value.upper()
            )
            return await msg.answer(
                BotTexts.TEXTS.cancel_create_refill_text.format(
                    paymentMethod=BotTexts.TEXTS.payments_names[unfinished_refill.way],
                    pay_amount=unfinished_refill.second_amount,
                    curr=BotConfig.CURRENCIES[curr.value]['sign'],
                    pay_id=unfinished_refill.receipt,
                    under_date=datetime.fromtimestamp(unfinished_refill.under_date).strftime("%d.%m.%Y %H:%M:%S")
                ),
                reply_markup=BotButtons.USERS_INLINE.refill_inl(
                    BotTexts,
                    unfinished_refill.way,
                    check_amount,
                    unfinished_refill.pay_url,
                    unfinished_refill.receipt,
                    unfinished_refill.second_amount
                ).as_markup()
            )
        await DB.delete_refill(unfinished_refill.receipt)

    if not amount_text or not amount_text.replace(".", "").replace(",", "").isdigit():
        return await msg.answer(BotTexts.TEXTS.no_int_amount)

    curr = settings.currency
    min_amount = BotTexts.TEXTS.min_amount if curr == models.Currencies.rub else await utils.get_exchange(BotTexts.TEXTS.min_amount, 'RUB', curr.value.upper())
    max_amount = BotTexts.TEXTS.max_amount if curr == models.Currencies.rub else await utils.get_exchange(BotTexts.TEXTS.max_amount, 'RUB', curr.value.upper())
    amount = float(amount_text.replace(",", "."))
    if not min_amount <= amount <= max_amount:
        return await msg.answer(BotTexts.TEXTS.min_max_amount.format(
            min_amount=min_amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            max_amount=max_amount
        ))

    bot_name = (await bot.get_me()).username
    comment_for_api = BotTexts.TEXTS.payment_comment_api.format(
        user_name=msg.from_user.full_name,
        bot_name=bot_name,
        curr=BotConfig.CURRENCIES[curr.value]['sign'],
        pay_amount=amount
    )
    _, _, _, _, _, _, xrocket = await initPayments()
    if not xrocket:
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    invoice_amount = amount if curr != models.Currencies.rub else await utils.get_exchange(amount, 'RUB', 'USD')
    payment_payload = f"refill:{msg.from_user.id}:{utils.get_unix(True)}"
    payment = await xrocket.create_invoice(invoice_amount, comment_for_api, payment_payload, f"https://t.me/{bot_name}")
    pay_url = payment.get("link") or payment.get("payLink") or payment.get("paymentLink") or payment.get("url")
    links = payment.get("links") if isinstance(payment.get("links"), dict) else {}
    pay_url = pay_url or links.get("telegramBotLink") or links.get("web")
    pay_id = str(payment.get("id") or payment.get("invoice_id") or payment.get("invoiceId") or payment.get("uuid"))
    if not pay_url or not pay_id or pay_id == "None":
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())
    pay_amount = amount if curr == models.Currencies.rub else await utils.get_exchange(amount, curr.value.upper(), 'RUB')

    await msg.answer(
        BotTexts.TEXTS.create_refill_text.format(
            paymentMethod=BotTexts.TEXTS.payments_names["xrocket"],
            pay_amount=amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            pay_id=pay_id,
            under_date=datetime.fromtimestamp(utils.get_unix() + 3600).strftime("%d.%m.%Y %H:%M:%S")
        ),
        reply_markup=BotButtons.USERS_INLINE.refill_inl(
            BotTexts,
            "xrocket",
            pay_amount,
            pay_url,
            pay_id,
            amount
        ).as_markup()
    )
    await DB.add_refill(float(pay_amount), "xrocket", msg.from_user.id, str(pay_id), pay_url, float(amount), curr)


async def send_custom_refill_invoice(msg: Message, BotTexts: BTs.Ru | BTs.En | BTs.Ua, amount_text: str):
    settings = await DB.get_settings()
    enabled_payments = await DB.get_enabled_payments()
    if not settings.is_refill or "custom_pay_method" not in enabled_payments:
        return await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    unfinished_refill = await DB.get_unfinished_user_refill(msg.from_user.id)
    if unfinished_refill:
        if utils.get_unix() <= unfinished_refill.under_date:
            curr = unfinished_refill.currency
            if unfinished_refill.way == "custom_pay_method":
                card_id = None
                if unfinished_refill.pay_url and unfinished_refill.pay_url.startswith("custom_card:"):
                    card_id = unfinished_refill.pay_url.split(":", 1)[1]
                _, custom_pay_text = await _custom_pay_instruction_text(BotTexts, card_id)
                return await msg.answer(
                    BotTexts.TEXTS.cancel_create_refill_text_custom_pay_method.format(
                        paymentMethod=settings.custom_pay_method,
                        pay_amount=unfinished_refill.second_amount,
                        curr=BotConfig.CURRENCIES[curr.value]['sign'],
                        pay_id=unfinished_refill.receipt,
                        under_date=datetime.fromtimestamp(unfinished_refill.under_date).strftime("%d.%m.%Y %H:%M:%S"),
                        custom_pay_method_text=custom_pay_text,
                    ),
                    reply_markup=BotButtons.USERS_INLINE.custom_pay_method_check(BotTexts, unfinished_refill.receipt).as_markup(),
                )
            check_amount = unfinished_refill.amount if curr == models.Currencies.rub else await utils.get_exchange(
                unfinished_refill.amount, 'RUB', curr.value.upper()
            )
            return await msg.answer(
                BotTexts.TEXTS.cancel_create_refill_text.format(
                    paymentMethod=BotTexts.TEXTS.payments_names[unfinished_refill.way],
                    pay_amount=unfinished_refill.second_amount,
                    curr=BotConfig.CURRENCIES[curr.value]['sign'],
                    pay_id=unfinished_refill.receipt,
                    under_date=datetime.fromtimestamp(unfinished_refill.under_date).strftime("%d.%m.%Y %H:%M:%S"),
                ),
                reply_markup=BotButtons.USERS_INLINE.refill_inl(BotTexts, unfinished_refill.way, check_amount, unfinished_refill.pay_url, unfinished_refill.receipt, unfinished_refill.second_amount).as_markup(),
            )
        await DB.delete_refill(unfinished_refill.receipt)

    if not amount_text or not amount_text.replace(".", "").replace(",", "").isdigit():
        return await msg.answer(BotTexts.TEXTS.no_int_amount)
    curr = settings.currency
    amount = float(amount_text.replace(",", "."))
    min_amount = max(float(settings.custom_pay_method_min_amount or 0), BotTexts.TEXTS.min_amount if curr == models.Currencies.rub else await utils.get_exchange(BotTexts.TEXTS.min_amount, 'RUB', curr.value.upper()))
    max_amount = BotTexts.TEXTS.max_amount if curr == models.Currencies.rub else await utils.get_exchange(BotTexts.TEXTS.max_amount, 'RUB', curr.value.upper())
    if not min_amount <= amount <= max_amount:
        return await msg.answer(BotTexts.TEXTS.min_max_amount.format(min_amount=min_amount, curr=BotConfig.CURRENCIES[curr.value]['sign'], max_amount=max_amount))
    receipt = str(utils.get_unix(True))
    amount_rub = amount if curr == models.Currencies.rub else await utils.get_exchange(amount, curr.value.upper(), 'RUB')
    card, custom_pay_text = await _custom_pay_instruction_text(BotTexts)
    if not card:
        return await msg.answer(custom_pay_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "refill").as_markup())
    await DB.add_refill(float(amount_rub), "custom_pay_method", msg.from_user.id, receipt, _custom_card_marker(card.card_id), float(amount), curr)
    await msg.answer(
        BotTexts.TEXTS.create_refill_text_custom_pay_method.format(
            paymentMethod=settings.custom_pay_method,
            pay_amount=amount,
            curr=BotConfig.CURRENCIES[curr.value]['sign'],
            pay_id=receipt,
            under_date=datetime.fromtimestamp(utils.get_unix() + 3600).strftime("%d.%m.%Y %H:%M:%S"),
            custom_pay_method_text=custom_pay_text,
        ),
        reply_markup=BotButtons.USERS_INLINE.custom_pay_method_check(BotTexts, receipt).as_markup(),
    )


async def send_stars_refill_invoice(msg: Message, BotTexts, amount_text: str):
    settings = await DB.get_settings()
    if "stars" not in await DB.get_enabled_payments() or not settings.is_refill:
        return await msg.answer(BotTexts.TEXTS.is_refill_text)
    try:
        amount = float(amount_text.replace(",", "."))
    except (TypeError, ValueError):
        return await msg.answer(BotTexts.TEXTS.no_int_amount)
    if amount <= 0:
        return await msg.answer(BotTexts.TEXTS.no_int_amount)
    rate = float(settings.stars_amd_per_star or 100)
    if rate <= 0:
        return await msg.answer(BotTexts.TEXTS.incorrect_data)
    amount_amd = amount if settings.currency == models.Currencies.amd else await utils.get_exchange(
        amount, settings.currency.value.upper(), "AMD"
    )
    stars = max(1, math.ceil(amount_amd / rate))
    receipt = str(utils.get_unix(True))
    payload = f"stars:{msg.from_user.id}:{amount}:{settings.currency.value}:{receipt}"
    await msg.answer_invoice(
        title="GS AutoShop",
        description=f"Հաշվեկշռի լիցքավորում՝ {amount}{BotConfig.CURRENCIES[settings.currency.value]['sign']}",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="Telegram Stars", amount=stars)],
    )


@userRouter.callback_query(F.data == "refill")
async def topup_balance(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    enabled_payments = await DB.get_enabled_payments()
    if (await DB.get_settings()).is_refill and enabled_payments:
        await edit_menu(call, BotTexts.TEXTS.choose_refill_method,
                        (await BotButtons.USERS_INLINE.get_refill_kb(BotTexts, enabled_payments)).as_markup(), "refill")
    else:
        await edit_menu(call, BotTexts.TEXTS.is_refill_text,
                        BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup(), "refill")


@userRouter.callback_query(F.data.startswith("refill:"))
async def refill(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    unfinishedRefill = await DB.get_unfinished_user_refill(call.from_user.id)
    await call.message.delete()
    if unfinishedRefill:
        if utils.get_unix() <= unfinishedRefill.under_date:
            curr = unfinishedRefill.currency
            amount = unfinishedRefill.amount if curr == models.Currencies.rub else await utils.get_exchange(
                unfinishedRefill.amount, 'RUB', curr.value.upper()
            )

            if unfinishedRefill.way == "custom_pay_method":
                settings = await DB.get_settings()
                card_id = None
                if unfinishedRefill.pay_url and unfinishedRefill.pay_url.startswith("custom_card:"):
                    card_id = unfinishedRefill.pay_url.split(":", 1)[1]
                _, custom_pay_text = await _custom_pay_instruction_text(BotTexts, card_id)
                return await call.message.answer(
                    BotTexts.TEXTS.cancel_create_refill_text_custom_pay_method.format(
                        paymentMethod=settings.custom_pay_method,
                        pay_amount=unfinishedRefill.second_amount,
                        curr=BotConfig.CURRENCIES[curr.value]['sign'],
                        pay_id=unfinishedRefill.receipt,
                        under_date=datetime.fromtimestamp(unfinishedRefill.under_date).strftime("%d.%m.%Y %H:%M:%S"),
                        custom_pay_method_text=custom_pay_text,
                    ),
                    reply_markup=BotButtons.USERS_INLINE.custom_pay_method_check(BotTexts, unfinishedRefill.receipt).as_markup()
                )
            else:
                return await call.message.answer(BotTexts.TEXTS.cancel_create_refill_text.format(
                    paymentMethod=BotTexts.TEXTS.payments_names[unfinishedRefill.way],
                    pay_amount=unfinishedRefill.second_amount,
                    curr=BotConfig.CURRENCIES[curr.value]['sign'],
                    pay_id=unfinishedRefill.receipt,
                    under_date=datetime.fromtimestamp(unfinishedRefill.under_date).strftime("%d.%m.%Y %H:%M:%S")
                ), reply_markup=BotButtons.USERS_INLINE.refill_inl(BotTexts, unfinishedRefill.way, amount, unfinishedRefill.pay_url,
                                                                unfinishedRefill.receipt, unfinishedRefill.second_amount).as_markup())
        else:
            await DB.delete_refill(unfinishedRefill.receipt)
    paymentMethod = call.data.split(":")[1]
    if paymentMethod not in {"cryptoBot", "xrocket", "stars", "custom_pay_method"}:
        return await call.answer("Վճարման այս եղանակը հասանելի չէ։", show_alert=True)
    await state.set_state(UserRefills.enter_amount)
    await state.update_data(way=paymentMethod)
    await call.message.answer(BotTexts.TEXTS.enter_amount_of_refill,
                                 reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "refill").as_markup())


@userRouter.message(StateFilter(UserRefills.enter_amount), F.text)
async def enter_amount(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    way = (await state.get_data()).get("way")
    await state.clear()
    if way == "stars":
        await send_stars_refill_invoice(msg, BotTexts, msg.text)
    elif way == "custom_pay_method":
        await send_custom_refill_invoice(msg, BotTexts, msg.text)
    elif way == "xrocket":
        await send_xrocket_refill_invoice(msg, BotTexts, msg.text)
    else:
        await send_crypto_refill_invoice(msg, BotTexts, msg.text)


@userRouter.pre_checkout_query()
async def stars_pre_checkout(query: PreCheckoutQuery):
    parts = query.invoice_payload.split(":")
    valid = (len(parts) == 5 and parts[0] == "stars" and
             parts[1].isdigit() and int(parts[1]) == query.from_user.id and
             "stars" in await DB.get_enabled_payments())
    await query.answer(ok=valid, error_message=None if valid else "Վճարումը հասանելի չէ։")


@userRouter.message(F.successful_payment)
async def stars_successful_payment(msg: Message, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    payment = msg.successful_payment
    parts = payment.invoice_payload.split(":")
    if len(parts) != 5 or parts[0] != "stars" or int(parts[1]) != msg.from_user.id:
        return
    _, _, amount_text, currency_code, receipt_seed = parts
    amount = float(amount_text)
    currency = models.Currencies(currency_code)
    receipt = payment.telegram_payment_charge_id or receipt_seed
    if await DB.get_refill(receipt=receipt):
        return
    amount_rub = amount if currency == models.Currencies.rub else await utils.get_exchange(
        amount, currency.value.upper(), "RUB"
    )
    await DB.add_refill(
        float(amount_rub), "stars", msg.from_user.id, receipt, "-", amount, currency
    )
    await success_refill(
        BotTexts, _MessageCallbackAdapter(msg), "stars", amount_rub,
        receipt, msg.from_user.id, amount,
    )


@userRouter.callback_query(F.data.startswith("check_pay:"))
async def check_pay(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    _, way, amount, pay_id, second_amount = call.data.split(":")
    lolz, aaio, cryptoBot, lava, yoomoney, cryptomus, xrocket = await initPayments()
    refill = await DB.get_refill(pay_id, True)
    try:
        if way == "cryptoBot":
            status = await cryptoBot.is_paid(pay_id)
        elif way == "xrocket":
            status = await xrocket.is_paid(pay_id)
        elif way == "lava":
            status = await lava.status_invoice(pay_id)
        elif way == "lolz":
            status = (await lolz.get_invoice(invoice_id=pay_id)).status == "paid"
        elif way == "yoomoney":
            status = yoomoney.check_yoomoney_payment(pay_id)
        elif way == "aaio":
            status = (await aaio.get_order_info(pay_id)).status in ["success", "hold"]
        else:
            # Cryptomus
            status = (await cryptomus.payment_info(order_id=pay_id)).status in [InvoiceStatuses.PAID, InvoiceStatuses.PAID_OVER]

        if status and not refill:
            await success_refill(BotTexts, call, way, amount, pay_id, call.from_user.id, second_amount)
        else:
            await call.answer(BotTexts.TEXTS.refill_check_no)
    except Exception as e:
        print(e)
        await call.answer(BotTexts.TEXTS.refill_check_no)
    
    
@userRouter.callback_query(F.data.startswith("check_custom_pay_method:"))
async def check_custom_pay_method(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    pay_id = call.data.split(":")[1]
    refill = await DB.get_refill(pay_id)
    await call.message.delete()
    if refill:
        settings = await DB.get_settings()
        if settings.is_custom_pay_method_receipt_on:
            await state.set_state(UserRefills.enter_receipt_for_custom_pay_method)
            await state.update_data(pay_id=pay_id)
            return await call.message.answer(BotTexts.TEXTS.send_receipt_photo)
        else:
            chat = BotConfig.LOGS_CHANNEL if BotConfig.LOGS_CHANNEL else BotConfig.ADMINS[0] 
            await bot.send_message(chat, text=BotTexts.ADMIN_TEXTS.new_refill_custom_pay_method_alert.format(
                                        username=f"<a href='tg://user?id={call.from_user.id}'>{call.from_user.full_name}</a>",
                                        user_id=call.from_user.id,
                                        amount=refill.second_amount,
                                        curr=BotConfig.CURRENCIES[refill.currency.value]['sign']
                                   ), 
                                   reply_markup=BotButtons.ADMIN_INLINE.confirm(
                                       f"check_custom_pay_method_receipt:{pay_id}:yes",
                                       f"check_custom_pay_method_receipt:{pay_id}:no",
                                   ).as_markup())
            

@userRouter.message(StateFilter(UserRefills.enter_receipt_for_custom_pay_method), F.photo)
async def enter_receipt_for_custom_pay_method(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    refill = await DB.get_refill((await state.get_data())['pay_id'])
    if refill:
        await state.update_data(photo=msg.photo[-1].file_id)
        await msg.reply(BotTexts.TEXTS.confirm_send_receipt_photo, 
                        reply_markup=BotButtons.ADMIN_INLINE.confirm(
                            f"send_receipt_to_check:yes",
                            f"send_receipt_to_check:no",
                        ).as_markup())
    
    
@userRouter.callback_query(StateFilter(UserRefills.enter_receipt_for_custom_pay_method), 
                           F.data.startswith("send_receipt_to_check:"))
async def send_receipt_to_check(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = await state.get_data()
    await state.clear()
    pay_id, photo = data['pay_id'], data['photo']
    _, action = call.data.split(":")
    if action == "yes":
        refill = await DB.get_refill(pay_id)
        chat = BotConfig.LOGS_CHANNEL if BotConfig.LOGS_CHANNEL else BotConfig.ADMINS[0] 
        if refill:
            await bot.send_photo(chat, photo=photo, 
                                caption=BotTexts.ADMIN_TEXTS.new_refill_custom_pay_method_alert.format(
                                    username=f"<a href='tg://user?id={call.from_user.id}'>{call.from_user.full_name}</a>",
                                    user_id=call.from_user.id,
                                    amount=refill.second_amount,
                                    curr=BotConfig.CURRENCIES[refill.currency.value]['sign']
                                    ), 
                                reply_markup=BotButtons.ADMIN_INLINE.confirm(
                                    f"check_custom_pay_method_receipt:{pay_id}:yes",
                                    f"check_custom_pay_method_receipt:{pay_id}:no",
                                ).as_markup())
        await call.message.edit_text(BotTexts.TEXTS.success)
    else:
        await call.message.delete()
        await state.set_state(UserRefills.enter_receipt_for_custom_pay_method)
        await state.update_data(pay_id=pay_id)
        await call.message.answer(BotTexts.TEXTS.send_receipt_photo)
    

@userRouter.callback_query(F.data.startswith("cancel_pay:"))
async def cancel_pay(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    pay_id = call.data.split(":")[1]
    if await DB.get_refill(pay_id):
        await DB.delete_refill(pay_id)
    else:
        await call.answer(BotTexts.TEXTS.error_refill)
    await call.message.delete()
    

###################################

@adminRouter.callback_query(F.data.startswith("check_custom_pay_method_receipt:"))
async def check_custom_pay_method_receipt(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    _, pay_id, action = call.data.split(":")
    refill = await DB.get_refill(pay_id)
    if refill:
        if action == "yes":
            await success_refill(BotTexts, call, "custom_pay_method", refill.amount, pay_id, refill.user_id, refill.second_amount)
            await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "NONE", "OK").as_markup())
        else:
            await bot.send_message(
                refill.user_id,
                BotTexts.TEXTS.refill_was_rejected.format(
                    amount=refill.second_amount,
                    curr=BotConfig.CURRENCIES[refill.currency.value]['sign']
                )
            )
            await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "NONE", "NO").as_markup())
            await DB.delete_refill(pay_id)


