from aiogram import F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types.input_file import FSInputFile

from tgbot.data.loader import bot, userRouter, adminRouter, dp
from tgbot.data.config import BotButtons, BotConfig, BotImages, DB
from tgbot.data.config import BotTexts as BTs
from tgbot.utils import utils, models
from tgbot.utils import item_content
from tgbot.utils.menu import edit_menu, get_banner, send_menu
from tgbot.states import userStates

import asyncio
import os


def _is_joined_channel(member) -> bool:
    status = getattr(member.status, "value", member.status)
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return status not in {"left", "kicked"}


@dp.callback_query(F.data == "NONE")
async def none_callback(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()


@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, state: FSMContext):
    await state.clear()
    settings = await DB.get_settings()
    BotTexts = await utils.get_language(call.from_user.id)
    if settings.is_sub:
        count = 0
        urls_txt = ''

        channels = await DB.get_mandatory_channels(enabled_only=True)
        if channels:
            for channel in channels:
                try:
                    user_status = await bot.get_chat_member(chat_id=channel.channel_id, user_id=call.from_user.id)
                    subscribed = _is_joined_channel(user_status)
                except Exception:
                    subscribed = False
                if not subscribed:
                    urls_txt += f"<a href='{channel.invite_link}'>{channel.title}</a> — Բաժանորդագրված չեք\n"
                else:
                    count += 1
                    urls_txt += f"<a href='{channel.invite_link}'>{channel.title}</a> — Բաժանորդագրված եք\n"

            if count != len(channels):
                return await edit_menu(
                    call, BotTexts.TEXTS.channels_error.format(urls_txt=urls_txt),
                    BotButtons.USERS_INLINE.mandatory_sub_kb(BotTexts, channels).as_markup(),
                    "main",
                )
    await edit_menu(
        call,
        BotTexts.TEXTS.main_menu.format(username=call.from_user.mention_html()),
        await BotButtons.USERS_REPLY.main_menu(BotTexts, call.from_user.id, BotConfig.ADMINS),
        "main",
    )
    
 

@userRouter.callback_query(F.data == "back_to_user_menu")
async def back_to_user_menu(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await edit_menu(
        call,
        BotTexts.TEXTS.main_menu.format(username=call.from_user.mention_html()),
        await BotButtons.USERS_REPLY.main_menu(BotTexts, call.from_user.id, BotConfig.ADMINS),
        "main",
    )


@userRouter.message(Command("start"))
async def command_start(msg: Message, command: CommandObject, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    user = await DB.get_user(user_id=msg.from_user.id)
    kb = await BotButtons.USERS_REPLY.main_menu(BotTexts, msg.from_user.id, BotConfig.ADMINS)
    message_text = BotTexts.TEXTS.main_menu.format(username=msg.from_user.mention_html())
    settings = await DB.get_settings()
    start_banner = await get_banner("main")
    if settings.is_ref:
        if not command.args:
            if start_banner:
                await msg.answer_photo(start_banner,
                                    caption=message_text,
                                    reply_markup=kb)
            else:
                await msg.answer(message_text, reply_markup=kb)
        else:
            try:
                reffer_user_id = int(command.args)
            except (TypeError, ValueError):
                return await msg.answer(BotTexts.TEXTS.incorrect_data, reply_markup=kb)
            reffer = await DB.get_user(user_id=reffer_user_id)
            if reffer is None:
                if start_banner:
                    await msg.answer_photo(start_banner,
                                           caption=message_text,
                                           reply_markup=kb)
                else:
                    await msg.answer(message_text, reply_markup=kb)
            else:
                if user.ref_id is not None:
                    await msg.answer(BotTexts.TEXTS.yes_reffer)
                else:
                    if reffer.user_id == msg.from_user.id:
                        await msg.answer(BotTexts.TEXTS.invite_yourself)
                    else:
                        await DB.update_user(user_id=msg.from_user.id, ref_id=reffer.user_id, ref_user_name=reffer.user_name, ref_full_name=reffer.full_name)
                        await DB.update_user(user_id=reffer.user_id, ref_count=reffer.ref_count + 1)

                        await bot.send_message(chat_id=reffer.user_id, text=BotTexts.TEXTS.new_refferal.format(user_name=user.user_name,
                                                       user_ref_count=reffer.ref_count + 1,
                                                       convert_ref=utils.numeral_noun_declension(reffer.ref_count + 1, BotTexts.TEXTS.ref_s)))

                        text, new_lvl, next_lvl, remain_refs, ref_lvl, isNewLvl = None, 1, 1, 1, 1, False
                        if int(reffer.ref_count) + 1 == int(settings.ref_lvl_2):
                            remain_refs = settings.ref_lvl_3 - (reffer.ref_count + 1)
                            ref_lvl, new_lvl, next_lvl, isNewLvl = 2, 2, 3, True
                        elif int(reffer.ref_count) + 1 == int(settings.ref_lvl_3):
                            ref_lvl, new_lvl, next_lvl, isNewLvl = 3, 3, 3, True
                            text = BotTexts.TEXTS.max_ref_lvl
                        
                        if isNewLvl:
                            if text is None:
                                text = BotTexts.TEXTS.new_ref_lvl.format(new_lvl=new_lvl, next_lvl=next_lvl, remain_refs=remain_refs,
                                                           convert_ref=utils.numeral_noun_declension(remain_refs, BotTexts.TEXTS.ref_s))
                            await bot.send_message(chat_id=reffer.user_id, text=text)
                            await DB.update_user(user_id=reffer.user_id, ref_lvl=ref_lvl)

                        if start_banner:
                            await msg.answer_photo(start_banner,
                                                caption=message_text,
                                                reply_markup=kb)
                        else:
                            await msg.answer(message_text, reply_markup=kb)
    else:
        if start_banner:
            await msg.answer_photo(start_banner,
                                    caption=message_text,
                                    reply_markup=kb)
        else:
            await msg.answer(message_text, reply_markup=kb)


@userRouter.message(F.text == BTs.Ru.BUTTONS.profile)
@userRouter.message(F.text == BTs.Hy.BUTTONS.profile)
@userRouter.message(F.text == BTs.Ua.BUTTONS.profile)
@userRouter.message(F.text == BTs.En.BUTTONS.profile)
async def profile_open(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    user = await DB.get_user(user_id=msg.from_user.id)
    settings = await DB.get_settings()
    total_refill = user.total_refill
    balance = getattr(user, f"balance_{settings.currency.value}")
    tr = total_refill if settings.currency == models.Currencies.rub else await utils.get_exchange(
        total_refill, 'RUB', settings.currency.value.upper()
    )
    text = BotTexts.TEXTS.profile_text.format(
        username=msg.from_user.mention_html(),
        user_id=msg.from_user.id,
        balance=f"{balance:.2f}",
        curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        total_refill=f"{tr:.2f}",
        reg_date=user.reg_date,
    )
    await send_menu(msg, text, (await BotButtons.USERS_INLINE.profile_menu(BotTexts)).as_markup(), "profile")


@userRouter.callback_query(F.data == "profile")
async def profile(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    user = await DB.get_user(user_id=call.from_user.id)
    settings = await DB.get_settings()
    balance = getattr(user, f"balance_{settings.currency.value}")
    tr = user.total_refill if settings.currency == models.Currencies.rub else await utils.get_exchange(
        user.total_refill, 'RUB', settings.currency.value.upper()
    )
    text = BotTexts.TEXTS.profile_text.format(
        username=call.from_user.mention_html(),
        user_id=call.from_user.id,
        balance=f"{balance:.2f}",
        curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        total_refill=f"{tr:.2f}",
        reg_date=user.reg_date,
    )
    await edit_menu(call, text, (await BotButtons.USERS_INLINE.profile_menu(BotTexts)).as_markup(), "profile")


@userRouter.message(F.text == BTs.Ru.BUTTONS.support)
@userRouter.message(F.text == BTs.Hy.BUTTONS.support)
@userRouter.message(F.text == BTs.En.BUTTONS.support)
@userRouter.message(F.text == BTs.Ua.BUTTONS.support)
async def open_support(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.support and settings.support != "-":
        text = BotTexts.TEXTS.support_text
        kb = (await BotButtons.USERS_INLINE.support(BotTexts)).as_markup()
    else:
        text = BotTexts.TEXTS.support_is_not_provided
        kb = BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup()

    await send_menu(msg, text, kb, "support")
        

@userRouter.callback_query(F.data == "support")
async def open_support_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.support and settings.support != "-":
        text = BotTexts.TEXTS.support_text
        kb = (await BotButtons.USERS_INLINE.support(BotTexts)).as_markup()
    else:
        text = BotTexts.TEXTS.support_is_not_provided
        kb = BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup()

    await edit_menu(call, text, kb, "support")


@userRouter.message(F.text == BTs.En.BUTTONS.faq)
@userRouter.message(F.text == BTs.Ru.BUTTONS.faq)
@userRouter.message(F.text == BTs.Hy.BUTTONS.faq)
@userRouter.message(F.text == BTs.Ua.BUTTONS.faq)
async def open_faq(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.faq and settings.faq != "-":
        text = settings.faq
        kb = (await BotButtons.USERS_INLINE.faq(BotTexts)).as_markup()
    else:
        text = BotTexts.TEXTS.incorrect_data
        kb = BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup()

    await send_menu(msg, text, kb, "faq")
        
@userRouter.callback_query(F.data == "faq")
async def open_faq_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.faq and settings.faq != "-":
        text = settings.faq
        kb = (await BotButtons.USERS_INLINE.faq(BotTexts)).as_markup()
    else:
        text = BotTexts.TEXTS.incorrect_data
        kb = BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup()

    await edit_menu(call, text, kb, "faq")


@userRouter.message(F.text == BTs.Ru.BUTTONS.topup_balance)
@userRouter.message(F.text == BTs.Hy.BUTTONS.topup_balance)
@userRouter.message(F.text == BTs.En.BUTTONS.topup_balance)
@userRouter.message(F.text == BTs.Ua.BUTTONS.topup_balance)
async def topup_balance(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    enabled_payments = await DB.get_enabled_payments()
    if settings.is_refill and enabled_payments:
            await send_menu(msg, BotTexts.TEXTS.choose_refill_method,
                            (await BotButtons.USERS_INLINE.get_refill_kb(BotTexts, enabled_payments)).as_markup(), "refill")
    else:
        await msg.answer(BotTexts.TEXTS.is_refill_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())

    
@userRouter.message(F.text == BTs.Ru.BUTTONS.buy)
@userRouter.message(F.text == BTs.Hy.BUTTONS.buy)
@userRouter.message(F.text == BTs.En.BUTTONS.buy)
@userRouter.message(F.text == BTs.Ua.BUTTONS.buy)
async def buy(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.is_buy:
        categories = await DB.get_all_categories()
        if categories:
            await send_menu(msg, BotTexts.TEXTS.available_cats,
                            BotButtons.USERS_INLINE.select_category(BotTexts, categories).as_markup(), "buy")
        else:
            await msg.answer(BotTexts.TEXTS.no_cats,
                             reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())
    else:
        await msg.answer(BotTexts.TEXTS.is_buy_text, reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup())
        
        
@userRouter.callback_query(F.data == "buy")
async def buy_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    settings = await DB.get_settings()
    if settings.is_buy:
        categories = await DB.get_all_categories()
        if categories:
            await edit_menu(call, BotTexts.TEXTS.available_cats,
                            BotButtons.USERS_INLINE.select_category(BotTexts, categories).as_markup(), "buy")
        else:
            await edit_menu(call, BotTexts.TEXTS.no_cats,
                            BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup(), "buy")
    else:
        await edit_menu(call, BotTexts.TEXTS.is_buy_text,
                        BotButtons.USERS_INLINE.custom_button(BotTexts, "back_to_user_menu").as_markup(), "buy")


@userRouter.callback_query(F.data == "close")
async def close_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await edit_menu(
        call, BotTexts.TEXTS.main_menu.format(username=call.from_user.mention_html()),
        await BotButtons.USERS_REPLY.main_menu(BotTexts, call.from_user.id, BotConfig.ADMINS), "main"
    )


@userRouter.callback_query(F.data == "ref_system")
async def ref_system(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    settings = await DB.get_settings()
    if settings.is_ref:
        await state.clear()
        bot_name = (await bot.get_me()).username
        user = await DB.get_user(user_id=call.from_user.id)

        ref_earn = getattr(user, f"ref_earn_{settings.currency.value}")

        ref_lvl = user.ref_lvl
        if ref_lvl == 1:
            lvl = settings.ref_lvl_2
            ref_percent = settings.ref_percent_1
        elif ref_lvl == 2:
            lvl = settings.ref_lvl_3
            ref_percent = settings.ref_percent_2
        else:
            lvl = settings.ref_lvl_3
            ref_percent = settings.ref_percent_3

        remain_refs = lvl - user.ref_count

        if ref_lvl == 3:
            mss = BotTexts.TEXTS.cur_max_lvl
        else:
            mss = BotTexts.TEXTS.next_lvl_remain.format(remain_refs=remain_refs, person_s=utils.numeral_noun_declension(remain_refs, BotTexts.TEXTS.person_s))

        if user.ref_full_name:
            reffer = f"<a href='tg://user?id={user.ref_id}'>{user.ref_full_name}</a>"
        else:
            reffer = BotTexts.TEXTS.nobody

        msg = BotTexts.TEXTS.ref_text.format(ref_link=f"<code>https://t.me/{bot_name}?start={call.from_user.id}</code>", ref_percent=ref_percent, 
                                    reffer=reffer, ref_earn=ref_earn, curr=BotConfig.CURRENCIES[settings.currency.value]['sign'], 
                                    convert_ref=utils.numeral_noun_declension(user.ref_count, BotTexts.TEXTS.ref_s), ref_count=user.ref_count, 
                                    ref_lvl=ref_lvl, mss=mss)
        await edit_menu(call, msg, BotButtons.USERS_INLINE.custom_button(BotTexts, "profile").as_markup(), "profile")
    else:
        await call.answer(BotTexts.TEXTS.is_ref_text, True)


@userRouter.callback_query(F.data == "activate_promo")
async def activate_promo(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await edit_menu(call, BotTexts.TEXTS.promo_act,
                    BotButtons.USERS_INLINE.custom_button(BotTexts, "profile").as_markup(), "profile")
    await state.set_state(userStates.UserPromocodes.enter_promo)


@userRouter.message(StateFilter(userStates.UserPromocodes.enter_promo))
async def enter_promo(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    curr = (await DB.get_settings()).currency
    promocode = await DB.get_promocode(name=msg.text)

    if promocode:
        await state.clear()
        user = await DB.get_user(user_id=msg.from_user.id)
        active_promo = await DB.get_active_promocode(user_id=msg.from_user.id, promocode_name=promocode.name)
        if promocode.uses == 0:
            await msg.answer(BotTexts.TEXTS.no_uses_promocode)
            await DB.delete_promocode(promocode.name)
        elif active_promo:
            await msg.answer(BotTexts.TEXTS.yes_uses_promocode)
        else:
            # active_promo is None
            main_discount = getattr(promocode, f"discount_{curr.value}")

            await DB.update_user(msg.from_user.id, 
                                 balance_rub=user.balance_rub + float(promocode.discount_rub), 
                                 balance_eur=user.balance_eur + float(promocode.discount_eur), 
                                 balance_usd=user.balance_usd + float(promocode.discount_usd),
                                 balance_amd=user.balance_amd + float(promocode.discount_amd))
            await DB.update_promocode(promocode.name, uses=promocode.uses - 1)
            await DB.activate_promocode(msg.from_user.id, promocode.name)
            await msg.answer(BotTexts.TEXTS.yes_promocode.format(discount=main_discount,
                                                         curr=BotConfig.CURRENCIES[curr.value]['sign']))
    else:
        await msg.answer(BotTexts.TEXTS.no_promocode.format(promocode=msg.text))
        
        
@userRouter.callback_query(F.data == "purchases_history")
async def purchases_history(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    purchases = await DB.get_last_purchases(call.from_user.id, 10)
    settings = await DB.get_settings()
    if purchases:
        await call.message.delete()
        for purchase in purchases:
            price = getattr(purchase, f"price_{settings.currency.value}")
            position = await DB.get_position(pos_id=purchase.pos_id)
            
            await call.message.answer(BotTexts.TEXTS.receipt_purchase.format(
                receipt=purchase.receipt,
                pos_name=position.name,
                sum=price,
                curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
                count=purchase.count,
                date=purchase.date
            ))
            
            stored_items = item_content.decode_purchase(purchase.item)
            if stored_items is not None:
                for stored_item in stored_items:
                    await item_content.deliver(call.message, stored_item)
                    await asyncio.sleep(0.3)
                continue
            match position.item_type:
                case "text":
                    if len(purchase.item) <= 4096:
                        await call.message.answer(purchase.item, parse_mode="None")
                    else:
                        with open(f"{position.name}.txt", "w", encoding="utf-8") as file:
                            file.write(purchase.item)
                            file.close()

                        await call.message.answer_document(document=FSInputFile(f"{position.name}.txt"), 
                                                        caption=BotTexts.TEXTS.your_items)
                        os.remove(f"{position.name}.txt")
                        break
                    await asyncio.sleep(0.3)
                case "photo":
                    for item in purchase.item.split("\n"):
                        data, file_id = item.split(":::")
                        await call.message.answer_photo(photo=file_id, caption=data, parse_mode="None")
                        await asyncio.sleep(0.3)
                case "file":
                    for item in purchase.item.split("\n"):
                        data, file_id = item.split(":::")
                        await call.message.answer_document(document=file_id, caption=data, parse_mode="None")
                        await asyncio.sleep(0.3)
                        
        await call.message.answer(BotTexts.TEXTS.last_10_purchases, 
                                  reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, "profile").as_markup())
    else:
        await call.answer(BotTexts.TEXTS.no_have_purchases)


# Переключение языка
@userRouter.callback_query(F.data == "change_language")
async def change_language(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await edit_menu(call, BotTexts.TEXTS.main_menu.format(username=call.from_user.mention_html()),
                    await BotButtons.USERS_REPLY.main_menu(BotTexts, call.from_user.id, BotConfig.ADMINS), "main")


@userRouter.callback_query(F.data.startswith("change_language:"))
async def change_language_choose(call: CallbackQuery, state: FSMContext):
    await state.clear()
    NewLanguage = BTs.Hy
    await edit_menu(
        call, NewLanguage.TEXTS.main_menu.format(username=call.from_user.mention_html()),
        await BotButtons.USERS_REPLY.main_menu(NewLanguage, call.from_user.id, BotConfig.ADMINS), "main"
    )

    
@adminRouter.message(Command(commands=['getFileId']))
async def getFileIdCommand(msg: Message, state: FSMContext, BotTexts):
    await state.clear()
    message = msg.reply_to_message
    media_type = ""
    
    if message.photo:
        media_type = "Фото"
        file_id = message.photo[-1].file_id
    elif message.animation:
        media_type = "Гиф"
        file_id = message.animation.file_id
    elif message.video:
        media_type = "Видео"
        file_id = message.video.file_id
    else:
        media_type = "Файл"
        # document
        file_id = message.document.file_id
    
    await msg.reply(f"<b>Тип медиа: <code>{media_type}</code>\nFILE_ID: <code>{file_id}</code></b>")

@adminRouter.message(Command(commands=['admin', 'adm', 'a']))
@adminRouter.message(F.text == BTs.Ru.BUTTONS.admin_panel)
@adminRouter.message(F.text == BTs.En.BUTTONS.admin_panel)
@adminRouter.message(F.text == BTs.Ua.BUTTONS.admin_panel)
async def admin_panel(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await send_menu(msg, BotTexts.ADMIN_TEXTS.welcome_to_the_admin_panel,
                    BotButtons.ADMIN_INLINE.admin_panel(BotTexts).as_markup(), "admin")
    
    
@adminRouter.callback_query(F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await edit_menu(call, BotTexts.ADMIN_TEXTS.welcome_to_the_admin_panel,
                    BotButtons.ADMIN_INLINE.admin_panel(BotTexts).as_markup(), "admin")

