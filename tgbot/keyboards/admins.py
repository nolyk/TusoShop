from tgbot.utils.catalog_emoji import catalog_button_name
from tgbot.utils.mini_app_menu import menu_enabled
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import telyx as tx
from tgbot.utils.digital_emoji import STARS_BUY_EMOJI_ID

from tgbot.data import config as config_file
from tgbot import utils


class InlineButtons:

    BANNER_MENUS = (
        ("main", "Главное меню", tx.settings),
        ("buy", "Каталог", tx.shopping_cart),
        ("profile", "Профиль", tx.user),
        ("refill", "Пополнение", tx.wallet),
        ("support", "Поддержка", tx.user),
        ("faq", "FAQ", tx.settings),
        ("contests", "Конкурсы", tx.chart_bar),
        ("admin", "Админ-панель", tx.settings),
    )

    @staticmethod
    def telyx_button(icon, text, callback_data=None, url=None):
        return InlineKeyboardButton(**icon.button(text, callback_data=callback_data, url=url))

    def custom_button(self, texts, callback_data, name=None):
        if not name:
            name = texts.BUTTONS.back
        return InlineKeyboardBuilder().button(text=name, callback_data=callback_data)
    
    def admin_panel(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(
            self.telyx_button(tx.settings, texts.ADMIN_TEXTS.main_settings, "main_settings"),
            self.telyx_button(tx.settings, texts.ADMIN_TEXTS.extra_settings, "extra_settings"),
        )
        builder.row(
            self.telyx_button(tx.settings, texts.ADMIN_TEXTS.switchers, "switchers"),
            self.telyx_button(tx.settings, texts.ADMIN_TEXTS.find, "find"),
        )
        builder.row(self.telyx_button(tx.chart_bar, texts.ADMIN_TEXTS.statistic, "stats"))
        builder.row(
            self.telyx_button(tx.shopping_cart, texts.ADMIN_TEXTS.products_manage, "products_manage"),
            self.telyx_button(tx.wallet, texts.ADMIN_TEXTS.payments_systems, "payments"),
        )
        builder.row(
            self.telyx_button(tx.megaphone, texts.ADMIN_TEXTS.mail, "mail_start"),
            self.telyx_button(tx.package, texts.ADMIN_TEXTS.mail_buttons, "mail_buttons"),
        )
        builder.row(self.telyx_button(tx.package, texts.ADMIN_TEXTS.ad_buttons, "ad_buttons"))
        builder.row(self.telyx_button(tx.megaphone, texts.ADMIN_TEXTS.mandatory_subscriptions, "mandatory_channels"))
        builder.row(self.telyx_button(tx.package, "Баннеры меню", "menu_banners"))
        builder.row(InlineKeyboardButton(
            text="Stars / Premium",
            callback_data="digital_admin:home",
            icon_custom_emoji_id=STARS_BUY_EMOJI_ID,
        ))
        builder.row(self.telyx_button(tx.chart_bar, texts.ADMIN_TEXTS.contests, "contests_admin"))
        builder.row(self.telyx_button(tx.settings, texts.ADMIN_TEXTS.back, "back_to_user_menu"))
        return builder

    def menu_banners(self, texts, configured=(), global_enabled=False):
        builder = InlineKeyboardBuilder()
        configured = set(configured)
        for menu_key, label, icon in self.BANNER_MENUS:
            status = " · задан" if menu_key in configured else ""
            builder.add(self.telyx_button(icon, label + status, f"menu_banner:open:{menu_key}"))
        builder.adjust(2)
        global_text = "Изменить общий баннер" if global_enabled else "Применить баннер везде"
        builder.row(self.telyx_button(tx.circle_check, global_text, "menu_banner:all"))
        if global_enabled:
            builder.row(self.telyx_button(tx.settings, "Сбросить общий баннер", "menu_banner:clear_all"))
        builder.row(self.telyx_button(tx.settings, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder

    def menu_banner_actions(self, texts, menu_key, is_custom=False):
        builder = InlineKeyboardBuilder()
        builder.row(self.telyx_button(tx.package, "Загрузить фото или ссылку", f"menu_banner:set:{menu_key}"))
        if is_custom:
            builder.row(self.telyx_button(tx.settings, "Сбросить баннер меню", f"menu_banner:delete:{menu_key}"))
        builder.row(self.telyx_button(tx.settings, texts.ADMIN_TEXTS.back, "menu_banners"))
        return builder
    
    async def switchers_kb(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        builder.row(InlineKeyboardButton(
            text=f"Mini App в меню | {'ON' if menu_enabled(settings) else 'OFF'}",
            callback_data="mini_app_menu:toggle", icon_custom_emoji_id="6181221171812377434"))
        builder.row(
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['tech_works']} | {'ON' if settings.is_work else 'OFF'}", callback_data="switchers:is_work"),
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['buys']} | {'ON' if settings.is_buy else 'OFF'}", callback_data="switchers:is_buy"),
        )
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['refills']} | {'ON' if settings.is_refill else 'OFF'}", callback_data="switchers:is_refill"))
        builder.row(
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['ref']} | {'ON' if settings.is_ref else 'OFF'}", callback_data="switchers:is_ref"),
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['contests']} | {'ON' if settings.contests_is_on else 'OFF'}", callback_data="switchers:contests_is_on"),
        )
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['notify']} | {'ON' if settings.is_notify else 'OFF'}", callback_data="switchers:is_notify"))
        builder.row(
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['keyboard']} | {settings.keyboard.value}", callback_data="switchers:keyboard"),
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['sub']} | {'ON' if settings.is_sub else 'OFF'}", callback_data="switchers:is_sub"),
        )
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.switchers_settings['multi_lang']} | {'ON' if settings.multi_lang else 'OFF'}", callback_data="switchers:multi_lang"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    async def main_settings(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        builder.row(
            InlineKeyboardButton(text=f"FAQ | {'OFF' if settings.faq is None or settings.faq in ['-', 'None'] else 'ON'}", callback_data="main_settings:faq"),
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['support']} | {'OFF' if settings.support is None or settings.support in ['-', 'None'] else 'ON'}", callback_data="main_settings:support"),
        )
        builder.row(
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['chat']} | {'OFF' if settings.chat is None or settings.chat in ['-', 'None'] else 'ON'}", callback_data="main_settings:chat"),
            InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['news']} | {'OFF' if settings.news is None or settings.news in ['-', 'None'] else 'ON'}", callback_data="main_settings:news"),
        )
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['ref_percent_1']} | {settings.ref_percent_1}%", callback_data="main_settings:ref_percent:1"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['ref_percent_2']} | {settings.ref_percent_2}%", callback_data="main_settings:ref_percent:2"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['ref_percent_3']} | {settings.ref_percent_3}%", callback_data="main_settings:ref_percent:3"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['default_lang']} | {(next((language for language in config_file.BotConfig.LANGUAGES if language['language'] == settings.default_lang.value), None))['name']}", callback_data="main_settings:default_lang"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.main_settings_values['currency']} | {config_file.BotConfig.CURRENCIES[settings.currency.value]['sign']}", callback_data="main_settings:currency"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def currencies_kb(self, texts):
        builder = InlineKeyboardBuilder()
        currencies = config_file.BotConfig.CURRENCIES
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.currencies['rub']} | {currencies['rub']['text']} | {currencies['rub']['sign']}",
                                callback_data="edit_main_setting:rub"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.currencies['usd']} | {currencies['usd']['text']} | {currencies['usd']['sign']}",
                                callback_data="edit_main_setting:usd"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.currencies['eur']} | {currencies['eur']['text']} | {currencies['eur']['sign']}",
                                callback_data="edit_main_setting:eur"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.currencies['amd']} | {currencies['amd']['text']} | {currencies['amd']['sign']}",
                                callback_data="edit_main_setting:amd"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "main_settings"))
        return builder

    async def langs_kb(self, texts):
        builder = InlineKeyboardBuilder()
        for lang in config_file.BotConfig.LANGUAGES:
            builder.row(InlineKeyboardButton(text=lang['name'], callback_data=f"edit_main_setting:{lang['language']}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "main_settings"))
        return builder
    
    async def extra_settings_kb(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.create_promocode, callback_data="extra_settings:promo_create"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete_promocode, callback_data="extra_settings:promo_delete"),
        )
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.edit_number_of_refs_for_ref_lvl_2} | {settings.ref_lvl_2}", 
                                         callback_data="extra_settings:ref_lvl:2"))
        builder.row(InlineKeyboardButton(text=f"{texts.ADMIN_TEXTS.edit_number_of_refs_for_ref_lvl_3} | {settings.ref_lvl_3}",
                                         callback_data="extra_settings:ref_lvl:3"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder 

    def products_manage(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.add_category, callback_data=f"add_category"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.edit_category, callback_data=f"edit_category"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.del_all_categories, callback_data=f"del_all_categories"),
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.add_subcategory, callback_data=f"add_subcategory"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.edit_subcategory, callback_data=f"edit_subcategory"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.del_all_subcategories, callback_data=f"del_all_subcategories"),
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.add_position, callback_data=f"add_position"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.edit_position, callback_data=f"edit_position"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.del_all_positions, callback_data=f"del_all_positions"),
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.add_items, callback_data=f"add_items"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.del_item, callback_data=f"del_item"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.del_all_items, callback_data=f"del_all_items"),
        )
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def category_select_menu(self, texts, categories):
        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.row(InlineKeyboardButton(text=catalog_button_name(category), callback_data=f"select_category:{category.cat_id}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def subcategory_select_menu(self, texts, subcategories, is_for_add_position=False, is_for_edit_position=False, positions=None):
        builder = InlineKeyboardBuilder()
        for subcategory in subcategories:
            builder.row(InlineKeyboardButton(text=catalog_button_name(subcategory), callback_data=f"select_subcategory:{subcategory.sub_cat_id}"))
        if is_for_edit_position:
            builder = self.position_select_menu(texts, positions, builder)
        if is_for_add_position:
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.select_this_category, callback_data=f"select_category:{subcategories[0].cat_id}:this"))
        if not is_for_edit_position:
            builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def position_select_menu(self, texts, positions, builder=None):
        if not builder:
            builder = InlineKeyboardBuilder()
        for position in positions:
            builder.row(InlineKeyboardButton(text=catalog_button_name(position), callback_data=f"select_position:{position.pos_id}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder

    def category_edit(self, texts, category_id, is_sub=False):
        builder = InlineKeyboardBuilder()
        if is_sub:
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.name, callback_data=f"edit_subcategory:{category_id}:name"))
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete, callback_data=f"edit_subcategory:{category_id}:delete"))
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.move, callback_data=f"edit_subcategory:{category_id}:move"))
        else:
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.name, callback_data=f"edit_category:{category_id}:name"))
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete, callback_data=f"edit_category:{category_id}:delete"))

        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def position_edit(self, texts, position_id):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.price, callback_data=f"position_edit:{position_id}:price"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.name, callback_data=f"position_edit:{position_id}:name")
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.description, callback_data=f"position_edit:{position_id}:description"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.photo, callback_data=f"position_edit:{position_id}:photo"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.position_type_text, callback_data=f"position_edit:{position_id}:position_type"),
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete, callback_data=f"position_edit:{position_id}:delete"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.move, callback_data=f"position_edit:{position_id}:move")
        )
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.clear_items, callback_data=f"position_edit:{position_id}:clear_items"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.upload_items, callback_data=f"position_edit:{position_id}:upload_items")
        )
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.get_items, callback_data=f"position_edit:{position_id}:get_items"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "edit_position"))
        return builder

    def confirm(self, callback_data1, callback_data2):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Да", callback_data=callback_data1),
                    InlineKeyboardButton(text="Нет", callback_data=callback_data2))
        return builder
    
    def position_item_types(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=f"📦 {texts.ADMIN_TEXTS.position_type['mixed']}", callback_data="select_position_type:mixed"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.photo, callback_data=f"select_position_type:photo"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.text, callback_data=f"select_position_type:text"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.file_, callback_data=f"select_position_type:file"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "products_manage"))
        return builder
    
    def ad_buttons_actions(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.create, callback_data="ad_buttons:create"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete, callback_data="ad_buttons:delete"),
        )
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def mail_buttons_actions(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.create, callback_data="mail_buttons:create"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.current_buttons, callback_data="mail_buttons:current"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def mail_button_types(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.open_category_button, callback_data="mail_button_type:category"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.open_subcategory_button, callback_data="mail_button_type:subcategory"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.open_position_button, callback_data="mail_button_type:position"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.open_contest_button, callback_data="mail_button_type:contest"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.link_button, callback_data="mail_button_type:link"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "mail_buttons"))
        return builder

    def mail_buttons(self, texts, buttons):
        builder = InlineKeyboardBuilder()
        for button in buttons:
            builder.row(InlineKeyboardButton(text=f"{button.name} | {texts.ADMIN_TEXTS.mail_buttons_types[button.button_type.split('|')[0]]}",
                                             callback_data=f"edit_mail_button:{button.button_id}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "mail_buttons"))
        return builder
    
    def mail_buttons_edit(self, texts, button_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.name, callback_data=f"mail_button_edit:{button_id}:name"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.delete, callback_data=f"mail_button_edit:{button_id}:delete"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "mail_buttons:current"))
        return builder
    
    async def buttons_for_mail(self, texts):
        builder = InlineKeyboardBuilder()
        buttons = await config_file.DB.get_mail_buttons()
        for button in buttons:
            button_type, value = button.button_type.split("|")
            if button_type == "link":
                builder.row(InlineKeyboardButton(text=button.name, url=value.strip()))
            elif button_type == "category":
                builder.row(InlineKeyboardButton(text=button.name, callback_data=f"mail_category_open:{value}"))
            elif button_type == "subcategory":
                builder.row(InlineKeyboardButton(text=button.name, callback_data=f"mail_subcategory_open:{value}"))
            elif button_type == "position":
                builder.row(InlineKeyboardButton(text=button.name, callback_data=f"mail_position_open:{value}"))
            else:
                # contest
                builder.row(InlineKeyboardButton(text=button.name, callback_data=f"mail_contest_open:{value}"))
        return builder
    
    def find_settings(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.profile, callback_data="find:profile"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.receipt, callback_data="find:receipt"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder

    def user_profile_actions(self, texts, user_id, is_ban):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.edit_balance, callback_data=f"user_edit:balance:{user_id}"))
        if is_ban:
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.unban, callback_data=f"user_edit:unban:{user_id}"))
        else:
            builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.ban, callback_data=f"user_edit:ban:{user_id}"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.send_message, callback_data=f"user_edit:sms:{user_id}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "find:profile"))
        return builder
    
    def edit_balance(self, texts, user_id):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.add_balance, callback_data=f"user_edit:add_balance:{user_id}"),
            InlineKeyboardButton(text=texts.ADMIN_TEXTS.minus_balance, callback_data=f"user_edit:minus_balance:{user_id}")
        )
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.edit_bal, callback_data=f"user_edit:edit_balance:{user_id}"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, f"user_edit:back:{user_id}"))
        return builder
    
    async def payments_settings(self, texts, payments: dict):
        builder = InlineKeyboardBuilder()
        for payment in payments.items():
            if payment[0] == "custom_pay_method":
                settings = await config_file.DB.get_settings()
                builder.add(InlineKeyboardButton(
                    text=f"[{'ON' if settings.is_custom_pay_method_on else 'OFF'}] {settings.custom_pay_method}",
                    callback_data=f"payments:custom_pay_method"
                    
                ))
            else:
                builder.add(
                    InlineKeyboardButton(
                        text=f"[{'ON' if payment[1] else 'OFF'}] {texts.TEXTS.payments_names[payment[0]]}",
                        callback_data=f"payments:{payment[0]}",
                    )
                )
        builder.adjust(2)
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    def payments_settings_info(self, texts, method, status, custom_pay_method_is_receipt_on = None):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.disable if status else texts.ADMIN_TEXTS.enable,
                                         callback_data=f"payment_action:{method}:enable_or_disable"))
        if method == "stars":
            builder.row(InlineKeyboardButton(
                text=texts.ADMIN_TEXTS.edit_stars_rate,
                callback_data="payment_action:stars:rate"
            ))
        elif method == "custom_pay_method":
            builder.row(InlineKeyboardButton(
                text=texts.ADMIN_TEXTS.edit_custom_pay_method_receipt.format(status="ON" if custom_pay_method_is_receipt_on else 'OFF'),
                callback_data="payment_action:custom_pay_method:receipt"
            ))
            builder.row(InlineKeyboardButton(
                text=texts.ADMIN_TEXTS.edit_custom_pay_method_name,
                callback_data="payment_action:custom_pay_method:name"
            ))
            builder.row(InlineKeyboardButton(
                text=texts.ADMIN_TEXTS.edit_custom_pay_method_text,
                callback_data="payment_action:custom_pay_method:text"
            ))
            builder.row(InlineKeyboardButton(
                text=getattr(texts.ADMIN_TEXTS, "custom_pay_cards", "💳 Карты для переводов"),
                callback_data="custom_pay_cards"
            ))
            builder.row(InlineKeyboardButton(
                text=texts.ADMIN_TEXTS.edit_custom_pay_method_min_amount,
                callback_data="payment_action:custom_pay_method:min"
            ))
        else:
            builder.row(
                InlineKeyboardButton(text=texts.ADMIN_TEXTS.get_balance, callback_data=f"payment_action:{method}:balance"),
                InlineKeyboardButton(text=texts.ADMIN_TEXTS.show_info, callback_data=f"payment_action:{method}:info")
            )
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "payments"))
        return builder

    def custom_pay_cards(self, texts, cards):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=getattr(texts.ADMIN_TEXTS, "add_custom_pay_card", "➕ Добавить карту"),
            callback_data="custom_pay_card:add",
        ))
        for card in cards:
            status = "✅" if card.is_active else "❌"
            builder.row(InlineKeyboardButton(
                text=f"{status} #{card.card_id} · {card.bank_name} · {card.holder_name}",
                callback_data=f"custom_pay_card:view:{card.card_id}",
            ))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "payments:custom_pay_method"))
        return builder

    def custom_pay_card_manage(self, texts, card):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=getattr(texts.ADMIN_TEXTS, "edit_custom_pay_card", "✏️ Изменить карту"),
            callback_data=f"custom_pay_card:edit:{card.card_id}",
        ))
        builder.row(InlineKeyboardButton(
            text=("❌ Выключить" if card.is_active else "✅ Включить"),
            callback_data=f"custom_pay_card:toggle:{card.card_id}",
        ))
        builder.row(InlineKeyboardButton(
            text=texts.ADMIN_TEXTS.delete,
            callback_data=f"custom_pay_card:delete:{card.card_id}",
        ))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "custom_pay_cards"))
        return builder

    async def mandatory_channels(self, texts, channels, bot_username):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=texts.ADMIN_TEXTS.add_bot_to_channel,
            url=f"https://t.me/{bot_username}?startchannel&admin=invite_users"
        ))
        builder.row(InlineKeyboardButton(
            text=texts.ADMIN_TEXTS.add_mandatory_channel,
            callback_data="mandatory_channel:add"
        ))
        for channel in channels:
            status = "✅" if channel.enabled else "❌"
            builder.row(InlineKeyboardButton(
                text=f"{status} {channel.title}",
                callback_data=f"mandatory_channel:view:{channel.channel_id}"
            ))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder

    def mandatory_channel_manage(self, texts, channel):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=texts.ADMIN_TEXTS.channel_disabled if channel.enabled else texts.ADMIN_TEXTS.channel_enabled,
            callback_data=f"mandatory_channel:toggle:{channel.channel_id}"
        ))
        builder.row(InlineKeyboardButton(
            text=texts.ADMIN_TEXTS.delete,
            callback_data=f"mandatory_channel:delete:{channel.channel_id}"
        ))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "mandatory_channels"))
        return builder
    
    def payments_info(self, texts, payments_config, method):
        builder = InlineKeyboardBuilder()
        for cfg in payments_config:
            builder.add(
                InlineKeyboardButton(
                    text=cfg.text, 
                    callback_data=f"payment_action:{method}:edit_cfg:{cfg.field}"
                )
            )
        builder.adjust(2)
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, f"payments:{method}"))
        return builder

    def stats_inl(self, texts):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.get_users_and_their_balances, 
                                         callback_data="get_users_and_their_balances"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.get_users_ids, 
                                         callback_data="get_users_ids"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "admin_panel"))
        return builder
    
    async def contests_inl(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_contests_settings()
        cur = config_file.BotConfig.CURRENCIES[(await config_file.DB.get_settings()).currency.value]['sign']
        
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.winners_count} | {settings.winners_num}',
                                         callback_data="edit_contest_settings:winners_num"))
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.prize} | {settings.prize}{cur}',
                                         callback_data="edit_contest_settings:prize"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.conditions, callback_data="edit_contest_settings:conditions"))
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.members_count} | {settings.members_num}',
                                         callback_data="edit_contest_settings:members_num"))
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.contest_time} | {settings.end_time}',
                                         callback_data="edit_contest_settings:end_time"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.end_contest_now, callback_data="cancel_contest_now"))
        builder.row(InlineKeyboardButton(text=texts.ADMIN_TEXTS.start_contest, callback_data='start_contest'))

        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, 'admin_panel'))
        return builder
    
    async def contests_conditions_inl(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_contests_settings()
        
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.purchases_count} | {settings.purchases_num}',
                                         callback_data="edit_contest_settings:purchases_num"))
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.refills_count} | {settings.refills_num}',
                                         callback_data="edit_contest_settings:refills_num"))
        builder.row(InlineKeyboardButton(text=f'{texts.ADMIN_TEXTS.channels_ids_for_sub} {len(utils.utils.get_channels(settings.channels_ids))}',
                                         callback_data="edit_contest_settings:channels_ids"))
        builder.row(self.telyx_button(tx.arrow_left, texts.ADMIN_TEXTS.back, "contests_admin"))
        return builder
    
    def choose_contest(self, texts, contests, is_for_cancel = False):
        builder = InlineKeyboardBuilder()
        for contest in contests:
            end_time = utils.utils.get_time_for_end_contest(contest, texts.TEXTS.day_s)
            builder.row(InlineKeyboardButton(
                text=f"#{contest.contest_id} | {contest.prize}{config_file.BotConfig.CURRENCIES[contest.currency.value]['sign']} | {end_time}",
                callback_data=f"cancel_contest_confirm:{contest.contest_id}:yes" if is_for_cancel else f"choose_contest:{contest.contest_id}"
            ))
            
        return builder
