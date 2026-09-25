import os
import time
from html import escape

from tgbot.states.digital_shop import DigitalAdmin

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.data.config import BotConfig, BotButtons
from tgbot.data.config import BotTexts as BTs
from tgbot.data.loader import adminRouter
from tgbot.repositories.digital_shop import digital_shop_repository
from tgbot.utils.digital_emoji import STARS_EMOJI
from tgbot.utils.menu import edit_menu


def admin_digital_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Продажа Stars: вкл / выкл", callback_data="digital_admin:stars")],
        [InlineKeyboardButton(text="📦 Заказы", callback_data="digital_admin:orders"),
         InlineKeyboardButton(text="⚠️ Ошибки", callback_data="digital_admin:errors")],
        [InlineKeyboardButton(text="💰 Цены и наценки", callback_data="digital_admin:pricing"),
         InlineKeyboardButton(text="💳 Оплата", callback_data="digital_admin:payments")],
        [InlineKeyboardButton(text="🌐 Mini App", callback_data="digital_admin:miniapp"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="digital_admin:stats")],
        [InlineKeyboardButton(text="⚙️ Выдача Stars / Premium", callback_data="digital_admin:fulfillment")],
        [InlineKeyboardButton(text="🔐 Кошелёк: ввод / замена", callback_data="digital_admin:wallet")],
        [InlineKeyboardButton(text="🔧 Диагностика", callback_data="digital_admin:diagnostics")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")],
    ])


@adminRouter.callback_query(F.data == "digital_admin:home")
async def digital_admin_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_menu(
        call,
        f"<b>{STARS_EMOJI} Управление цифровым магазином</b>\n\n"
        "Stars, Premium, цифровые заказы, платёжные провайдеры и Mini App.",
        admin_digital_keyboard(), "admin",
    )


@adminRouter.callback_query(F.data == "digital_admin:stars")
async def stars_availability(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    enabled = await digital_shop_repository.product_enabled("stars")
    text = ("<b>⭐ Продажа Stars</b>\n\nСтатус: " + ("включена ✅" if enabled else "выключена ⛔")
            + "\nНастройка действует в боте и Mini App и сохраняется после перезапуска."
            + "\nУже оплаченные заказы остаются доступны для выдачи."
            + "\nПополнение баланса звёздами настраивается отдельно в разделе оплаты.")
    if not BotConfig.DIGITAL_SHOP_ENABLED:
        text += "\n⚠️ Весь цифровой магазин отключён переменной DIGITAL_SHOP_ENABLED."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Выключить" if enabled else "✅ Включить",
                              callback_data=f"digital_stars_enabled:{0 if enabled else 1}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="digital_admin:home")],
    ])
    await edit_menu(call, text, keyboard, "admin")


@adminRouter.callback_query(F.data.startswith("digital_stars_enabled:"))
async def set_stars_availability(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    action = (call.data or "").split(":")
    if len(action) != 2 or action[1] not in {"0", "1"}:
        return await call.answer("Некорректная команда", show_alert=True)
    await digital_shop_repository.set_stars_enabled(action[1] == "1", call.from_user.id)
    await call.answer("Сохранено")
    await stars_availability(call)


@adminRouter.callback_query(F.data == "digital_admin:stats")
async def digital_admin_stats(call: CallbackQuery):
    stats = await digital_shop_repository.stats()
    text = (
        "<b>📊 Цифровая статистика</b>\n\n"
        f"Всего заказов: <b>{stats['total']}</b>\n"
        f"Выполнено: <b>{stats['completed']}</b>\n"
        f"Ошибок выдачи: <b>{stats['failed']}</b>"
    )
    await edit_menu(call, text, admin_digital_keyboard(), "admin")


@adminRouter.callback_query(F.data == "digital_admin:diagnostics")
async def digital_admin_diagnostics(call: CallbackQuery):
    checks = {
        "Цифровой магазин": BotConfig.DIGITAL_SHOP_ENABLED,
        "Mini App URL": BotConfig.WEBAPP_URL.startswith("https://"),
        "JWT secret": bool(BotConfig.JWT_SECRET),
        "MarketApp token": bool(BotConfig.MARKETAPP_API_TOKEN),
        "TonAPI key": bool(BotConfig.TONAPI_KEY),
    }
    lines = ["<b>🔧 Безопасная диагностика</b>", ""]
    lines.extend(f"{'✅' if ok else '⚠️'} {name}" for name, ok in checks.items())
    lines.append("\n<i>Секретные значения не отображаются.</i>")
    await edit_menu(call, "\n".join(lines), admin_digital_keyboard(), "admin")




def private_admin(event) -> bool:
    message = event.message if isinstance(event, CallbackQuery) else event
    return bool(event.from_user and event.from_user.id in BotConfig.ADMINS
                and message and message.chat.type == "private")


@adminRouter.callback_query(F.data == "digital_admin:fulfillment")
async def fulfillment_settings(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    rows = []
    for product, label in (("stars", "Stars"), ("premium", "Premium")):
        mode = await digital_shop_repository.fulfillment_mode(product)
        rows.append([InlineKeyboardButton(
            text=f"{'✓ ' if mode == value else ''}{label}: {title}",
            callback_data=f"digital_mode:{product}:{value}",
        ) for value, title in (("manual", "Вручную"), ("auto", "Авто"))])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="digital_admin:home")])
    await edit_menu(call, "<b>Режим выдачи</b>\n\nStars и Premium настраиваются независимо. "
                    "Настройки сохраняются, но приём цифровых платежей и выполнение заказов "
                    "ещё отключены до подключения и проверки провайдера.",
                    InlineKeyboardMarkup(inline_keyboard=rows), "admin")


@adminRouter.callback_query(F.data.startswith("digital_mode:"))
async def change_fulfillment(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    parts = (call.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"stars", "premium"} or parts[2] not in {"manual", "auto"}:
        return await call.answer("Некорректный режим", show_alert=True)
    await digital_shop_repository.set_setting(f"{parts[1]}_fulfillment_mode", parts[2], call.from_user.id)
    await call.answer("Сохранено")
    await fulfillment_settings(call)


@adminRouter.callback_query(F.data == "digital_admin:wallet")
async def wallet_setup(call: CallbackQuery, state: FSMContext):
    from tgbot.services.digital_shop.wallet_secret import wallet_cipher
    if not private_admin(call):
        return await call.answer("Только администратору в личном чате", show_alert=True)
    try:
        wallet_cipher()
    except (ValueError, TypeError, UnicodeError):
        return await call.answer("Сначала настройте WALLET_ENCRYPTION_KEY на сервере. Ввод отключён.", show_alert=True)
    await state.clear()
    await state.set_state(DigitalAdmin.mnemonic)
    await state.update_data(wallet_deadline=time.time() + 180)
    await call.message.answer(
        "Отправьте 24 слова TON-мнемоники одним сообщением через пробел в течение 3 минут. "
        "Новый ввод заменит прежний кошелёк. /cancel — отмена.\n\n"
        "⚠️ Чат с ботом не имеет сквозного шифрования. Безопаснее использовать отдельный "
        "рабочий кошелёк с небольшим балансом или настраивать секрет на сервере. "
        "Сообщение удаляется перед сохранением, слова не отображаются в ответах. "
        "Сохранение не запускает автоматическую выдачу.")
    await call.answer()


@adminRouter.message(DigitalAdmin.mnemonic)
async def wallet_mnemonic(message: Message, state: FSMContext):
    from tgbot.services.digital_shop.wallet_secret import encrypt_mnemonic
    if not private_admin(message):
        return
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Ввод отменён.")
    deadline = (await state.get_data()).get("wallet_deadline", 0)
    try:
        await message.delete()
    except Exception:
        await state.clear()
        return await message.answer("Не удалось удалить сообщение. Секрет не сохранён. Удалите сообщение вручную.")
    if time.time() > deadline:
        await state.clear()
        return await message.answer("Время ввода истекло. Откройте настройку кошелька заново.")
    try:
        encrypted = encrypt_mnemonic(message.text or "")
    except (ValueError, TypeError, UnicodeError):
        return await message.answer("Некорректная TON-мнемоника: нужны 24 действительных слова. /cancel — отмена.")
    try:
        await digital_shop_repository.set_setting("ton_wallet_mnemonic", encrypted, message.from_user.id, secret=True)
    except Exception:
        await state.clear()
        return await message.answer("Не удалось сохранить кошелёк. Прежняя настройка не заменена.")
    await state.clear()
    await message.answer("Кошелёк сохранён в зашифрованном виде. Повторный ввод в этом разделе заменит его.")


@adminRouter.callback_query(F.data.in_({"digital_admin:orders", "digital_admin:errors"}))
async def digital_admin_orders(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    errors = call.data == "digital_admin:errors"
    orders = await digital_shop_repository.list_admin_orders(errors_only=errors)
    lines = ["<b>Ошибки выдачи</b>" if errors else "<b>Последние 20 заказов</b>"]
    for order in orders:
        lines.append(f"<code>{escape(str(order.public_id))}</code> · {escape(order.product_type)} · {order.quantity:g} · {escape(order.status)}")
    if not orders:
        lines.append("Записей пока нет.")
    await edit_menu(call, "\n\n".join(lines), admin_digital_keyboard(), "admin")


@adminRouter.callback_query(F.data.in_({"digital_admin:pricing", "digital_admin:payments", "digital_admin:miniapp"}))
async def digital_admin_info(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    if call.data == "digital_admin:pricing":
        stars = await digital_shop_repository.get_setting("stars_markup_percent", "0")
        premium = await digital_shop_repository.get_setting("premium_markup_percent", "7")
        text = f"<b>Текущие наценки</b>\n\nStars: {escape(stars)}%\nPremium: {escape(premium)}%\n\nЦена сейчас запрашивается через MarketApp. Редактор наценок пока не подключён."
    elif call.data == "digital_admin:payments":
        text = "<b>Оплата Stars/Premium</b>\n\nПриём платежей и исполнение заказов ещё не подключены. Настройки выдачи сохраняются, но переводы не запускаются.\n\nДля Fragment нужен перенос исполнителя из старого проекта: создание заявки, подпись TON-перевода, подтверждение и защита от повторной выдачи. Наличие мнемоники не заменяет этот код."
    else:
        text = "<b>Mini App</b>\n\nHTTPS-адрес " + ("настроен." if BotConfig.WEBAPP_URL.startswith("https://") else "не настроен.") + "\nКаталог и покупка обычных товаров подключены. Stars/Premium: выбор получателя и расчёт цены; оплата отключена."
    await edit_menu(call, text, admin_digital_keyboard(), "admin")


@adminRouter.callback_query(F.data.startswith("digital_admin:"))
async def digital_admin_pending(call: CallbackQuery):
    await call.answer("Кнопка устарела. Откройте меню Stars/Premium заново.", show_alert=True)

@adminRouter.callback_query(F.data.startswith("digital_manual:"))
async def digital_manual_action(call: CallbackQuery):
    if not private_admin(call):
        return await call.answer("Нет доступа", show_alert=True)
    parts = (call.data or "").split(":", 2)
    if len(parts) != 3 or parts[1] not in {"complete", "fail"}:
        return await call.answer("Некорректная команда", show_alert=True)
    public_id = parts[2]
    if parts[1] == "complete":
        order = await digital_shop_repository.complete_manual_order(public_id, call.from_user.id)
        if order is None:
            return await call.answer("Заказ уже закрыт или не найден", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Закрыто", callback_data="NONE")
        ]]))
        await call.answer("Выдача отмечена")
        return
    order = await digital_shop_repository.fail_manual_order(public_id, call.from_user.id)
    if order is None:
        return await call.answer("Заказ уже закрыт или не найден", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Ошибка выдачи", callback_data="NONE")
    ]]))
    await call.answer("Отмечено как ошибка")
