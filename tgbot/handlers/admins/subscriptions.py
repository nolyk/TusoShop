from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from tgbot.data.config import BotButtons, BotTexts as BTs, DB
from tgbot.data.loader import adminRouter, bot
from tgbot.states.adminStates import AdminMainSettings
from tgbot.utils import utils
from tgbot.utils.menu import safe_edit_text


async def render_channels(target, texts, edit=False):
    channels = await DB.get_mandatory_channels()
    bot_username = (await bot.get_me()).username
    message = (texts.ADMIN_TEXTS.mandatory_channels_text if channels
               else texts.ADMIN_TEXTS.mandatory_channels_empty)
    markup = (await BotButtons.ADMIN_INLINE.mandatory_channels(
        texts, channels, bot_username
    )).as_markup()
    if edit:
        return await safe_edit_text(target.message, message, reply_markup=markup)
    return await target.answer(message, reply_markup=markup)


@adminRouter.callback_query(F.data == "mandatory_channels")
async def mandatory_channels(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru):
    await state.clear()
    await render_channels(call, BotTexts, edit=True)


@adminRouter.callback_query(F.data == "mandatory_channel:add")
async def mandatory_channel_add(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru):
    await state.set_state(AdminMainSettings.enter_mandatory_channel)
    await safe_edit_text(
        call.message,
        BotTexts.ADMIN_TEXTS.enter_mandatory_channel,
        reply_markup=BotButtons.ADMIN_INLINE.custom_button(
            BotTexts, "mandatory_channels"
        ).as_markup(),
    )


@adminRouter.message(StateFilter(AdminMainSettings.enter_mandatory_channel))
async def mandatory_channel_receive(msg: Message, state: FSMContext, BotTexts: BTs.Ru):
    origin = getattr(msg, "forward_origin", None)
    chat = getattr(origin, "chat", None) or getattr(msg, "forward_from_chat", None)
    reference = chat.id if chat else (msg.text or "").strip()
    if isinstance(reference, str) and reference.lstrip("-").isdigit():
        reference = int(reference)
    try:
        channel = await bot.get_chat(reference)
        me = await bot.get_me()
        membership = await bot.get_chat_member(channel.id, me.id)
        status = getattr(membership.status, "value", membership.status)
        if status not in {"administrator", "creator"}:
            raise ValueError("bot is not an administrator")
        if channel.username:
            invite_link = f"https://t.me/{channel.username}"
        else:
            invite_link = channel.invite_link
            if not invite_link:
                invite_link = (await bot.create_chat_invite_link(channel.id)).invite_link
    except Exception:
        return await msg.answer(BotTexts.ADMIN_TEXTS.channel_not_accessible)

    await DB.add_mandatory_channel(channel.id, channel.title, invite_link)
    await DB.update_settings(is_sub=True)
    await state.clear()
    await utils.send_admins(
        "channel_added_alert", admin=msg.from_user.mention_html(),
        title=channel.title, channel_id=channel.id,
    )
    await msg.answer(BotTexts.ADMIN_TEXTS.channel_added.format(title=channel.title))
    await render_channels(msg, BotTexts)


@adminRouter.callback_query(F.data.startswith("mandatory_channel:view:"))
async def mandatory_channel_view(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru):
    await state.clear()
    channel = await DB.get_mandatory_channel(call.data.rsplit(":", 1)[1])
    if not channel:
        return await render_channels(call, BotTexts, edit=True)
    status = (BotTexts.ADMIN_TEXTS.channel_enabled if channel.enabled
              else BotTexts.ADMIN_TEXTS.channel_disabled)
    await safe_edit_text(
        call.message,
        BotTexts.ADMIN_TEXTS.channel_manage.format(
            title=channel.title, channel_id=channel.channel_id, status=status
        ),
        reply_markup=BotButtons.ADMIN_INLINE.mandatory_channel_manage(
            BotTexts, channel
        ).as_markup(),
    )


@adminRouter.callback_query(F.data.startswith("mandatory_channel:toggle:"))
async def mandatory_channel_toggle(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru):
    channel_id = int(call.data.rsplit(":", 1)[1])
    await DB.toggle_mandatory_channel(channel_id)
    channel = await DB.get_mandatory_channel(channel_id)
    status = (BotTexts.ADMIN_TEXTS.channel_enabled if channel.enabled
              else BotTexts.ADMIN_TEXTS.channel_disabled)
    await safe_edit_text(
        call.message,
        BotTexts.ADMIN_TEXTS.channel_manage.format(
            title=channel.title, channel_id=channel.channel_id, status=status
        ),
        reply_markup=BotButtons.ADMIN_INLINE.mandatory_channel_manage(
            BotTexts, channel
        ).as_markup(),
    )


@adminRouter.callback_query(F.data.startswith("mandatory_channel:delete:"))
async def mandatory_channel_delete(call: CallbackQuery, state: FSMContext, BotTexts: BTs.Ru):
    await DB.delete_mandatory_channel(int(call.data.rsplit(":", 1)[1]))
    await call.answer(BotTexts.ADMIN_TEXTS.channel_deleted)
    await render_channels(call, BotTexts, edit=True)
