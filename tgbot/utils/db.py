from tgbot import utils
from tgbot.utils import models

from sqlalchemy import select, update, delete, insert, func, funcfilter, desc

import math
import datetime

PAYMENTS_CONFIG_FIELDS = {
    "lolz": ["lolz_token", "lolz_merchant_id"],
    "cryptoBot": ['crypto_token'],
    "xrocket": ["xrocket_token", "xrocket_asset"],
    'lava': ['lava_secret_key', "lava_project_id"],
    'aaio': ['aaio_api_key', "aaio_shop_id", 'aaio_secret_key_1'],
    'yoomoney': ["yoomoney_token", "yoomoney_number"],
    'cryptomus': ["payment_api_key", "merchant_id"]
}

class DataBase:
    async def get_user(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.User).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()

    async def register_user(self, user_id, user_name, full_name):
        async with models.async_session() as session:
            await session.execute(insert(models.User).values(
                user_id=user_id,
                user_name=user_name,
                full_name=full_name,
                reg_date=utils.utils.get_date(),
                reg_date_unix=utils.utils.get_unix(),
            ))
            await session.commit()

    # Редактирование пользователя
    async def update_user(self, user_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.User).where(models.User.user_id == user_id).values(**kwargs))
            await session.commit()

    # Удаление пользователя из БД
    async def delete_user(self, user_id):
        async with models.async_session() as session:
            await session.execute(delete(models.User).where(models.User.user_id == user_id))
            await session.commit()

    # Получение всех пользователей из БД
    async def all_users(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.User))).scalars().all()

    ##############################################################################################
    ################################            Другое            ################################
    ##############################################################################################

    # Добавление пополнения
    async def add_refill(self, amount, way, user_id, receipt, pay_url, second_amount, currency):
        async with models.async_session() as session:
            await session.execute(
                insert(models.Refill).values(
                    user_id=user_id,
                    amount=amount,
                    way=way,
                    receipt=receipt,
                    date=utils.utils.get_date(),
                    date_unix=utils.utils.get_unix(),
                    pay_url=pay_url,
                    second_amount=second_amount,
                    currency=currency,
                    under_date=utils.utils.get_unix() + 3600,
                )
            )
            await session.commit()

    # Получение пополнения
    async def get_refill(self, receipt, is_finished=False):
        async with models.async_session() as session:
            return (await session.execute(select(models.Refill).where(models.Refill.receipt == receipt).where(models.Refill.is_finish == is_finished))).scalar_one_or_none()

    # Получение всех пополнений
    async def all_refills(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.Refill))).scalars().all()

    async def update_refill(self, receipt, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Refill).where(models.Refill.receipt == receipt).values(**kwargs))
            await session.commit()

    async def delete_refill(self, receipt):
        async with models.async_session() as session:
            await session.execute(delete(models.Refill).where(models.Refill.receipt == receipt))
            await session.commit()

    async def get_unfinished_user_refill(self, user_id):
        async with models.async_session() as session:
            return (await session.execute(select(models.Refill).where(models.Refill.user_id == user_id).where(models.Refill.is_finish == False))).scalar_one_or_none()

    async def update_rates(self, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Rates).values(**kwargs))
            await session.commit()


    async def get_rates(self):
        async with models.async_session() as session:
            rates = await session.get_one(models.Rates, "rates")

        return rates.usd_rub, rates.usd_eur, rates.eur_rub, rates.eur_usd, rates.rub_usd, rates.rub_eur

    async def credit_manual_refill(self, user_id, balances):
        if 'rub' not in balances or not balances or any(
            code not in {'rub', 'usd', 'eur', 'amd'} or not math.isfinite(float(value)) or float(value) <= 0
            for code, value in balances.items()
        ):
            raise ValueError('Invalid manual refill amounts')
        values = {f'balance_{code}': func.coalesce(getattr(models.User, f'balance_{code}'), 0) + float(value)
                  for code, value in balances.items()}
        values.update(count_refills=func.coalesce(models.User.count_refills, 0) + 1,
                      total_refill=func.coalesce(models.User.total_refill, 0) + float(balances['rub']))
        async with models.async_session() as session:
            result = await session.execute(update(models.User).where(models.User.user_id == user_id).values(**values))
            if result.rowcount != 1:
                raise ValueError('Manual refill user not found')
            await session.commit()

    async def get_settings(self):
        async with models.async_session() as session:
            return await session.get_one(models.Settings, "main")
    
    # Изменение настроек
    async def update_settings(self, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Settings).values(**kwargs))
            await session.commit()

    async def get_enabled_payments(self):
        async with models.async_session() as session:
            payments = await session.get_one(models.Payment, "payments")
            settings = await session.get_one(models.Settings, "main")

        enabled = []
        for method in ("cryptoBot", "xrocket", "yoomoney", "lolz", "lava", "aaio", "cryptomus", "stars"):
            if getattr(payments, method, False):
                enabled.append(method)
        if settings.is_custom_pay_method_on:
            enabled.append("custom_pay_method")
        return enabled

    async def get_mandatory_channels(self, enabled_only=False):
        async with models.async_session() as session:
            query = select(models.MandatoryChannel).order_by(models.MandatoryChannel.title)
            if enabled_only:
                query = query.where(models.MandatoryChannel.enabled.is_(True))
            return (await session.execute(query)).scalars().all()

    async def get_mandatory_channel(self, channel_id):
        async with models.async_session() as session:
            return await session.get(models.MandatoryChannel, int(channel_id))

    async def add_mandatory_channel(self, channel_id, title, invite_link):
        async with models.async_session() as session:
            current = await session.get(models.MandatoryChannel, int(channel_id))
            if current:
                current.title, current.invite_link, current.enabled = title, invite_link, True
            else:
                session.add(models.MandatoryChannel(
                    channel_id=int(channel_id), title=title,
                    invite_link=invite_link, enabled=True,
                ))
            await session.commit()

    async def toggle_mandatory_channel(self, channel_id):
        async with models.async_session() as session:
            channel = await session.get_one(models.MandatoryChannel, int(channel_id))
            channel.enabled = not channel.enabled
            await session.commit()
            return channel.enabled

    async def delete_mandatory_channel(self, channel_id):
        async with models.async_session() as session:
            channel = await session.get(models.MandatoryChannel, int(channel_id))
            if channel:
                await session.delete(channel)
                await session.commit()

    async def get_payments(self):
        async with models.async_session() as session:
            payments = await session.get_one(models.Payment, "payments")
            settings = await session.get_one(models.Settings, "main")
        
        all_payments = {}
        for payment in payments.__dict__.items():
            if payment[0] not in ["_sa_instance_state", "settings"]:
                all_payments[payment[0]] = payment[1]
        all_payments["custom_pay_method"] = settings.is_custom_pay_method_on
        return all_payments
    
    # Вкл/Выкл платежной системы
    async def update_payment(self, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Payment).values(**kwargs))
            await session.commit()
            
    async def update_payment_config(self, field, value):
        async with models.async_session() as session:
            await session.execute(update(models.PaymentConfig).where(models.PaymentConfig.field == field).values(value=value))
            await session.commit()

    async def get_payments_config(self) -> dict:
        async with models.async_session() as session:
            config = (await session.execute(select(models.PaymentConfig))).all()
        
        paymentsConfig = {}
        for field in config:
            field = field[0]
            for configField in PAYMENTS_CONFIG_FIELDS.values():
                for fieldName in configField:
                    if field.field == fieldName:
                        paymentsConfig[fieldName] = field.value

        return paymentsConfig
    
    async def get_config_for_payment(self, payment):
        async with models.async_session() as session:
            return (await session.execute(select(models.PaymentConfig).where(models.PaymentConfig.payment_id == payment))).scalars().all()

    async def get_custom_pay_cards(self, active_only=False):
        async with models.async_session() as session:
            query = select(models.CustomPayCard).order_by(models.CustomPayCard.card_id)
            if active_only:
                query = query.where(models.CustomPayCard.is_active.is_(True))
            return (await session.execute(query)).scalars().all()

    async def get_custom_pay_card(self, card_id):
        async with models.async_session() as session:
            return await session.get(models.CustomPayCard, int(card_id))

    async def get_random_custom_pay_card(self):
        async with models.async_session() as session:
            return (await session.execute(
                select(models.CustomPayCard)
                .where(models.CustomPayCard.is_active.is_(True))
                .order_by(func.random())
                .limit(1)
            )).scalar_one_or_none()

    async def add_custom_pay_card(self, bank_name, holder_name, card_number, note=""):
        async with models.async_session() as session:
            card = models.CustomPayCard(
                bank_name=bank_name.strip(),
                holder_name=holder_name.strip(),
                card_number=card_number.strip(),
                note=(note or "").strip(),
                is_active=True,
                created_at_unix=utils.utils.get_unix(),
            )
            session.add(card)
            await session.commit()
            return card.card_id

    async def update_custom_pay_card(self, card_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.CustomPayCard).where(models.CustomPayCard.card_id == int(card_id)).values(**kwargs))
            await session.commit()

    async def toggle_custom_pay_card(self, card_id):
        async with models.async_session() as session:
            card = await session.get_one(models.CustomPayCard, int(card_id))
            card.is_active = not card.is_active
            await session.commit()
            return card.is_active

    async def delete_custom_pay_card(self, card_id):
        async with models.async_session() as session:
            await session.execute(delete(models.CustomPayCard).where(models.CustomPayCard.card_id == int(card_id)))
            await session.commit()

    # Получение промокода
    async def get_promocode(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Promocode).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()

    # Получение активироного промокода
    async def get_active_promocode(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.ActivePromocode).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()

    # Активировать промокод
    async def activate_promocode(self, user_id, promocode_name):
        async with models.async_session() as session:
            await session.execute(insert(models.ActivePromocode).values(user_id=user_id, promocode_name=promocode_name))
            await session.commit()

    # Редактирование промокода
    async def update_promocode(self, promocode, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Promocode).where(models.Promocode.name == promocode).values(**kwargs))
            await session.commit()


    # Создание промокода
    async def create_promocode(self, promocode, uses, discount_rub, discount_usd, discount_eur, discount_amd):
        async with models.async_session() as session:
            await session.execute(insert(models.Promocode).values(
                name=promocode,
                uses=uses,
                discount_rub=discount_rub,
                discount_usd=discount_usd,
                discount_eur=discount_eur,
                discount_amd=discount_amd,
            ))
            await session.commit()


    # Удаление промокода
    async def delete_promocode(self, promocode):
        async with models.async_session() as session:
            await session.execute(delete(models.Promocode).where(models.Promocode.name == promocode))
            await session.execute(delete(models.ActivePromocode).where(models.ActivePromocode.promocode_name == promocode))
            await session.commit()

    async def add_ad_button(self, name, content, photo, links):
        async with models.async_session() as session:
            await session.execute(insert(models.AdButton).values(
                name=name,
                text=content,
                photo=photo,
                links=links,
            ))
            await session.commit()

    async def delete_ad_button(self, name):
        async with models.async_session() as session:
            await session.execute(delete(models.AdButton).where(models.AdButton.name == name))
            await session.commit()

    async def get_ad_buttons(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.AdButton))).scalars().all()
        
    async def get_ad_button(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.AdButton).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()

    async def get_menu_banner(self, menu_key: str):
        async with models.async_session() as session:
            return await session.get(models.MenuBanner, menu_key)

    async def get_menu_banners(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.MenuBanner).order_by(models.MenuBanner.menu_key))).scalars().all()

    async def set_menu_banner(self, menu_key: str, photo_url: str):
        async with models.async_session() as session:
            banner = await session.get(models.MenuBanner, menu_key)
            if banner:
                banner.photo_url = photo_url
            else:
                session.add(models.MenuBanner(menu_key=menu_key, photo_url=photo_url))
            await session.commit()

    async def delete_menu_banner(self, menu_key: str):
        async with models.async_session() as session:
            await session.execute(delete(models.MenuBanner).where(models.MenuBanner.menu_key == menu_key))
            await session.commit()

    async def replace_all_menu_banners(self, menu_keys, photo_url: str):
        async with models.async_session() as session:
            await session.execute(delete(models.MenuBanner))
            session.add_all(
                models.MenuBanner(menu_key=menu_key, photo_url=photo_url)
                for menu_key in dict.fromkeys(menu_keys)
            )
            await session.commit()

    async def delete_all_menu_banners(self):
        async with models.async_session() as session:
            await session.execute(delete(models.MenuBanner))
            await session.commit()

    async def add_category(self, name, name_html=None):
        async with models.async_session() as session:
            await session.execute(insert(models.Category).values(name=name, name_html=name_html))
            await session.commit()

    async def get_all_categories(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.Category))).scalars().all()

    async def get_category(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Category).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()
        
    async def update_category(self, category_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Category).where(models.Category.cat_id == category_id).values(**kwargs))
            await session.commit()

    async def delete_category(self, category_id):
        async with models.async_session() as session:
            await session.execute(delete(models.Category).where(models.Category.cat_id == category_id))
            await session.commit()

    async def delete_all_categories(self):
        async with models.async_session() as session:
            await session.execute(delete(models.Category))
            await session.commit()

    async def add_subcategory(self, name, category_id, name_html=None):
        async with models.async_session() as session:
            await session.execute(insert(models.SubCategory).values(name=name, cat_id=category_id, name_html=name_html))
            await session.commit()

    async def get_all_subcategories(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.SubCategory))).scalars().all()

    async def get_subcategory(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.SubCategory).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()
        
    async def get_subcategories(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.SubCategory).filter_by(**kwargs).params(**kwargs))).scalars().all()
        
    async def update_subcategory(self, subcategory_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.SubCategory).where(models.SubCategory.sub_cat_id == subcategory_id).values(**kwargs))
            await session.commit()

    async def delete_subcategory(self, subcategory_id):
        async with models.async_session() as session:
            await session.execute(delete(models.SubCategory).where(models.SubCategory.sub_cat_id == subcategory_id))
            await session.commit()

    async def delete_all_subcategories(self):
        async with models.async_session() as session:
            await session.execute(delete(models.SubCategory))
            await session.commit()

    async def get_all_positions(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.Position))).scalars().all()

    async def get_positions(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Position).filter_by(**kwargs).params(**kwargs))).scalars().all()
        
    async def get_position(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Position).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()
        
    async def update_position(self, position_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.Position).where(models.Position.pos_id == position_id).values(**kwargs))
            await session.commit()

    async def delete_position(self, position_id):
        async with models.async_session() as session:
            await session.execute(delete(models.Position).where(models.Position.pos_id == position_id))
            await session.execute(delete(models.Item).where(models.Item.pos_id == position_id))
            await session.commit()

    async def delete_all_positions(self):
        async with models.async_session() as session:
            await session.execute(delete(models.Position))
            await session.execute(delete(models.Item))
            await session.commit()

    async def add_position(self, name, price_rub, price_usd, price_eur, price_amd, description, photo, cat_id, sub_cat_id, position_type, item_type, name_html=None):
        async with models.async_session() as session:
            await session.execute(insert(models.Position).values(
                name=name,
                name_html=name_html,
                price_rub=float(price_rub),
                price_usd=float(price_usd),
                price_eur=float(price_eur),
                price_amd=float(price_amd),
                description=description,
                photo=photo,
                cat_id=int(cat_id),
                sub_cat_id=int(sub_cat_id) if sub_cat_id else None,
                is_infinity=position_type,
                item_type=item_type,
            ))
            await session.commit()

    async def get_items(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Item).filter_by(**kwargs).params(**kwargs))).scalars().all()
        
    async def delete_position_items(self, position_id):
        async with models.async_session() as session:
            await session.execute(delete(models.Item).where(models.Item.pos_id == position_id))
            await session.commit()

    async def add_items(self, category_id, position_id, items, file_id, is_file=False, is_text_infinity=False):
        async with models.async_session() as session:
            if is_file:
                await session.execute(insert(models.Item).values(
                    pos_id=position_id,
                    cat_id=category_id,
                    date=utils.utils.get_date(),
                    data=items,
                    file_id=file_id
                ))
            else:
                if is_text_infinity:
                    await session.execute(insert(models.Item).values(
                        data=items,
                        pos_id=position_id,
                        cat_id=category_id,
                        date=utils.utils.get_date()
                    ))
                else:
                    for item_data in items:
                        if not item_data.isspace() and item_data != "":
                            await session.execute(insert(models.Item).values(
                                data=item_data.strip(),
                                pos_id=position_id,
                                cat_id=category_id,
                                date=utils.utils.get_date()
                            ))
            await session.commit()

    async def delete_all_items(self):
        async with models.async_session() as session:
            await session.execute(delete(models.Item))
            await session.commit()

    async def delete_item(self, item_id):
        async with models.async_session() as session:
            await session.execute(delete(models.Item).where(models.Item.item_id == item_id))
            await session.commit()

    async def add_mail_button(self, name, button_type):
        async with models.async_session() as session:
            await session.execute(insert(models.MailButton).values(name=name, button_type=button_type))
            await session.commit()

    async def get_mail_buttons(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.MailButton))).scalars().all()
        
    async def get_mail_button(self, button_id):
        async with models.async_session() as session:
            return (await session.execute(select(models.MailButton).where(models.MailButton.button_id == button_id))).scalar_one_or_none()
        
    async def delete_mail_button(self, button_id):
        async with models.async_session() as session:
            await session.execute(delete(models.MailButton).where(models.MailButton.button_id == button_id))
            await session.commit()

    async def update_mail_button(self, button_id, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.MailButton).where(models.MailButton.button_id == button_id).values(**kwargs))
            await session.commit()

    async def get_payment_method_stats(self, method):
        refills_for_day, refills_for_week, refills_for_month, refills_for_all_time = 0, 0, 0, 0
        refills_count_for_day, refills_count_for_week, refills_count_for_month, refills_count_for_all_time = 0, 0, 0, 0
        async with models.async_session() as session:
            today = datetime.datetime.today()
            month_timestamp = int(datetime.datetime(today.year, today.month, 1, 00, 00, 00).timestamp())
            settings = await self.get_settings()
            refills = (await session.execute(select(models.Refill).where(models.Refill.way == method))).scalars().all()
            
            for refill in refills:
                if refill.date_unix - settings.profit_day >= 0:
                    if settings.currency == refill.currency:
                        refills_for_day += refill.second_amount
                    else:
                        refills_for_day += await utils.utils.get_exchange(refill.second_amount , refill.currency.value.upper(), settings.currency.value.upper())
                    refills_count_for_day += 1
                
                if refill.date_unix - settings.profit_week >= 0:
                    if settings.currency == refill.currency:
                        refills_for_week += refill.second_amount
                    else:
                        refills_for_week += await utils.utils.get_exchange(refill.second_amount , refill.currency.value.upper(), settings.currency.value.upper())
                    refills_count_for_week += 1
                    
                if refill.date_unix - month_timestamp >= 0:
                    if settings.currency == refill.currency:
                        refills_for_month += refill.second_amount
                    else:
                        refills_for_month += await utils.utils.get_exchange(refill.second_amount , refill.currency.value.upper(), settings.currency.value.upper())
                    refills_count_for_month += 1
                    
                if settings.currency == refill.currency:
                    refills_for_all_time += refill.second_amount
                else:
                    refills_for_all_time += await utils.utils.get_exchange(refill.second_amount , refill.currency.value.upper(), settings.currency.value.upper())
                refills_count_for_all_time += 1
            
            
            return refills_for_day, refills_for_week, refills_for_month, refills_for_all_time, refills_count_for_day, refills_count_for_week, refills_count_for_month, refills_count_for_all_time
    
    async def get_purchases_stats_for_user(self, user_id):
        async with models.async_session() as session:
            return {
                "count_purchases": (await session.execute(select(funcfilter(func.sum(models.Purchase.count), models.Purchase.user_id == user_id)))).scalar() or 0,
                "total_purchases_rub": (await session.execute(select(funcfilter(func.sum(models.Purchase.price_rub), models.Purchase.user_id == user_id)))).scalar() or 0,
                "total_purchases_eur": (await session.execute(select(funcfilter(func.sum(models.Purchase.price_eur), models.Purchase.user_id == user_id)))).scalar() or 0,
                "total_purchases_usd": (await session.execute(select(funcfilter(func.sum(models.Purchase.price_usd), models.Purchase.user_id == user_id)))).scalar() or 0,
                "total_purchases_amd": (await session.execute(select(funcfilter(func.sum(models.Purchase.price_amd), models.Purchase.user_id == user_id)))).scalar() or 0,
            }
            
    async def buy_items(self, items: list[models.Item], count: int, is_infitity: bool, is_file_or_photo: bool):
        from tgbot.utils import item_content
        async with models.async_session() as session:
            save_items, save_len = [], 0
            for x, select_item in enumerate(items):
                if x != count:
                    if item_content.decode_item(select_item.data):
                        select_data = select_item.data
                    elif select_item.file_id:
                        kind, file_id = select_item.file_id.split(':', 1)
                        select_data = item_content.legacy_media_item('document' if kind == 'file' else kind,
                                                                     select_item.data or '', file_id)
                    elif is_file_or_photo:
                        if count > 1:
                            select_data = f"{x + 1}. {select_item.data if select_item.data else ''}:::{select_item.file_id.split(':')[1]}"
                        else:
                            select_data = f"{select_item.data if select_item.data else ''}:::{select_item.file_id.split(':')[1]}"
                    else:
                        if count > 1:
                            select_data = f"{x + 1}. {select_item.data}"
                        else:
                            select_data = select_item.data

                    save_items.append(select_data)
                    if not is_infitity:
                        await session.execute(delete(models.Item).where(models.Item.item_id == select_item.item_id))
                        
                    if len(select_data) >= save_len:
                        save_len = len(select_data)
                else:
                    break
            await session.commit()
            save_len = math.ceil(3500 / (save_len + 1))

        return save_items, save_len
    
    async def add_purchase(self, user_id, receipt, count, price_rub, price_usd, price_eur, price_amd, pos_id, item):
        async with models.async_session() as session:
            await session.execute(insert(models.Purchase).values(
                user_id=user_id,
                receipt=str(receipt),
                count=count,
                price_rub=price_rub,
                price_usd=price_usd,
                price_eur=price_eur,
                price_amd=price_amd,
                pos_id=pos_id,
                item=item,
                date=utils.utils.get_date(),
                unix=utils.utils.get_unix(),
            ))
            await session.commit()

    async def get_purchase(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Purchase).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()
        
    # Последние N покупок
    async def get_last_purchases(self, user_id, count):
        async with models.async_session() as session:
            return (await session.execute(select(models.Purchase).where(models.Purchase.user_id == user_id).order_by(desc(models.Purchase.unix)).limit(count))).scalars().all()

    async def get_data_for_stats(self):
        async with models.async_session() as session:
            return ((await session.execute(select(models.Purchase))).scalars().all(),
                    (await session.execute(select(models.Refill))).scalars().all(),
                    (await session.execute(select(models.User))).scalars().all(),
                    await session.get_one(models.Settings, "main"))
    
    async def get_sum_balances(self):
        async with models.async_session() as session:
            return {
                "rub": (await session.execute(select(func.sum(models.User.balance_rub)))).scalar() or 0, 
                "usd": (await session.execute(select(func.sum(models.User.balance_usd)))).scalar() or 0, 
                "eur": (await session.execute(select(func.sum(models.User.balance_eur)))).scalar() or 0,
                "amd": (await session.execute(select(func.sum(models.User.balance_amd)))).scalar() or 0,
            }
            
    async def create_contest(self, prize, currency, members_num, end_time, winners_num, channels_ids, refills_num, purchases_num):
        async with models.async_session() as session:
            await session.execute(insert(models.Contest).values(
                prize=prize,
                currency=currency,
                members_num=members_num,
                end_time=end_time,
                winners_num=winners_num,
                channels_ids=channels_ids,
                refills_num=refills_num,
                purchases_num=purchases_num
            ))
            await session.commit()

    async def get_all_contests(self):
        async with models.async_session() as session:
            return (await session.execute(select(models.Contest))).scalars().all()

    async def get_contest(self, **kwargs):
        async with models.async_session() as session:
            return (await session.execute(select(models.Contest).filter_by(**kwargs).params(**kwargs))).scalar_one_or_none()

    async def get_contests_settings(self):
        async with models.async_session() as session:
            return await session.get_one(models.ContestsSettings, "main")
    
    # Изменение настроек
    async def update_contests_settings(self, **kwargs):
        async with models.async_session() as session:
            await session.execute(update(models.ContestsSettings).values(**kwargs))
            await session.commit()

    async def get_contest_members(self, contest_id: int):
        async with models.async_session() as session:
            return (await session.execute(select(models.ContestMember).where(models.ContestMember.contest_id == contest_id))).scalars().all()

    async def add_contest_member(self, user_id: int, contest_id: int):
        async with models.async_session() as session:
            await session.execute(insert(models.ContestMember).values(
                user_id=user_id,
                contest_id=contest_id
            ))
            await session.commit()
        
    async def get_contest_members_id(self, contest_id: int):
        members = await self.get_contest_members(contest_id)
        users_ids = []
        for user in members:
            users_ids.append(user.user_id)
        return users_ids

    async def delete_contest(self, contest_id):
        async with models.async_session() as session:
            await session.execute(delete(models.Contest).where(models.Contest.contest_id == contest_id))
            await session.execute(delete(models.ContestMember).where(models.ContestMember.contest_id == contest_id))
            await session.commit()
