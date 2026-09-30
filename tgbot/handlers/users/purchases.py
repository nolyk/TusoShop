from tgbot.utils.catalog_emoji import catalog_name
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types.input_file import FSInputFile

from tgbot.data.loader import userRouter, dp
from tgbot.data.config import BotButtons, BotImages, BotConfig, DB
from tgbot.data.config import BotTexts as BTs
from tgbot.utils import utils, models
from tgbot.utils import item_content
from tgbot.utils.menu import edit_menu
from tgbot.states import userStates

import os
import asyncio

@userRouter.callback_query(F.data.startswith("open_category:"))
@userRouter.callback_query(F.data.startswith("mail_category_open:"))
async def open_category(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    try:
        category_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return await call.answer(BotTexts.TEXTS.incorrect_data, show_alert=True)
    category = await DB.get_category(cat_id=category_id)
    if not category:
        return await call.answer(BotTexts.TEXTS.data_was_edit, show_alert=True)
    positions = await DB.get_positions(cat_id=category_id)
    sub_categories = await DB.get_subcategories(cat_id=category_id)
    if sub_categories or positions:
        kb = (await BotButtons.USERS_INLINE.select_subcategories_and_positions(
            BotTexts, sub_categories, positions
        )).as_markup()
        if call.data.startswith("open_category"):
            await edit_menu(call, BotTexts.TEXTS.current_cat.format(name=catalog_name(category)), kb, f"category:{category_id}")
        else:
            await call.message.answer(BotTexts.TEXTS.current_cat.format(name=catalog_name(category)), reply_markup=kb)
    else:
        if call.data.startswith("open_category"):
            await edit_menu(
                call, BotTexts.TEXTS.no_products,
                BotButtons.USERS_INLINE.custom_button(BotTexts, "buy").as_markup(),
                f"category:{category_id}",
            )
        else:
            await call.answer(BotTexts.TEXTS.no_products, show_alert=True)
        
        
@userRouter.callback_query(F.data.startswith("open_subcategory:"))
@userRouter.callback_query(F.data.startswith("mail_subcategory_open:"))
async def open_subcategory(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    try:
        subcategory_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return await call.answer(BotTexts.TEXTS.incorrect_data, show_alert=True)
    subcategory = await DB.get_subcategory(sub_cat_id=subcategory_id)
    if not subcategory:
        return await call.answer(BotTexts.TEXTS.data_was_edit, show_alert=True)
    positions = await DB.get_positions(sub_cat_id=subcategory_id)
    if positions:
        category = await DB.get_category(cat_id=positions[0].cat_id)
        kb = (await BotButtons.USERS_INLINE.select_positions(BotTexts, positions)).as_markup()
        if call.data.startswith("open_subcategory"):
            await edit_menu(call, BotTexts.TEXTS.current_cat.format(name=f"{catalog_name(category)} - {catalog_name(subcategory)}"),
                            kb, f"subcategory:{subcategory_id}")
        else:
            await call.message.answer(BotTexts.TEXTS.current_cat.format(name=f"{catalog_name(category)} - {catalog_name(subcategory)}"), reply_markup=kb)
    else:
        if call.data.startswith("open_subcategory"):
            await edit_menu(
                call, BotTexts.TEXTS.no_products,
                BotButtons.USERS_INLINE.custom_button(BotTexts, f"open_category:{subcategory.cat_id}").as_markup(),
                f"subcategory:{subcategory_id}",
            )
        else:
            await call.answer(BotTexts.TEXTS.no_products, show_alert=True)
        

@userRouter.callback_query(F.data.startswith("open_position:"))
@userRouter.callback_query(F.data.startswith("mail_position_open:"))
async def open_position(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    try:
        position_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return await call.answer(BotTexts.TEXTS.incorrect_data, show_alert=True)
    position = await DB.get_position(pos_id=position_id)
    if not position:
        return await call.answer(BotTexts.TEXTS.data_was_edit, show_alert=True)
    category = await DB.get_category(cat_id=position.cat_id)
    subcategory = await DB.get_subcategory(sub_cat_id=position.sub_cat_id)
    settings = await DB.get_settings()
    price = getattr(position, f"price_{settings.currency.value}")
    if position.is_infinity:
        items = BotTexts.BUTTONS.nolimit
    else:
        items = f"{len(await DB.get_items(pos_id=position.pos_id))} {BotTexts.BUTTONS.pcs}"
    text = BotTexts.TEXTS.open_position_text.format(
        cat_name=f"{catalog_name(category)} - {catalog_name(subcategory)}" if subcategory else catalog_name(category),
        pos_name=catalog_name(position),
        price=price,
        cur=BotConfig.CURRENCIES[settings.currency.value]["sign"],
        items=items,
        desc=position.description if position.description else ""
    )
    kb = BotButtons.USERS_INLINE.position_buy(BotTexts, position).as_markup()
    photo = position.photo if position.photo and position.photo != "-" else None
    if call.data.startswith("open_position"):
        await edit_menu(call, text, kb, f"position:{position_id}", fallback=photo)
    elif photo:
        await call.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
    else:
        await call.message.answer(text=text, reply_markup=kb)
        

@userRouter.callback_query(F.data.startswith("buy_position:"))
async def buy_position(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    position = await DB.get_position(pos_id=int(call.data.split(":")[1]))
    user = await DB.get_user(user_id=call.from_user.id)
    items = await DB.get_items(pos_id=position.pos_id)
    settings = await DB.get_settings()
    curr = BotConfig.CURRENCIES[settings.currency.value]['sign']
    
    price = getattr(position, f"price_{settings.currency.value}")
    balance = getattr(user, f"balance_{settings.currency.value}")

    if balance < price:
        await call.answer(BotTexts.TEXTS.no_balance_for_buying) 
        enabled_payments = await DB.get_enabled_payments()
        if settings.is_refill and enabled_payments:
            if BotImages.TOPUP_BALANCE_PHOTO:
                return await call.message.answer_photo(photo=BotImages.TOPUP_BALANCE_PHOTO, caption=BotTexts.TEXTS.choose_refill_method,
                                        reply_markup=(await BotButtons.USERS_INLINE.get_refill_kb(BotTexts, enabled_payments)).as_markup())
            else:
                return await call.message.answer(BotTexts.TEXTS.choose_refill_method,
                            reply_markup=(await BotButtons.USERS_INLINE.get_refill_kb(BotTexts, enabled_payments)).as_markup())

    if len(items) < 1:
        return await call.answer(BotTexts.TEXTS.no_products, True)

    if price != 0:
        count = int(balance / price)
        
        if count > len(items):
            items = len(items)
        else:
            items = count
    else:
        items = len(items)
        
    await call.message.delete()
    
    if items == 1:
        await call.message.answer(
            BotTexts.TEXTS.confirm_buy_products.format(
                position_name=catalog_name(position),
                count=1,
                price=price,
                curr=curr,
            ),
            reply_markup=BotButtons.USERS_INLINE.confirm_buy_item(position.pos_id, 1).as_markup()
        )
    else:
        await state.set_state(userStates.UserProducts.enter_count_products_for_buy)
        await state.update_data(position=position)

        await call.message.answer(
            BotTexts.TEXTS.enter_count_items_for_buy.format(
                pos_name=catalog_name(position),
                items=items,
                price=price,
                curr=curr,
                balance=balance,
            ),
            reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, f"open_position:{position.pos_id}").as_markup()
        )


@userRouter.message(F.text, StateFilter(userStates.UserProducts.enter_count_products_for_buy))
async def enter_count_products_for_buy(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    position: models.Position = (await state.get_data())['position']
    user = await DB.get_user(user_id=msg.from_user.id)
    items = await DB.get_items(pos_id=position.pos_id)
    settings = await DB.get_settings()
    curr = BotConfig.CURRENCIES[settings.currency.value]['sign']
    
    price = getattr(position, f"price_{settings.currency.value}")
    balance = getattr(user, f"balance_{settings.currency.value}")

    if price != 0:
        count = int(balance / price)
        if count > len(items):
            count = len(items)
    else:
        count = len(items)

    send_message = BotTexts.TEXTS.enter_count_items_for_buy.format(
                pos_name=catalog_name(position),
                items=count,
                price=price,
                curr=curr,
                balance=balance,
            )

    if not msg.text.isdigit():
        return await msg.answer(
            f"{BotTexts.TEXTS.incorrect_data}\n" + send_message,
            reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, f"open_position:{position.pos_id}").as_markup()
        )

    count = int(msg.text)
    amount_pay = round(price * count, 2)

    if len(items) < 1:
        await state.clear()
        return await msg.answer(BotTexts.TEXTS.data_was_edit)

    if count < 1 or count > len(items):
        return await msg.answer(
            f"{BotTexts.TEXTS.incorrect_count_items}\n" + send_message,
            reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, f"open_position:{position.pos_id}").as_markup()
        )

    if int(balance) < amount_pay:
        return await msg.answer(
            f"{BotTexts.TEXTS.no_balance_on_account}\n" + send_message,
            reply_markup=BotButtons.USERS_INLINE.custom_button(BotTexts, f"open_position:{position.pos_id}").as_markup()
        )

    await state.clear()
    await msg.answer(
        BotTexts.TEXTS.confirm_buy_products.format(
            position_name=catalog_name(position),
            count=count,
            price=amount_pay,
            curr=curr,
        ),
        reply_markup=BotButtons.USERS_INLINE.confirm_buy_item(position.pos_id, count).as_markup()
    )


# Подтверждение покупки товара
@userRouter.callback_query(F.data.startswith("buy_item_confirm:"))
async def user_buy_confirm(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    position = await DB.get_position(pos_id=int(call.data.split(":")[1]))
    purchase_count = int(call.data.split(":")[2])
    items = await DB.get_items(pos_id=position.pos_id)

    if purchase_count > len(items):
        return await call.message.edit_text(
            BotTexts.TEXTS.data_was_edit,
        )

    await call.message.edit_text(BotTexts.TEXTS.please_await_products)

    user = await DB.get_user(user_id=call.from_user.id)
    settings = await DB.get_settings()
    curr = BotConfig.CURRENCIES[settings.currency.value]['sign']
    
    price = getattr(position, f"price_{settings.currency.value}")
    balance = getattr(user, f"balance_{settings.currency.value}")
    
    purchase_price = round(price * purchase_count, 2)

    if balance < purchase_price:
        return await call.message.answer(BotTexts.TEXTS.no_balance_on_account)

    
    save_items, save_len = await DB.buy_items(items, purchase_count, position.is_infinity, position.item_type in ['photo', 'file'])
    save_count = len(save_items)

    if purchase_count != save_count:
        purchase_price = round(price * save_count, 2)
        purchase_count = save_count

    await DB.update_user(user.user_id,
                         balance_rub=round(user.balance_rub - round(position.price_rub * purchase_count, 2), 2),
                         balance_eur=round(user.balance_eur - round(position.price_eur * purchase_count, 2), 2),
                         balance_usd=round(user.balance_usd - round(position.price_usd * purchase_count, 2), 2))
    await DB.update_user(user.user_id,
                         balance_amd=round(user.balance_amd - round(position.price_amd * purchase_count, 2), 2))

    receipt = utils.get_unix(True)
    purchase_data = item_content.encode_purchase(save_items)

    await DB.add_purchase(
        user_id=user.user_id,
        receipt=receipt,
        count=purchase_count,
        price_rub=round(position.price_rub * purchase_count, 2),
        price_usd=round(position.price_usd * purchase_count, 2),
        price_eur=round(position.price_eur * purchase_count, 2),
        price_amd=round(position.price_amd * purchase_count, 2),
        pos_id=position.pos_id,
        item=purchase_data
    )

    await call.message.delete()
    
    if any(item_content.decode_item(item) for item in save_items):
        for item in save_items:
            await item_content.deliver(call.message, item)
            await asyncio.sleep(0.3)
    else:
      match position.item_type:
        case "text":
            for item in utils.split_messages(save_items, save_count):
                send_items = "\n\n".join(item)
                if len(send_items) <= 4096:
                    await call.message.answer(send_items, parse_mode="None")
                else:
                    with open(f"position-{position.pos_id}.txt", "w", encoding="utf-8") as file:
                        file.write(send_items)
                        file.close()

                    await call.message.answer_document(document=FSInputFile(f"position-{position.pos_id}.txt"), 
                                                       caption=BotTexts.TEXTS.your_items)
                    os.remove(f"position-{position.pos_id}.txt")
                    break
                await asyncio.sleep(0.3)
        case "photo":
            for item in utils.split_messages(save_items, save_len)[0]:
                data, file_id = item.split(":::")
                await call.message.answer_photo(photo=file_id, caption=data, parse_mode="None")
                await asyncio.sleep(0.3)
        case "file":
            for item in utils.split_messages(save_items, save_len)[0]:
                data, file_id = item.split(":::")
                await call.message.answer_document(document=file_id, caption=data, parse_mode="None")
                await asyncio.sleep(0.3)
        

    await call.message.answer(
        BotTexts.TEXTS.successful_buying.format(
            receipt=receipt,
            position_name=catalog_name(position),
            purchase_count=purchase_count,
            purchase_price=purchase_price,
            curr=curr,
            date=utils.get_date(),
        )
    )
    await utils.send_admins(
        "new_purchase_alert",
            user_name=call.from_user.mention_html(),
            user_id=call.from_user.id,
            amount=purchase_price,
            curr=curr,
            pos_name=catalog_name(position),
            receipt=receipt,
            count=purchase_count
        )

