from unittest.mock import AsyncMock
import pytest
from aiogram.methods import SendMessage, SendPhoto, EditMessageText, EditMessageMedia, SendMediaGroup, AnswerCallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto, MessageEntity
from tgbot.data.loader import bot
from tgbot.data.config import BotTexts
from tgbot.utils.status_emoji import html_status, StatusEmojiMiddleware
from tgbot.utils.premium_emoji import STATUS_IDS, normalize_button_text

@pytest.mark.parametrize('symbol', list(STATUS_IDS))
def test_html_each_status_idempotent(symbol):
    text=f'<b>{symbol} test</b><code>{symbol}</code><a href="https://example.org/{symbol}">link</a>'
    result=html_status(text)
    assert f'emoji-id="{STATUS_IDS[symbol]}"' in result
    assert f'<code>{symbol}</code>' in result
    assert f'https://example.org/{symbol}' in result
    assert html_status(result)==result

@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['message','photo','edit','media','album','entities','plain'])
async def test_delivery_paths(kind):
    text='🛍 ✅️ done ❌'
    methods={
      'message':SendMessage(chat_id=1,text=text),
      'photo':SendPhoto(chat_id=1,photo='fixture',caption=text),
      'edit':EditMessageText(chat_id=1,message_id=1,text=text),
      'media':EditMessageMedia(chat_id=1,message_id=1,media=InputMediaPhoto(media='fixture',caption=text)),
      'album':SendMediaGroup(chat_id=1,media=[InputMediaPhoto(media='one',caption=text),InputMediaPhoto(media='two',caption=text)]),
      'entities':SendMessage(chat_id=1,text=text,entities=[MessageEntity(type='bold',offset=0,length=13)]),
      'plain':SendMessage(chat_id=1,text=text,parse_mode=None),
    }
    method=methods[kind]; endpoint=AsyncMock(return_value=True)
    await bot.session.middleware.wrap_middlewares(endpoint)(bot,method)
    if kind in {'entities','plain'}:
        assert method.text==text and method.parse_mode is None
        emoji=[e for e in method.entities if e.type=='custom_emoji']
        assert [(e.offset,e.length,e.custom_emoji_id) for e in emoji]==[(3,2,STATUS_IDS['✅']),(11,1,STATUS_IDS['❌'])]
    else:
        content=method.text if kind in {'message','edit'} else method.caption if kind=='photo' else method.media.caption if kind=='media' else method.media[0].caption
        assert STATUS_IDS['✅'] in content and STATUS_IDS['❌'] in content
    endpoint.assert_awaited_once()

@pytest.mark.asyncio
async def test_buttons_and_ad_prompt():
    buttons=[InlineKeyboardButton(text='✅ Այո',callback_data='yes'),InlineKeyboardButton(text='❌ Ոչ',callback_data='no'),InlineKeyboardButton(text='Создать',callback_data='ad_buttons:create'),InlineKeyboardButton(text=normalize_button_text('✅ Проверить'),callback_data='check')]
    method=SendMessage(chat_id=1,text=BotTexts.Hy.ADMIN_TEXTS.enter_name_for_create_ad_button,reply_markup=InlineKeyboardMarkup(inline_keyboard=[buttons]))
    await bot.session.middleware.wrap_middlewares(AsyncMock())(bot,method)
    assert [b.icon_custom_emoji_id for b in buttons]==[STATUS_IDS['✅'],STATUS_IDS['❌'],STATUS_IDS['📢'],STATUS_IDS['✅']]
    assert [b.callback_data for b in buttons]==['yes','no','ad_buttons:create','check']
    assert [b.text for b in buttons[:2]]==['Այո','Ոչ']
    assert STATUS_IDS['📢'] in method.text

@pytest.mark.asyncio
async def test_reply_label_and_alert_unchanged():
    button=KeyboardButton(text=normalize_button_text('❌ Cancel fixture'))
    method=SendMessage(chat_id=1,text='test',reply_markup=ReplyKeyboardMarkup(keyboard=[[button]]))
    before=button.text
    await StatusEmojiMiddleware()(AsyncMock(),bot,method)
    assert button.text==before and button.icon_custom_emoji_id==STATUS_IDS['❌']
    alert=AnswerCallbackQuery(callback_query_id='fixture',text='✅ OK')
    await StatusEmojiMiddleware()(AsyncMock(),bot,alert)
    assert alert.text=='✅ OK'

def test_existing_custom_id_replaced():
    assert html_status('<tg-emoji emoji-id="123">❌</tg-emoji>')=='<tg-emoji emoji-id="6181355634353513160">❌</tg-emoji>'
    assert '✅' in BotTexts.Hy.ADMIN_TEXTS.success

@pytest.mark.asyncio
async def test_existing_entity_and_icon():
    method=SendMessage(chat_id=1,text='❌',parse_mode=None,entities=[MessageEntity(type='custom_emoji',offset=0,length=1,custom_emoji_id='123')],reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Confirm',callback_data='confirm',icon_custom_emoji_id='5211226456100738227')]]))
    await StatusEmojiMiddleware()(AsyncMock(),bot,method)
    assert method.entities[0].custom_emoji_id==STATUS_IDS['❌']
    assert method.reply_markup.inline_keyboard[0][0].icon_custom_emoji_id==STATUS_IDS['✅']
