from datetime import datetime,timezone
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from aiogram.types import Message,Chat,User,MessageEntity
from aiogram.methods import SendMessage
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from tgbot.data.config import DB,BotTexts
from tgbot.data.loader import bot
from tgbot.utils import models
from tgbot.utils.catalog_emoji import name_fields,catalog_name,catalog_button_name
from tgbot.handlers.admins import products
from tgbot.keyboards.users import InlineButtons

ID='6181440610281464581'
def incoming(text='🛍 ✅ Խաղեր & More'):
    msg=Message(message_id=1,date=datetime.now(timezone.utc),chat=Chat(id=1,type='private'),from_user=User(id=1,is_bot=False,first_name='Fixture'),text=text,entities=[MessageEntity(type='custom_emoji',offset=3,length=1,custom_emoji_id=ID)])
    return Obj(text=msg.text,html_text=msg.html_text,from_user=msg.from_user,answer=AsyncMock(),reply=AsyncMock())

@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['category','subcategory','position'])
async def test_name_capture_create_and_rename(monkeypatch,kind):
    msg=incoming(); obj=Obj(cat_id=1,sub_cat_id=2,pos_id=3,name='old')
    state=Obj(clear=AsyncMock(),set_state=AsyncMock(),update_data=AsyncMock(),get_data=AsyncMock(return_value={'category':obj,'category_id':1,'subcategory_id':2,'old_name':'old','position':obj}))
    monkeypatch.setattr(products.utils,'send_admins',AsyncMock())
    monkeypatch.setattr(products,'get_position_info',AsyncMock())
    monkeypatch.setattr(DB,'get_position',AsyncMock(return_value=obj))
    add_name={'category':'add_category','subcategory':'add_subcategory','position':'add_position'}[kind]
    update_name={'category':'update_category','subcategory':'update_subcategory','position':'update_position'}[kind]
    add=AsyncMock();update=AsyncMock();monkeypatch.setattr(DB,add_name,add);monkeypatch.setattr(DB,update_name,update)
    await getattr(products,'enter_'+kind+'_name')(msg,state,BotTexts.Hy)
    kwargs=state.update_data.call_args.kwargs if kind=='position' else add.call_args.kwargs
    assert kwargs['name']==msg.text and ID in kwargs['name_html']
    rename={'category':'enter_new_name_for_category','subcategory':'enter_new_name_for_sub','position':'enter_new_position_name'}[kind]
    await getattr(products,rename)(msg,state,BotTexts.Hy)
    assert update.call_args.kwargs['name_html']==msg.html_text
    plain=Obj(**vars(msg));plain.text='Plain';plain.html_text='Plain'
    await getattr(products,rename)(plain,state,BotTexts.Hy)
    assert update.call_args.kwargs['name_html']=='Plain'

@pytest.mark.asyncio
async def test_database_roundtrip(monkeypatch):
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        for cls in (models.Category,models.SubCategory,models.Position):
            await conn.run_sync(cls.__table__.create)
    sessions=async_sessionmaker(engine,expire_on_commit=False); monkeypatch.setattr(models,'async_session',sessions)
    fields=name_fields(incoming())
    async with sessions() as session:
        session.add_all([models.Category(cat_id=1,**fields),models.SubCategory(sub_cat_id=2,cat_id=1,**fields),models.Position(pos_id=3,cat_id=1,**fields)])
        await session.commit()
    for obj in (await DB.get_category(cat_id=1),await DB.get_subcategory(sub_cat_id=2),await DB.get_position(pos_id=3)):
        assert obj.name==fields['name'] and obj.name_html==fields['name_html']
    await engine.dispose()

@pytest.mark.asyncio
async def test_outgoing_text_and_button_keep_exact_id():
    fields=name_fields(incoming());obj=Obj(cat_id=1,**fields)
    kb=InlineButtons().select_category(BotTexts.Hy,[obj]).as_markup()
    method=SendMessage(chat_id=1,text='<code>'+catalog_name(obj)+'</code>',reply_markup=kb)
    await bot.session.middleware.wrap_middlewares(AsyncMock())(bot,method)
    button=method.reply_markup.inline_keyboard[0][0]
    assert button.icon_custom_emoji_id==ID and button.callback_data=='open_category:1'
    assert button.text=='🛍  Խաղեր & More'
    assert '<tg-emoji' not in button.text
    assert ID in method.text and '<code>' not in method.text

def test_legacy_and_multiple():
    assert catalog_button_name(Obj(name='A & B',name_html='A &amp; B'))=='A & B'
    assert catalog_name(Obj(name='Old'))=='Old'

@pytest.mark.asyncio
async def test_description_entities_preserved(monkeypatch):
    msg=incoming(); state=Obj(set_state=AsyncMock(),update_data=AsyncMock())
    await products.enter_position_description(msg,state,BotTexts.Hy)
    assert state.update_data.call_args.kwargs['description']==msg.html_text
