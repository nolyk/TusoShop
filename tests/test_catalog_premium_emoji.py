from unittest.mock import AsyncMock
from aiogram.methods import SendMessage,SendPhoto,EditMessageText,EditMessageCaption,EditMessageReplyMarkup,EditMessageMedia,GetMe
from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardMarkup,KeyboardButton,InputMediaPhoto
import pytest
from tgbot.data.config import BotTexts
from tgbot.data.loader import bot
from tgbot.utils.back_button_emoji import BackButtonEmojiMiddleware

@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['message','photo','text_edit','caption_edit','markup_edit','media_edit','reply'])
async def test_back_every_delivery_path(kind):
    back=InlineKeyboardButton(text='Հետ',callback_data='open_category:7',icon_custom_emoji_id='1')
    keep=InlineKeyboardButton(text='Գնել',callback_data='buy',icon_custom_emoji_id='6181477413856224769')
    markup=InlineKeyboardMarkup(inline_keyboard=[[back,keep]])
    methods={
        'message':lambda:SendMessage(chat_id=1,text='test',reply_markup=markup),
        'photo':lambda:SendPhoto(chat_id=1,photo='fixture',reply_markup=markup),
        'text_edit':lambda:EditMessageText(chat_id=1,message_id=1,text='test',reply_markup=markup),
        'caption_edit':lambda:EditMessageCaption(chat_id=1,message_id=1,caption='test',reply_markup=markup),
        'markup_edit':lambda:EditMessageReplyMarkup(chat_id=1,message_id=1,reply_markup=markup),
        'media_edit':lambda:EditMessageMedia(chat_id=1,message_id=1,media=InputMediaPhoto(media='fixture'),reply_markup=markup),
        'reply':lambda:SendMessage(chat_id=1,text='test',reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Հետ')]])),
    }
    method=methods[kind](); terminal=AsyncMock(return_value=True)
    assert await bot.session.middleware.wrap_middlewares(terminal)(bot,method) is True
    rows=method.reply_markup.keyboard if kind=='reply' else method.reply_markup.inline_keyboard
    assert rows[0][0].icon_custom_emoji_id=='6181715848965661096'
    if kind!='reply':
        assert rows[0][0].callback_data=='open_category:7'
        assert rows[0][1].icon_custom_emoji_id=='6181477413856224769'
    terminal.assert_awaited_once_with(bot,method)

@pytest.mark.asyncio
@pytest.mark.parametrize('label',['Назад','◀ Back','Հետ','⬅ Назад'])
async def test_back_translations(label):
    button=InlineKeyboardButton(text=label,callback_data='admin_panel')
    method=SendMessage(chat_id=1,text='test',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]]))
    await BackButtonEmojiMiddleware()(AsyncMock(),bot,method)
    assert button.icon_custom_emoji_id=='6181715848965661096'

@pytest.mark.asyncio
async def test_no_keyboard_passthrough():
    request=GetMe();next_request=AsyncMock(return_value=True)
    assert await BackButtonEmojiMiddleware()(next_request,bot,request) is True

def test_exact_catalog_heading_and_product():
    assert BotTexts.Hy.TEXTS.available_cats == '<b><tg-emoji emoji-id="5472189467869619770">🛒</tg-emoji> Հասանելի կատեգորիաները</b>'
    assert '6181208703522317605' in BotTexts.Hy.TEXTS.current_cat
    rendered=BotTexts.Hy.TEXTS.open_position_text.format(cat_name='Համարներ',pos_name='Armenia',price='21400.0',cur='֏',items='Անսահմանափակ',desc='fixture')
    for id in ('5472189467869619770','5472382354850881695','5474129800949964546','5471946243871645459'):
        assert rendered.count(id)==1
    assert '21400.0֏' in rendered and 'Armenia' in rendered and rendered.endswith('fixture')
