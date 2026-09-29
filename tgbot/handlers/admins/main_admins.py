from tgbot.utils.mini_app_menu import toggle_mini_app_menu
from aiogram.exceptions import TelegramAPIError
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types.input_file import FSInputFile

from tgbot.data.loader import bot, adminRouter
from tgbot.data.config import BotButtons, BotConfig, DB
from tgbot.data.config import BotTexts as BTs
from tgbot.states import adminStates
from tgbot.utils import models, utils
from tgbot.utils.menu import edit_menu, safe_edit_text, validate_banner_url

from traceback import print_exc
import datetime
import html
import os

async def get_data_for_mail_button(data, value):
    if data == "category":
        category = await DB.get_category(cat_id=int(value))
        return f"<code>{category.name}</code> [<code>{category.cat_id}</code>]"
    elif data == "subcategory": 
        subcategory = await DB.get_subcategory(sub_cat_id=int(value))
        return f"<code>{subcategory.name}</code> [<code>{subcategory.sub_cat_id}</code>]"
    elif data == "position":
        position = await DB.get_position(pos_id=int(value))
        return f"<code>{position.name}</code> [<code>{position.pos_id}</code>]"
    elif data == "contest":
        contest = await DB.get_contest(contest_id=int(value))
        return f"<code>{contest.prize}{BotConfig.CURRENCIES[contest.currency.value]['sign']}</code> [<code>{contest.contest_id}</code>]"
    else:
        # link
        return f"<code>{value}</code>" 


async def get_user_profile(BotTexts, user: models.User):
    settings = await DB.get_settings()
    purchases = await DB.get_purchases_stats_for_user(user.user_id)
    code = settings.currency.value
    balance = getattr(user, f"balance_{code}")
    total_refill = user.total_refill if code == "rub" else await utils.get_exchange(user.total_refill, 'RUB', code.upper())
    total_purchases = purchases[f'total_purchases_{code}']
    ref_earn = getattr(user, f"ref_earn_{code}")
        
    match user.language.value:
        case "ru":
            language = BotConfig.LANGUAGES[0]['name'] # ru
        case "en":
            language = BotConfig.LANGUAGES[1]['name'] # en
        case "ua": 
            language = BotConfig.LANGUAGES[2]['name'] # ua

    return BotTexts.ADMIN_TEXTS.user_profile_found.format(
        username=f"<a href='tg://user?id={user.user_id}'>{user.full_name}</a>",
        user_id=user.user_id,
        balance=balance,
        curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        total_refill=total_refill,
        count_refills=user.count_refills,
        count_purchases=purchases['count_purchases'],
        total_purchases=total_purchases,
        reg_date=user.reg_date,
        language=language,
        ref_count=user.ref_count,
        ref_lvl=user.ref_lvl,
        ref_name=f"<a href='tg://user?id={user.ref_id}'>{user.ref_full_name}</a>" if user.ref_full_name else BotTexts.TEXTS.nobody,
        ref_earn=ref_earn,
    )


@adminRouter.message(Command("admin"), F.chat.type == "private")
async def admin_command(message: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await message.answer(BotTexts.ADMIN_TEXTS.welcome_to_the_admin_panel,
                         reply_markup=BotButtons.ADMIN_INLINE.admin_panel(BotTexts).as_markup())


@adminRouter.callback_query(F.data == "admin_panel")
async def admin_panel(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.welcome_to_the_admin_panel,
                     reply_markup=BotButtons.ADMIN_INLINE.admin_panel(BotTexts).as_markup())


@adminRouter.callback_query(F.data == "menu_banners")
async def menu_banners(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    banners = await DB.get_menu_banners()
    configured = {banner.menu_key for banner in banners}
    text = (
        "<b>Баннеры меню</b>\n\n"
        "Выберите нужное меню кнопкой ниже. В выбранное меню можно загрузить "
        "фотографию из Telegram или вставить прямую HTTPS-ссылку.\n\n"
        "Кнопка «Применить баннер везде» задаёт общий баннер для всех экранов; "
        "индивидуальный баннер меню имеет приоритет."
    )
    await edit_menu(
        call, text,
        BotButtons.ADMIN_INLINE.menu_banners(BotTexts, configured, "all" in configured).as_markup(),
        "admin",
    )


@adminRouter.callback_query(F.data.startswith("menu_banner:open:"))
async def menu_banner_open(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    menu_key = call.data.split(":", 2)[2]
    allowed = {item[0]: item[1] for item in BotButtons.ADMIN_INLINE.BANNER_MENUS}
    if menu_key not in allowed:
        return await call.answer("Неизвестное меню", show_alert=True)
    custom = await DB.get_menu_banner(menu_key)
    status = "установлен отдельно" if custom else "используется общий или стандартный"
    await edit_menu(
        call,
        f"<b>{allowed[menu_key]}</b>\n\nТекущий баннер: {status}.",
        BotButtons.ADMIN_INLINE.menu_banner_actions(BotTexts, menu_key, custom is not None).as_markup(),
        menu_key,
    )


@adminRouter.callback_query(F.data.startswith("menu_banner:set:"))
async def menu_banner_set(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    menu_key = call.data.split(":", 2)[2]
    allowed = {item[0] for item in BotButtons.ADMIN_INLINE.BANNER_MENUS}
    if menu_key not in allowed:
        return await call.answer("Неизвестное меню", show_alert=True)
    await state.update_data(banner_menu_key=menu_key)
    await state.set_state(adminStates.AdminExtraButtons.enter_banner_media)
    await safe_edit_text(
        call.message,
        "Отправьте фотографию сообщением или вставьте прямую публичную HTTPS-ссылку на изображение.",
        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "menu_banners").as_markup(),
    )


@adminRouter.callback_query(F.data == "menu_banner:all")
async def menu_banner_all(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await state.update_data(banner_menu_key="all")
    await state.set_state(adminStates.AdminExtraButtons.enter_banner_media)
    await safe_edit_text(
        call.message,
        "Отправьте одну фотографию или прямую HTTPS-ссылку — этот баннер будет применён во всех меню.",
        BotButtons.ADMIN_INLINE.custom_button(BotTexts, "menu_banners").as_markup(),
    )


@adminRouter.callback_query(F.data.startswith("menu_banner:delete:"))
async def menu_banner_delete(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    menu_key = call.data.split(":", 2)[2]
    allowed = {item[0] for item in BotButtons.ADMIN_INLINE.BANNER_MENUS}
    if menu_key not in allowed:
        return await call.answer("Неизвестное меню", show_alert=True)
    await DB.delete_menu_banner(menu_key)
    await call.answer("Баннер меню сброшен", show_alert=True)
    await menu_banners(call, state, BotTexts)


@adminRouter.callback_query(F.data == "menu_banner:clear_all")
async def menu_banner_clear_all(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await DB.delete_all_menu_banners()
    await call.answer("Все баннеры сброшены", show_alert=True)
    await menu_banners(call, state, BotTexts)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_banner_media))
async def enter_banner_media(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.photo:
        media = msg.photo[-1].file_id
    elif msg.text:
        try:
            media = validate_banner_url(msg.text)
        except ValueError:
            return await msg.reply("Нужна фотография или публичная прямая HTTPS-ссылка без localhost и приватного IP.")
    else:
        return await msg.reply("Отправьте именно фотографию или HTTPS-ссылку.")
    menu_key = (await state.get_data()).get("banner_menu_key")
    if not menu_key:
        await state.clear()
        return await msg.reply("Сессия устарела. Откройте управление баннерами заново.")
    if menu_key == "all":
        keys = [item[0] for item in BotButtons.ADMIN_INLINE.BANNER_MENUS] + ["all"]
        await DB.replace_all_menu_banners(keys, media)
    else:
        await DB.set_menu_banner(menu_key, media)
    await state.clear()
    scope = "всех меню" if menu_key == "all" else "выбранного меню"
    await msg.answer(
        f"Баннер для {scope} сохранён.",
        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "menu_banners").as_markup(),
    )
    

@adminRouter.callback_query(F.data == "main_settings")
async def main_settings(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.main_settings_text, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.main_settings(BotTexts)).as_markup())


@adminRouter.callback_query(F.data.startswith("main_settings:"))
async def main_settings_edit(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    action = call.data.split(":")[1]
    settings = await DB.get_settings()

    if action == "currency":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_new_currency,
                                 reply_markup=BotButtons.ADMIN_INLINE.currencies_kb(BotTexts).as_markup())
    elif action =="default_lang":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_new_default_language,
                                 reply_markup=(await BotButtons.ADMIN_INLINE.langs_kb(BotTexts)).as_markup())
    elif action == "ref_percent":
        ref_lvl = call.data.split(":")[2]
        await state.update_data(ref_lvl=ref_lvl)
        await safe_edit_text(call.message, text=BotTexts.ADMIN_TEXTS.edit_main_setting.format(
            action=BotTexts.ADMIN_TEXTS.main_settings_values[f"ref_percent_{ref_lvl}"],
            value=settings.__dict__[f'ref_percent_{ref_lvl}'],
        ), reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "main_settings").as_markup())
    else:
        await safe_edit_text(call.message, text=BotTexts.ADMIN_TEXTS.edit_main_setting.format(
            action=BotTexts.ADMIN_TEXTS.main_settings_values[action],
            value=settings.__dict__[action],
        ), reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "main_settings").as_markup())
    await state.set_state(adminStates.AdminMainSettings.enter_new_value)
    await state.update_data(action=action)


@adminRouter.message(StateFilter(adminStates.AdminMainSettings.enter_new_value))
async def enter_new_value_main_settings(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = await state.get_data()
    await state.clear()
    if data['action'] == "ref_percent":
        data['action'] = f"ref_percent_{data['ref_lvl']}"
        value = int(msg.text)
    elif data['action'] == "faq":
        value = msg.html_text
    else:
        value = msg.text

    await DB.update_settings(**{data['action']: value})
    await msg.answer(BotTexts.ADMIN_TEXTS.main_settings_text, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.main_settings(BotTexts)).as_markup())


@adminRouter.callback_query(StateFilter(adminStates.AdminMainSettings.enter_new_value), F.data.startswith("edit_main_setting"))
async def edit_main_setting(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    action = (await state.get_data())['action']
    await state.clear()
    new_value = call.data.split(":")[1]
    await DB.update_settings(**{action: new_value})
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.main_settings_text, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.main_settings(BotTexts)).as_markup())
    

@adminRouter.callback_query(F.data == "mini_app_menu:toggle")
async def mini_app_menu_toggle(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    try:
        enabled = await toggle_mini_app_menu(DB, bot, BotConfig.WEBAPP_URL)
    except ValueError as error:
        await call.answer(str(error), show_alert=True)
        return
    except TelegramAPIError:
        await call.answer("Telegram не применил изменение. Настройка возвращена; повторите попытку.", show_alert=True)
        return
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_what_you_want_to_enable_disable,
                         reply_markup=(await BotButtons.ADMIN_INLINE.switchers_kb(BotTexts)).as_markup())
    await call.answer("Mini App включён в меню." if enabled else "Mini App скрыт. Старые меню обновятся после /start.", show_alert=True)


@adminRouter.callback_query(F.data == "switchers")
async def switchers(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_what_you_want_to_enable_disable,
                                 reply_markup=(await BotButtons.ADMIN_INLINE.switchers_kb(BotTexts)).as_markup())


@adminRouter.callback_query(F.data.startswith("switchers:"))
async def switchers_edit(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    action = call.data.split(":")[1]
    settings = await DB.get_settings()
    values = {
        models.Keyboards.Reply: models.Keyboards.Inline,
        models.Keyboards.Inline: models.Keyboards.Reply,
        False: True,
        True: False,
    }

    await DB.update_settings(**{action: values[settings.__dict__[action]]})
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_what_you_want_to_enable_disable,
                                 reply_markup=(await BotButtons.ADMIN_INLINE.switchers_kb(BotTexts)).as_markup())


@adminRouter.callback_query(F.data == "extra_settings")
async def extra_settings(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_action, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.extra_settings_kb(BotTexts)).as_markup())


@adminRouter.callback_query(F.data.startswith("extra_settings:"))
async def extra_settings_edit(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    action = call.data.split(":")[1]
    if action == "promo_create":
        await state.set_state(adminStates.AdminExtraSettings.enter_promo_name_for_create)
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_promo_name_for_create,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "extra_settings").as_markup())
    elif action == "promo_delete":
        await state.set_state(adminStates.AdminExtraSettings.enter_promo_name_for_delete)
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_promo_name_for_delete,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, 'extra_settings').as_markup())
    else:
        # ref_lvl
        ref_lvl = call.data.split(":")[2]
        await state.set_state(adminStates.AdminExtraSettings.enter_new_number_of_refs_for_ref_lvl)
        await state.update_data(ref_lvl=ref_lvl)
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_new_number_of_refs_for_ref_lvl.format(lvl=ref_lvl),
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "extra_settings").as_markup())


@adminRouter.message(StateFilter(adminStates.AdminExtraSettings.enter_promo_name_for_create))
async def enter_promo_name_for_create(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if await DB.get_promocode(name=msg.text):
        await msg.reply(BotTexts.ADMIN_TEXTS.this_promo_is_already_exists,
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "extra_settings").as_markup())
    else:
        await state.update_data(name=msg.text)
        await msg.reply(BotTexts.ADMIN_TEXTS.now_enter_number_of_uses_for_promo,
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "extra_settings:promo_create").as_markup())
        await state.set_state(adminStates.AdminExtraSettings.enter_promo_uses)


@adminRouter.message(StateFilter(adminStates.AdminExtraSettings.enter_promo_uses))
async def enter_promo_uses(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.isdigit():
        await state.update_data(uses=int(msg.text))
        await msg.reply(BotTexts.ADMIN_TEXTS.enter_discount_for_promo,
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "extra_settings:promo_create").as_markup())
        await state.set_state(adminStates.AdminExtraSettings.enter_promo_discount)
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_number)


@adminRouter.message(StateFilter(adminStates.AdminExtraSettings.enter_promo_discount))
async def enter_promo_discount(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.isdigit() or msg.text.replace(".", "").isdigit():
        data = await state.get_data()
        settings = await DB.get_settings()
        discounts = await utils.get_currency_amounts(float(msg.text), settings.currency.value)

        await DB.create_promocode(data['name'], data['uses'], discounts['rub'],
                                  discounts['usd'], discounts['eur'], discounts['amd'])
        await msg.reply(BotTexts.ADMIN_TEXTS.promo_is_created.format(
            name=data['name'],
            uses=data['uses'],
            discount=msg.text,
            curr=BotConfig.CURRENCIES[settings.currency.value]['sign'],
        ))
        await utils.send_admins("promo_is_created_alert",
            username=msg.from_user.mention_html(),
            name=data['name'],
            uses=data['uses'],
            discount=msg.text,
            curr=BotConfig.CURRENCIES[settings.currency]['sign'],
        )
        await msg.answer(BotTexts.ADMIN_TEXTS.choose_action, 
                                 reply_markup=(await BotButtons.ADMIN_INLINE.extra_settings_kb(BotTexts)).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_number)


@adminRouter.message(StateFilter(adminStates.AdminExtraSettings.enter_promo_name_for_delete))
async def enter_promo_name_for_delete(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if await DB.get_promocode(name=msg.text):
        await state.clear()
        await DB.delete_promocode(msg.text)
        await msg.reply(BotTexts.ADMIN_TEXTS.promo_is_deleted.format(name=msg.text))
        await utils.send_admins("promo_is_deleted_alert", username=msg.from_user.mention_html(), name=msg.text)
        await msg.answer(BotTexts.ADMIN_TEXTS.choose_action, 
                        reply_markup=(await BotButtons.ADMIN_INLINE.extra_settings_kb(BotTexts)).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.this_promo_is_not_exits)


@adminRouter.message(StateFilter(adminStates.AdminExtraSettings.enter_new_number_of_refs_for_ref_lvl))
async def enter_new_number_of_refs_for_ref_lvl(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.isdigit():
        ref_lvl = (await state.get_data())['ref_lvl']
        await state.clear()
        await DB.update_settings(**{f"ref_lvl_{ref_lvl}": int(msg.text)})
        await msg.reply(BotTexts.ADMIN_TEXTS.you_edit_number_of_refs_for_ref_lvl.format(
            lvl=ref_lvl,
            count=msg.text,
            convert=utils.numeral_noun_declension(int(msg.text), BotTexts.TEXTS.person_s)    
        ))
        await utils.send_admins("edit_number_of_refs_for_ref_lvl_alert",
            username=msg.from_user.mention_html(),
            lvl=ref_lvl,
            count=msg.text,
            convert=utils.numeral_noun_declension(int(msg.text), BotTexts.TEXTS.person_s) 
        )
        await msg.answer(BotTexts.ADMIN_TEXTS.choose_action, 
                        reply_markup=(await BotButtons.ADMIN_INLINE.extra_settings_kb(BotTexts)).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_number)


@adminRouter.callback_query(F.data == "ad_buttons")
async def ad_buttons(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_action,
                                 reply_markup=BotButtons.ADMIN_INLINE.ad_buttons_actions(BotTexts).as_markup())
    

@adminRouter.callback_query(F.data.startswith("ad_buttons:"))
async def ad_buttons_actions(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    if call.data.split(":")[1] == "create":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_name_for_create_ad_button,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "ad_buttons").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_name_for_create_ad_button)
    else:
        # delete
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_name_for_delete_ad_button,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "ad_buttons").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_name_for_delete_ad_button)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_name_for_create_ad_button))
async def enter_name_for_create_ad_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if len(msg.text) <= 64:
        await msg.reply(BotTexts.ADMIN_TEXTS.enter_content_for_ad_button,
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "ad_buttons:create").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_content_for_ad_button)
        await state.update_data(name=msg.text)
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.name_error)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_content_for_ad_button))
async def enter_content_for_ad_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if len(msg.text) <= 2000:
        await msg.reply(BotTexts.ADMIN_TEXTS.enter_photo_for_ad_button,
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "ad_buttons:create").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_photo_for_ad_button)
        await state.update_data(content=msg.html_text)
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.description_error)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_photo_for_ad_button), F.photo)
@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_photo_for_ad_button), F.text == "-")
async def enter_photo_for_ad_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await msg.reply(BotTexts.ADMIN_TEXTS.enter_links_buttons_for_ad_button,
                    reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "ad_buttons:create").as_markup())
    await state.set_state(adminStates.AdminExtraButtons.enter_links_buttons_for_ad_button)
    await state.update_data(photo=None if msg.text == "-" else msg.photo[-1].file_id)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_links_buttons_for_ad_button))
async def enter_links_buttons_for_ad_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = await state.get_data()
    await state.clear()
    await DB.add_ad_button(data['name'], data['content'], data['photo'], 
                           None if msg.text == "-" else msg.text)
    await utils.send_admins("ad_button_is_created_alert",
        username=msg.from_user.mention_html(),
        name=data['name'],
    )
    await msg.answer(BotTexts.ADMIN_TEXTS.welcome_to_the_admin_panel,
                     reply_markup=BotButtons.ADMIN_INLINE.admin_panel(BotTexts).as_markup())
    


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_name_for_delete_ad_button))
async def enter_name_for_delete_ad_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await DB.delete_ad_button(msg.text)
    await msg.reply(BotTexts.ADMIN_TEXTS.success)
    await utils.send_admins("ad_button_is_deleted_alert",
        username=msg.from_user.mention_html(),
        name=msg.text,
    )
    await msg.answer(BotTexts.ADMIN_TEXTS.choose_action,
                     reply_markup=BotButtons.ADMIN_INLINE.ad_buttons_actions(BotTexts).as_markup())


@adminRouter.callback_query(F.data == "mail_buttons")
async def mail_buttons(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.choose_action,
                                 reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
    

@adminRouter.callback_query(F.data.startswith("mail_buttons:"))
async def mail_buttons_actions(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    if call.data.split(":")[1] == "create":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_name_for_create_mail_button,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "mail_buttons").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_name_for_create_mail_button)
    else:
        # current
        buttons = await DB.get_mail_buttons()
        if buttons:
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_button, 
                                         reply_markup=BotButtons.ADMIN_INLINE.mail_buttons(BotTexts, buttons).as_markup())
        else:
            await call.answer(BotTexts.ADMIN_TEXTS.no_mail_buttons_available)


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_name_for_create_mail_button))
async def enter_name_for_create_mail_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if len(msg.text) <= 64:
        await msg.reply(BotTexts.ADMIN_TEXTS.select_mail_button_type,
                    reply_markup=BotButtons.ADMIN_INLINE.mail_button_types(BotTexts).as_markup())
        await state.set_state(adminStates.AdminExtraButtons.select_mail_button_type)
        await state.update_data(name=msg.text)
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.name_error)


@adminRouter.callback_query(F.data.startswith("mail_button_type:"), StateFilter(adminStates.AdminExtraButtons.select_mail_button_type))
async def select_mail_button_type(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    data = call.data.split(":")
    if data[1] == "link":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_link_for_mail_button,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "mail_buttons:create").as_markup())
        await state.set_state(adminStates.AdminExtraButtons.enter_link_for_create_mail_button)
    elif data[1] == "category":
        categories = await DB.get_all_categories()
        if categories:
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_category,
                                         reply_markup=BotButtons.ADMIN_INLINE.category_select_menu(BotTexts, categories).as_markup())
            await state.set_state(adminStates.AdminExtraButtons.select_category_for_open_category_button)
        else:
            await call.answer(BotTexts.ADMIN_TEXTS.no_categories_available)
    elif data[1] == "subcategory":
        categories = await DB.get_all_categories()
        if categories:
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_category,
                                         reply_markup=BotButtons.ADMIN_INLINE.category_select_menu(BotTexts, categories).as_markup())
            await state.set_state(adminStates.AdminExtraButtons.select_category_for_open_subcategory_button)
        else:
            await call.answer(BotTexts.ADMIN_TEXTS.no_categories_available)
    elif data[1] == "position":
        categories = await DB.get_all_categories()
        if categories:
            await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_category,
                                         reply_markup=BotButtons.ADMIN_INLINE.category_select_menu(BotTexts, categories).as_markup())
            await state.set_state(adminStates.AdminExtraButtons.select_category_for_open_position_button)
        else:
            await call.answer(BotTexts.ADMIN_TEXTS.no_categories_available)
    else:
        # contest
        contests = await DB.get_all_contests()
        if contests:
            await safe_edit_text(call.message, BotTexts.TEXTS.choose_contest,
                                         reply_markup=BotButtons.ADMIN_INLINE.choose_contest(BotTexts, contests).as_markup())
            await state.set_state(adminStates.AdminExtraButtons.select_contest_for_open_contest_button)
        else:
            await call.answer(BotTexts.TEXTS.no_contests)
    await state.update_data(mail_button_type=data[1])


@adminRouter.callback_query(F.data.startswith("choose_contest:"), StateFilter(adminStates.AdminExtraButtons.select_contest_for_open_contest_button))
async def select_contest_for_open_contest_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await DB.add_mail_button((await state.get_data())['name'], f"contest|{int(call.data.split(':')[1])}")
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.success)
    await call.message.answer(BotTexts.ADMIN_TEXTS.choose_action,
                              reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
    await state.clear()


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_link_for_create_mail_button))
async def enter_link_for_create_mail_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.startswith("https://") or msg.text.startswith("http://"):
        await DB.add_mail_button((await state.get_data())['name'], f"link|{msg.text}")
        await msg.reply(BotTexts.ADMIN_TEXTS.success)
        await msg.answer(BotTexts.ADMIN_TEXTS.choose_action,
                         reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
        await state.clear()
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_link)


@adminRouter.callback_query(F.data.startswith("select_category:"), StateFilter(adminStates.AdminExtraButtons.select_category_for_open_category_button))
async def select_category_for_open_category_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await DB.add_mail_button((await state.get_data())['name'], f"category|{int(call.data.split(':')[1])}")
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.success)
    await call.message.answer(BotTexts.ADMIN_TEXTS.choose_action,
                              reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
    await state.clear()


@adminRouter.callback_query(F.data.startswith("select_category:"), StateFilter(adminStates.AdminExtraButtons.select_category_for_open_subcategory_button))
async def select_category_for_open_subcategory_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    sub_categories = await DB.get_subcategories(cat_id=int(call.data.split(":")[1]))
    if sub_categories:
        await safe_edit_text(call.message, 
            BotTexts.ADMIN_TEXTS.select_subcategory,
            reply_markup=BotButtons.ADMIN_INLINE.subcategory_select_menu(BotTexts, subcategories=sub_categories).as_markup()
        )
        await state.set_state(adminStates.AdminExtraButtons.select_subcategory_for_open_subcategory_button)
    else:
        await call.answer(BotTexts.ADMIN_TEXTS.no_subcategories_available_in_this_category)


@adminRouter.callback_query(F.data.startswith("select_subcategory:"), StateFilter(adminStates.AdminExtraButtons.select_subcategory_for_open_subcategory_button))
async def select_subcategory_for_open_subcategory_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await DB.add_mail_button((await state.get_data())['name'], f"subcategory|{int(call.data.split(':')[1])}")
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.success)
    await call.message.answer(BotTexts.ADMIN_TEXTS.choose_action,
                              reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
    await state.clear()


@adminRouter.callback_query(F.data.startswith("select_category:"), StateFilter(adminStates.AdminExtraButtons.select_category_for_open_position_button))
async def select_category_for_open_position_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    positions = await DB.get_positions(cat_id=int(call.data.split(":")[1]), sub_cat_id=None)
    sub_categories = await DB.get_subcategories(cat_id=int(call.data.split(":")[1]))
    if sub_categories:
        await safe_edit_text(call.message, 
            BotTexts.ADMIN_TEXTS.select_subcategory,
            reply_markup=BotButtons.ADMIN_INLINE.subcategory_select_menu(BotTexts, subcategories=sub_categories, 
                                                                         positions=positions, is_for_edit_position=True).as_markup()
        )
        await state.set_state(adminStates.AdminExtraButtons.select_subcategory_for_open_position_button)
    else:
        if positions:
            await safe_edit_text(call.message, 
                BotTexts.ADMIN_TEXTS.select_position,
                reply_markup=BotButtons.ADMIN_INLINE.position_select_menu(BotTexts, positions).as_markup(),
            )
            await state.set_state(adminStates.AdminExtraButtons.select_position_for_open_position_button)
        else:
            await call.answer(BotTexts.ADMIN_TEXTS.no_positions_available_in_this_category)


@adminRouter.callback_query(F.data.startswith("select_subcategory:"), StateFilter(adminStates.AdminExtraButtons.select_subcategory_for_open_position_button))
async def select_subcategory_for_open_position_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    positions = await DB.get_positions(sub_cat_id=int(call.data.split(":")[1]))
    if positions:
        await safe_edit_text(call.message, 
            BotTexts.ADMIN_TEXTS.select_position,
            reply_markup=BotButtons.ADMIN_INLINE.position_select_menu(BotTexts, positions).as_markup(),
        )
        await state.set_state(adminStates.AdminExtraButtons.select_position_for_open_position_button)
    else:
        await call.answer(BotTexts.ADMIN_TEXTS.no_positions_available_in_this_subcategory)


@adminRouter.callback_query(F.data.startswith("select_position:"), StateFilter(adminStates.AdminExtraButtons.select_position_for_open_position_button, adminStates.AdminExtraButtons.select_subcategory_for_open_position_button))
async def select_position_for_open_position_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await DB.add_mail_button((await state.get_data())['name'], f"position|{int(call.data.split(':')[1])}")
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.success)
    await call.message.answer(BotTexts.ADMIN_TEXTS.choose_action,
                              reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())
    await state.clear()


@adminRouter.callback_query(F.data.startswith("edit_mail_button:"))
async def edit_mail_button(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    button = await DB.get_mail_button(int(call.data.split(":")[1]))
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.mail_button_text.format(name=button.name, 
                                                                              data=await get_data_for_mail_button(*button.button_type.split("|"))), 
                                 reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_edit(BotTexts, button.button_id).as_markup())
    

@adminRouter.callback_query(F.data.startswith("mail_button_edit:"))
async def mail_button_edit(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    data = call.data.split(":")
    button = await DB.get_mail_button(int(data[1]))

    if data[2] == "name":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_new_mail_button_name)
        await state.set_state(adminStates.AdminExtraButtons.enter_new_name_for_mail_button)
        await state.update_data(button=button)
    elif data[2] == "delete":
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.confirm_mail_button_delete.format(name=button.name),
                                  reply_markup=BotButtons.ADMIN_INLINE.confirm(f"mail_button_edit:{button.button_id}:del", 
                                                                               f"edit_mail_button:{button.button_id}").as_markup())
    else:
        # del
        await DB.delete_mail_button(button.button_id)
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.success)
        await call.message.answer(BotTexts.ADMIN_TEXTS.choose_action,
                                  reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_actions(BotTexts).as_markup())


@adminRouter.message(StateFilter(adminStates.AdminExtraButtons.enter_new_name_for_mail_button))
async def enter_new_name_for_mail_button(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if len(msg.text) <= 64:
        button = (await state.get_data())['button']
        await state.clear()
        await DB.update_mail_button(button.button_id, name=msg.text)
        await msg.reply(BotTexts.ADMIN_TEXTS.success)
        await msg.answer(BotTexts.ADMIN_TEXTS.mail_button_text.format(name=msg.text, 
                                                                      data=await get_data_for_mail_button(*button.button_type.split("|"))), 
                         reply_markup=BotButtons.ADMIN_INLINE.mail_buttons_edit(BotTexts, button.button_id).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.name_error)


@adminRouter.callback_query(F.data == "mail_start")
async def mail_start(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await call.message.delete()
    await call.message.answer(BotTexts.ADMIN_TEXTS.enter_message_for_mail,
                                 reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "admin_panel").as_markup())
    await state.set_state(adminStates.AdminOther.enter_message_for_mail)


@adminRouter.message(StateFilter(adminStates.AdminOther.enter_message_for_mail))
async def enter_message_for_mail(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await msg.reply(BotTexts.ADMIN_TEXTS.confirm_message_for_mail)
    await msg.copy_to(msg.chat.id, 
                      reply_markup=BotButtons.ADMIN_INLINE.confirm(f"confirm_mail_start", "mail_start").as_markup())
    await state.update_data(message=msg)


@adminRouter.callback_query(StateFilter(adminStates.AdminOther.enter_message_for_mail), F.data == "confirm_mail_start")
async def confirm_mail_start(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    try:
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.mail_started)
    except TelegramBadRequest:
        await call.message.delete()
        await call.message.answer(BotTexts.ADMIN_TEXTS.mail_started)
    success_users_count, failed_users_count = 0, 0
    users = await DB.all_users()
    await utils.send_admins("mail_started_alert", username=call.from_user.mention_html())
    try:
        message: Message = (await state.get_data())['message']
        for user in users:
            try:
                await message.copy_to(user.user_id, reply_markup=(await BotButtons.ADMIN_INLINE.buttons_for_mail(BotTexts)).as_markup())
                success_users_count += 1
            except TelegramForbiddenError:
                failed_users_count += 1
    except:
        print_exc()
        await call.message.answer(BotTexts.ADMIN_TEXTS.mail_error)
    finally:
        await call.message.answer(BotTexts.ADMIN_TEXTS.success_mail_text.format(
            all_users_count=len(users),
            success_users_count=success_users_count,
            failed_users_count=failed_users_count
        ))
        await state.clear()
    

@adminRouter.callback_query(F.data == "find")
async def find(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.select_what_you_want_to_find, 
                                 reply_markup=BotButtons.ADMIN_INLINE.find_settings(BotTexts).as_markup())


@adminRouter.callback_query(F.data.startswith("find:"))
async def find_callback(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    action = call.data.split(":")[1]
    if action == "profile":
        text = BotTexts.ADMIN_TEXTS.enter_user_profile
        await state.set_state(adminStates.AdminFind.enter_user_profile)
    else:
        # receipt
        text = BotTexts.ADMIN_TEXTS.enter_receipt
        await state.set_state(adminStates.AdminFind.enter_receipt)
    await safe_edit_text(call.message, text, reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find").as_markup())


@adminRouter.message(StateFilter(adminStates.AdminFind.enter_user_profile))
async def enter_user_profile(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.isdigit():
        params = {"user_id": int(msg.text)}
    elif msg.text.startswith("@"):
        params = {"user_name": msg.text.replace("@", "")}
    else:
        # full_name
        params = {"full_name": msg.text}
    user = await DB.get_user(**params)
    if user:
        await state.clear()
        await msg.reply(await get_user_profile(BotTexts, user),
                        reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, user.is_ban).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.no_user_find, 
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find").as_markup())
        
    
@adminRouter.callback_query(F.data.startswith("user_edit:"))
async def user_edit(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    _, action, user_id = call.data.split(":")
    user = await DB.get_user(user_id=int(user_id))
    if action == "balance":
        await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.edit_balance(BotTexts, user.user_id).as_markup())
    elif action == "back":
        await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, user.is_ban).as_markup())
    elif action == "ban":
        await DB.update_user(user.user_id, is_ban=True)
        await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, True).as_markup())
    elif action == "unban":
        await DB.update_user(user.user_id, is_ban=False)
        await call.message.edit_reply_markup(reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, False).as_markup())
    elif action in ["add_balance", "minus_balance", "edit_balance"]:
        match action:
            case "add_balance":
                await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_sum_for_add_to_balance,
                                             reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:profile").as_markup())
            case "minus_balance":
                await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_sum_for_minus_from_balance,
                                             reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:profile").as_markup())
            case "edit_balance":
                await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_sum_for_edit_balance,
                                             reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:profile").as_markup())
        await state.set_state(adminStates.AdminFind.enter_new_balance)
        await state.update_data(action=action, user=user)
    else:
        # sms
        await safe_edit_text(call.message, BotTexts.ADMIN_TEXTS.enter_sms_for_user,
                                     reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:profile").as_markup())
        await state.set_state(adminStates.AdminFind.enter_sms_for_user)
        await state.update_data(user=user)


@adminRouter.message(StateFilter(adminStates.AdminFind.enter_new_balance))
async def enter_new_balance(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    if msg.text.isdigit or msg.text.replace(".", "").isdigit():
        data = await state.get_data()
        await state.clear()
        settings = await DB.get_settings()
        balances = await utils.get_currency_amounts(float(msg.text), settings.currency.value)
        if data['action'] == "add_balance":
            await DB.update_user(data['user'].user_id, 
                                 **{f"balance_{code}": getattr(data['user'], f"balance_{code}") + value for code, value in balances.items()},
                                 )
        elif data['action'] == "minus_balance":
            await DB.update_user(data['user'].user_id, 
                                 **{f"balance_{code}": getattr(data['user'], f"balance_{code}") - value for code, value in balances.items()},
                                 )
        else:
            # edit_balance
            await DB.update_user(data['user'].user_id, 
                                 **{f"balance_{code}": value for code, value in balances.items()},
                                 )
            
        user = await DB.get_user(user_id=data['user'].user_id)
        await utils.send_admins("new_balance_alert",
            username=msg.from_user.mention_html(),
            user=f"<a href='tg://user?id={user.user_id}'>{user.full_name}</a>",
            )
        await msg.reply(await get_user_profile(BotTexts, user),
                        reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, user.is_ban).as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.value_is_no_number)
    

@adminRouter.message(StateFilter(adminStates.AdminFind.enter_sms_for_user))
async def enter_sms_for_user(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    user = (await state.get_data())['user']
    await state.clear()
    await msg.copy_to(user.user_id)
    await msg.reply(await get_user_profile(BotTexts, user),
                    reply_markup=BotButtons.ADMIN_INLINE.user_profile_actions(BotTexts, user.user_id, user.is_ban).as_markup())
    

@adminRouter.message(StateFilter(adminStates.AdminFind.enter_receipt))
async def enter_receipt(msg: Message, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    refill = await DB.get_refill(msg.text, True)
    purchase = await DB.get_purchase(receipt=msg.text)
    settings = await DB.get_settings()
    if refill:
        await state.clear()
        sum = refill.amount if settings.currency == models.Currencies.rub else await utils.get_exchange(
            refill.amount, "RUB", settings.currency.value.upper()
        )
        user = await DB.get_user(user_id=refill.user_id)
        
        try:
            way = BotTexts.TEXTS.payments_names[refill.way] if refill.way != "custom_pay_method" else settings.custom_pay_method
        except:
            way = refill.way
            
        await msg.reply(BotTexts.ADMIN_TEXTS.receipt_refill.format(
            receipt=msg.text,
            username=f"<a href='tg://user?id={user.user_id}'>{user.full_name}</a>",
            way=way,
            sum=sum,
            curr=BotConfig.CURRENCIES[settings.currency.value]["sign"],
            date=refill.date,
            url=refill.pay_url,
        ), reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:receipt").as_markup())
    elif purchase:
        await state.clear()
        price = getattr(purchase, f"price_{settings.currency.value}")
        position = await DB.get_position(pos_id=purchase.pos_id)
        user = await DB.get_user(user_id=purchase.user_id)
        await msg.reply(BotTexts.ADMIN_TEXTS.receipt_purchase.format(
            receipt=msg.text,
            username=f"<a href='tg://user?id={user.user_id}'>{user.full_name}</a>",
            pos_name=position.name,
            sum=price,
            curr=BotConfig.CURRENCIES[settings.currency.value]["sign"],
            date=purchase.date,
            count=purchase.count,
        ))
        await msg.answer(purchase.item,
                         reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:receipt").as_markup())
    else:
        await msg.reply(BotTexts.ADMIN_TEXTS.no_receipt, 
                        reply_markup=BotButtons.ADMIN_INLINE.custom_button(BotTexts, "find:receipt").as_markup())
        
@adminRouter.callback_query(F.data == "stats")
async def stats_open(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()

    refill_amount_all, refill_amount_day, refill_amount_week, refill_amount_month = 0, 0, 0, 0
    refill_count_all, refill_count_day, refill_count_week, refill_count_month = 0, 0, 0, 0
    profit_amount_all, profit_amount_day, profit_amount_week, profit_amount_month = 0, 0, 0, 0
    profit_count_all, profit_count_day, profit_count_week, profit_count_month = 0, 0, 0, 0
    users_all, users_day, users_week, users_month, users_money = 0, 0, 0, 0, 0

    all_purchases, all_refills, all_users, settings = await DB.get_data_for_stats()
    cur = BotConfig.CURRENCIES[settings.currency.value]['sign']
    today = datetime.datetime.today()
    month_timestamp = int(datetime.datetime(today.year, today.month, 1, 00, 00, 00).timestamp())

    for purchase in all_purchases:
        price = getattr(purchase, f"price_{settings.currency.value}")
                
        profit_count_all += purchase.count
        profit_amount_all += price
        
        if purchase.unix - settings.profit_day >= 0:
            profit_amount_day += price
            profit_count_day += purchase.count
        if purchase.unix - settings.profit_week >= 0:
            profit_amount_week += price
            profit_count_week += purchase.count
        if purchase.unix - month_timestamp >= 0:
            profit_amount_month += price
            profit_count_month += purchase.count

    for refill in all_refills:
        refill_amount = refill.amount if settings.currency == models.Currencies.rub else await utils.get_exchange(
            refill.amount, 'RUB', settings.currency.value.upper()
        )
            
        refill_amount_all += refill_amount
        refill_count_all += 1

        if refill.date_unix - settings.profit_day >= 0:
            refill_amount_day += refill_amount
            refill_count_day += 1
        if refill.date_unix - settings.profit_week >= 0:
            refill_amount_week += refill_amount
            refill_count_week += 1
        if refill.date_unix - month_timestamp >= 0:
            refill_amount_month += refill_amount
            refill_count_month += 1

    for user in all_users:
        user_balance = getattr(user, f"balance_{settings.currency.value}")
            
        users_money += user_balance
        users_all += 1

        if user.reg_date_unix - settings.profit_day >= 0:
            users_day += 1
        if user.reg_date_unix - settings.profit_week >= 0:
            users_week += 1
        if user.reg_date_unix - month_timestamp >= 0:
            users_month += 1

    msg = BotTexts.ADMIN_TEXTS.stats_message.format(
        users_day=users_day,
        users_week=users_week,
        users_month=users_month,
        users_all=users_all,
        cur=cur,
        users_money=round(users_money, 2),
        profit_count_day=profit_count_day,
        profit_amount_day=round(profit_amount_day, 2),
        profit_count_week=profit_count_week,
        profit_amount_week=round(profit_amount_week, 2),
        profit_count_month=profit_count_month,
        profit_amount_month=round(profit_amount_month, 2),
        profit_count_all=profit_count_all,
        profit_amount_all=round(profit_amount_all, 2),
        refill_count_day=refill_count_day,
        refill_amount_day=round(refill_amount_day, 2),
        refill_count_week=refill_count_week,
        refill_amount_week=round(refill_amount_week, 2),
        refill_count_month=refill_count_month,
        refill_amount_month=round(refill_amount_month, 2),
        refill_count_all=refill_count_all,
        refill_amount_all=round(refill_amount_all, 2),
        admins=len(BotConfig.ADMINS),
    )
    for admin_id in BotConfig.ADMINS:
        user = await DB.get_user(user_id=admin_id)
        msg += f"<b><a href='tg://user?id={user.user_id}'>{user.full_name}</a></b>\n"

    await safe_edit_text(call.message, msg, reply_markup=BotButtons.ADMIN_INLINE.stats_inl(BotTexts).as_markup())
    

@adminRouter.callback_query(F.data == "get_users_and_their_balances")
async def get_users_and_balances(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    msg = ""

    user_sum = await DB.get_sum_balances()
    if user_sum['rub'] == 0:
        return await call.answer(BotTexts.ADMIN_TEXTS.sum_is_zero_and_no_users_with_balance)
    users = await DB.all_users()

    for user in users:
        if user.balance_rub == 0:
            continue
        try:
            chat = await bot.get_chat(chat_id=user.user_id)
        except:
            continue
        msg += f"{chat.full_name} @{chat.username} (ID: {chat.id}) - {round(user.balance_rub, 2)}₽ | {round(user.balance_usd, 2)}$ | {round(user.balance_eur, 2)}€\n"

    with open('users_balances.txt', 'w', encoding="utf-8") as f:
        f.write(BotTexts.ADMIN_TEXTS.users_balances_txt_text.format(
            rub=round(user_sum['rub'], 2),
            usd=round(user_sum['usd'], 2),
            eur=round(user_sum['eur'], 2),
            users_balances=msg,
        ))
        f.close()

    await bot.send_document(call.message.chat.id, FSInputFile(f"users_balances.txt"), 
                            caption=BotTexts.ADMIN_TEXTS.all_users_and_their_balances)

    os.remove("users_balances.txt")
    await call.answer()
        

@adminRouter.callback_query(F.data == "get_users_ids")
async def get_users_ids(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru | BTs.En | BTs.Ua):
    await state.clear()
    users = await DB.all_users()

    with open("users_ids.txt", "w") as file:
        for user in users:
            file.write(f"{user.user_id}\n")
        file.close()

    await call.message.answer_document(document=FSInputFile(f"users_ids.txt"),
                                       caption=BotTexts.ADMIN_TEXTS.list_of_all_users_ids)

    os.remove("users_ids.txt")
    await call.answer()

