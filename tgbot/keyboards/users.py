from tgbot.utils.mini_app_menu import menu_enabled, valid_url
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
import telyx as tx
from tgbot.utils.digital_emoji import STARS_BUY_EMOJI_ID
from tgbot.utils.premium_emoji import storefront_ad_label
from tgbot.utils.storefront_branding import style_storefront_keyboard

from tgbot import utils
from tgbot.data import config as config_file

class InlineButtons:
    @staticmethod
    def telyx_button(icon, text, callback_data=None, url=None):
        return InlineKeyboardButton(**icon.button(text, callback_data=callback_data, url=url))

    async def profile_menu(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        
        if settings.is_ref:
            builder.add(
                InlineKeyboardButton(text=texts.BUTTONS.ref_system, callback_data="ref_system", icon_custom_emoji_id="6181676644504185221")
            )
            
        builder.row(
            InlineKeyboardButton(text=texts.BUTTONS.activate_promo, callback_data="activate_promo", icon_custom_emoji_id="6183777454742577008"),
            InlineKeyboardButton(text=texts.BUTTONS.purchases_history, callback_data="purchases_history", icon_custom_emoji_id="6181724391655613194")
        )
        # The customer storefront is Armenian-only; do not offer other languages.
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder

    async def support(self, texts):
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text=texts.BUTTONS.support_text,
                url=(await config_file.DB.get_settings()).support,
                icont_custom_emoji_id="5210970420215320683"
            )
        )
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder

    async def faq(self, texts):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        kb = []
        if settings.news and settings.news != "-":
            kb.append(
                InlineKeyboardButton(
                    text=texts.BUTTONS.faq_news_inl,
                    url=settings.news
                )
            )
        if settings.chat and settings.chat != "-":
            kb.append(
                InlineKeyboardButton(
                    text=texts.BUTTONS.faq_chat_inl,
                    url=settings.chat
                )
            )
        builder.add(*kb)
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder

    def close(self, texts):
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text=texts.BUTTONS.close,
                callback_data="close",
            )
        )

        return builder

    async def get_refill_kb(self, texts, payments):
        builder = InlineKeyboardBuilder()
        for payment in [payment for payment in payments if payment in {"cryptoBot", "xrocket", "stars", "custom_pay_method"}]:
            if payment == "custom_pay_method":
                settings = await config_file.DB.get_settings()
                builder.add(InlineKeyboardButton(
                    text=settings.custom_pay_method,
                    callback_data="refill:custom_pay_method",
                ))
            else:
                button_kwargs = {
                    "text": texts.TEXTS.payments_names[payment],
                    "callback_data": f"refill:{payment}",
                }
                builder.add(InlineKeyboardButton(**button_kwargs))
        builder.adjust(2)
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder

    def custom_button(self, texts, callback_data, name=None):
        if not name:
            name = texts.BUTTONS.back
        return InlineKeyboardBuilder().button(text=name, callback_data=callback_data)

    def refill_inl(self, texts, way, amount, url, pay_id, second_amount):
        builder = InlineKeyboardBuilder()
        builder.button(text=texts.BUTTONS.refill_link_inl, url=url)
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.refill_check_inl, callback_data=f"check_pay:{way}:{amount}:{pay_id}:{second_amount}"))
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.cancel, callback_data=f"cancel_pay:{pay_id}"))
        return builder
    
    def custom_pay_method_check(self, texts, pay_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=texts.BUTTONS.send_payment_to_check,
            callback_data=f"check_custom_pay_method:{pay_id}"
        ))
        builder.row(InlineKeyboardButton(
            text=texts.BUTTONS.cancel, 
            callback_data=f"cancel_pay:{pay_id}"
        ))
        return builder

    def ad_buttons_links_buttons(self, texts, links, is_back=False):
        try:
            builder = InlineKeyboardBuilder()
            if not links and is_back:
                builder.row(
                    self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu")
                )
                return builder.as_markup()
            links = links.split("\n")
            if links:
                for link in links:
                    try:
                        name, url = link.split("|")
                        try:
                            builder.row(InlineKeyboardButton(text=name, url=url.strip()))
                        except:
                            continue
                    except ValueError:
                        continue
                if is_back:
                    builder.row(
                        self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu")
                    )
                return builder.as_markup()
            else:
                name, url = links.split("|")
                if name and url:
                    try:
                        builder.row(InlineKeyboardButton(text=name, url=url.strip()))
                        if is_back:
                            builder.row(
                                self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu")
                            )
                        return builder.as_markup()
                    except:
                        return None
                else:
                    return None
        except:
            return None
        
    def select_category(self, texts, categories):
        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.add(InlineKeyboardButton(text=category.name, callback_data=f"open_category:{category.cat_id}"))
        builder.adjust(2)
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder

    async def select_subcategories_and_positions(self, texts, subcategories, positions):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()

        for sub_category in subcategories:
            builder.add(InlineKeyboardButton(text=sub_category.name, callback_data=f"open_subcategory:{sub_category.sub_cat_id}"))
        for position in positions:
            if position.sub_cat_id is not None:
                continue
            price = getattr(position, f"price_{settings.currency.value}")
            if position.is_infinity:
                items = texts.BUTTONS.nolimit
            else:
                items = f"{len(await config_file.DB.get_items(pos_id=position.pos_id))} {texts.BUTTONS.pcs}"
            builder.add(InlineKeyboardButton(text=texts.BUTTONS.position_button_name.format(
                name=position.name,
                price=price,
                curr=config_file.BotConfig.CURRENCIES[settings.currency.value]['sign'],
                items=items,
            ), callback_data=f"open_position:{position.pos_id}"))
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.back, callback_data=f"buy"))
        return builder

    async def select_positions(self, texts, positions):
        builder = InlineKeyboardBuilder()
        settings = await config_file.DB.get_settings()
        for position in positions:
            price = getattr(position, f"price_{settings.currency.value}")
            if position.is_infinity:
                items = texts.BUTTONS.nolimit
            else:
                items = f"{len(await config_file.DB.get_items(pos_id=position.pos_id))} {texts.BUTTONS.pcs}"
            builder.add(InlineKeyboardButton(text=texts.BUTTONS.position_button_name.format(
                name=position.name,
                price=price,
                curr=config_file.BotConfig.CURRENCIES[settings.currency.value]['sign'],
                items=items,
            ), callback_data=f"open_position:{position.pos_id}"))
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.back, callback_data=f"open_category:{positions[0].cat_id}"))
        return builder

    def position_buy(self, texts, position):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.buy, callback_data=f"buy_position:{position.pos_id}"))
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.back, callback_data=f"open_subcategory:{position.sub_cat_id}" if position.sub_cat_id else f"open_category:{position.cat_id}"))    
        return builder
    
    def confirm_buy_item(self, position_id, count):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Այո", callback_data=f"buy_item_confirm:{position_id}:{count}"),
                    InlineKeyboardButton(text="Ոչ", callback_data=f"open_position:{position_id}"))
        return builder
    
    def choose_contest(self, texts, contests):
        builder = InlineKeyboardBuilder()
        for contest in contests:
            end_time = utils.utils.get_time_for_end_contest(contest, texts.TEXTS.day_s)
            builder.row(InlineKeyboardButton(
                text=f"#{contest.contest_id} | {contest.prize}{config_file.BotConfig.CURRENCIES[contest.currency.value]['sign']} | {end_time}",
                callback_data=f"contest_view:{contest.contest_id}"
            ))
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder
    
    async def contest_inl(self, texts, contest, user):
        from tgbot.data.loader import bot

        builder = InlineKeyboardBuilder()
        purchases = (await config_file.DB.get_purchases_stats_for_user(user.user_id))['count_purchases']
        count_success, count_conditions, channels_count = 0, 0, 0

        if contest.refills_num > 0:
            count_conditions += 1
            if user.count_refills >= contest.refills_num:
                count_success += 1
        if contest.purchases_num > 0:
            count_conditions += 1
            if purchases >= contest.purchases_num:
                count_success += 1
        if len(utils.utils.get_channels(contest.channels_ids)) > 0:
            count_conditions += 1
            channels_ids = utils.utils.get_channels(contest.channels_ids)
            for channel_id in channels_ids:
                user_status = await bot.get_chat_member(chat_id=channel_id, user_id=user.user_id)
                if user_status.status != 'left':
                    channels_count += 1

            if channels_count == len(channels_ids):
                count_success += 1

        if count_success == count_conditions:
            builder.row(InlineKeyboardButton(text=texts.BUTTONS.contest_enter, 
                                             callback_data=f"contest_enter:{contest.contest_id}"))
        else:
            builder.row(InlineKeyboardButton(
                text=texts.BUTTONS.you_not_completed_all_conditions.format(
                    count=count_success,
                    count_conditions=count_conditions    
                ),
                callback_data="NONE", icon_custom_emoji_id="6181207762924478466"))
        builder.row(self.telyx_button(tx.arrow_left, texts.BUTTONS.back, "back_to_user_menu"))
        return builder
    
    def choose_language(self, texts):
        builder = InlineKeyboardBuilder()
        for language in config_file.BotConfig.LANGUAGES:
            builder.row(
                InlineKeyboardButton(
                    text=language['name'],
                    callback_data=f"change_language:{language['language']}"
                )
            )
        builder.row(InlineKeyboardButton(
            text=texts.BUTTONS.back,
            callback_data="profile"
        ))
        return builder
    
    async def sub_kb(self, texts, bot, channels):
        builder = InlineKeyboardBuilder()
        for channel_id in channels:
            channel = await bot.get_chat(chat_id=channel_id)
            try:
                link = "https://t.me/" + channel.username
            except:
                try:
                    link = channel.invite_link
                except:
                    link = (await bot.create_chat_invite_link(chat_id=channel_id)).invite_link
            builder.row(InlineKeyboardButton(text=channel.title, url=link))
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.check_sub, callback_data="check_sub"))
        return builder

    def mandatory_sub_kb(self, texts, channels):
        builder = InlineKeyboardBuilder()
        for channel in channels:
            builder.row(InlineKeyboardButton(text=channel.title, url=channel.invite_link))
        builder.row(InlineKeyboardButton(text=texts.BUTTONS.check_sub, callback_data="check_sub"))
        return builder
    

class ReplyButtons:
    async def main_menu(self, texts, user_id, admins):
        settings = await config_file.DB.get_settings()
        ad_buttons = await config_file.DB.get_ad_buttons()
        if settings.keyboard.value == "Reply":
            kb_extra = [KeyboardButton(text=texts.BUTTONS.support)]
            if settings.faq and settings.faq != "-":
                kb_extra.insert(0, KeyboardButton(text=texts.BUTTONS.faq))
            kb = [
                [KeyboardButton(text=texts.BUTTONS.buy), KeyboardButton(text=texts.BUTTONS.profile)],
                [KeyboardButton(text="⭐ Stars & Premium")],
                kb_extra,
                [KeyboardButton(text=texts.BUTTONS.topup_balance)]
            ]
            if menu_enabled(settings) and valid_url(config_file.BotConfig.WEBAPP_URL):
                kb.insert(0, [KeyboardButton(text="Mini App", web_app=WebAppInfo(url=config_file.BotConfig.WEBAPP_URL))])
            if settings.contests_is_on:
                kb.append([KeyboardButton(text=texts.BUTTONS.contests)])
            if user_id in admins:
                kb.append([KeyboardButton(text=texts.BUTTONS.admin_panel),])
            
            for button in ad_buttons:
                kb.append([KeyboardButton(text=storefront_ad_label(button.name))])

            keyboard = ReplyKeyboardMarkup(
                keyboard=kb,
                resize_keyboard=True,
                input_field_placeholder=texts.BUTTONS.choose_action
            )
        else:
            builder = InlineKeyboardBuilder()
            if menu_enabled(settings) and valid_url(config_file.BotConfig.WEBAPP_URL):
                builder.row(InlineKeyboardButton(
                    text="Mini App",
                    web_app=WebAppInfo(url=config_file.BotConfig.WEBAPP_URL),
                ))
            builder.row(
                InlineButtons.telyx_button(tx.shopping_cart, texts.BUTTONS.buy, "buy"),
                InlineButtons.telyx_button(tx.user, texts.BUTTONS.profile, "profile")
            )
            builder.row(InlineKeyboardButton(
                text="Stars & Premium",
                callback_data="digital:home",
                icon_custom_emoji_id=STARS_BUY_EMOJI_ID,
            ))
            kb_extra = [InlineButtons.telyx_button(tx.user, texts.BUTTONS.support, "support")]
            if settings.faq and settings.faq != "-":
                kb_extra.insert(0, InlineButtons.telyx_button(tx.settings, texts.BUTTONS.faq, "faq"))
            builder.row(*kb_extra)
            builder.row(InlineButtons.telyx_button(tx.wallet, texts.BUTTONS.topup_balance, "refill"))
            if settings.contests_is_on:
                builder.row(InlineButtons.telyx_button(tx.chart_bar, texts.BUTTONS.contests, "contests"))
            if user_id in admins:
                builder.row(InlineButtons.telyx_button(tx.settings, texts.BUTTONS.admin_panel, "admin_panel"))

            for button in ad_buttons:
                builder.row(InlineButtons.telyx_button(tx.package, storefront_ad_label(button.name), f"ad_button_open:{button.button_id}"))

            keyboard = builder.as_markup()

        return style_storefront_keyboard(keyboard)
    
    
