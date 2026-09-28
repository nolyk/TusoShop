from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from string import Formatter
import pytest
from tgbot.data.config import BotTexts,DB
from tgbot.handlers.users import digital_shop as d,refill as r

def test_receipt_and_active_refill_fields():
    assert '<tg-emoji emoji-id="6181523988481581415">📋</tg-emoji>' in BotTexts.Hy.TEXTS.send_receipt_photo
    template=BotTexts.Hy.TEXTS.cancel_create_refill_text_custom_pay_method
    assert {n for _,n,_,_ in Formatter().parse(template) if n}=={'paymentMethod','pay_amount','curr','pay_id','under_date','custom_pay_method_text'}
    details=BotTexts.Hy.TEXTS.custom_pay_transfer_details.format(bank='BANK',holder='HOLDER',number='0000',note='NOTE')
    result=template.format(paymentMethod='Bank',pay_amount='1000.00',curr='֏',pay_id='fixture-42',under_date='30.09.2026',custom_pay_method_text=details)
    for id in ['6181207762924478466','6181551167034631404','6183559145849890138','6181548602939155001','6181377573046461008','6181248419084903585']:assert id in result
    for field in ['BANK','HOLDER','0000','NOTE','1000.00֏','fixture-42','30.09.2026']:assert field in result

@pytest.mark.asyncio
async def test_receipt_yes_no_keep_callbacks(monkeypatch):
    monkeypatch.setattr(DB,'get_refill',AsyncMock(return_value=Obj(receipt='42')))
    state=Obj(get_data=AsyncMock(return_value={'pay_id':'42'}),update_data=AsyncMock())
    msg=Obj(photo=[Obj(file_id='PHOTO')],reply=AsyncMock())
    await r.enter_receipt_for_custom_pay_method(msg,state,BotTexts.Hy)
    buttons=msg.reply.call_args.kwargs['reply_markup'].inline_keyboard[0]
    assert [(b.text,b.callback_data) for b in buttons]==[('Այո','send_receipt_to_check:yes'),('Ոչ','send_receipt_to_check:no')]
    state.update_data.assert_awaited_once_with(photo='PHOTO')

@pytest.mark.asyncio
@pytest.mark.parametrize('product',['stars','premium'])
async def test_wizard_icons_and_actions(monkeypatch,product):
    monkeypatch.setattr(d.digital_shop_repository,'product_enabled',AsyncMock(return_value=True))
    render=AsyncMock();monkeypatch.setattr(d,'edit_menu',render)
    state=Obj(clear=AsyncMock(),update_data=AsyncMock())
    await getattr(d,'digital_'+product)(Obj(answer=AsyncMock()),state)
    text=render.call_args.args[1];keyboard=render.call_args.args[2]
    buttons={b.callback_data:b for row in keyboard.inline_keyboard for b in row}
    state.update_data.assert_awaited_once_with(digital_product=product)
    if product=='stars':
        assert text.count('6181597355112932310')==3
        assert '50' in text and '4,999' in text
        for amount in (50,100,500):assert buttons[f'digital:stars_amount:{amount}'].icon_custom_emoji_id=='6181597355112932310'
        assert buttons['digital:stars_custom'].icon_custom_emoji_id=='6183790833565705068'
    else:
        assert '6181700898184503901' in text
        for month,id in [(3,'6181389547415282170'),(6,'6181713619877634683'),(12,'6181253951002780793')]:
            assert buttons[f'digital:premium_period:{month}'].icon_custom_emoji_id==id
            assert buttons[f'digital:premium_period:{month}'].text==f'{month} ամիս'
    assert buttons['digital:home'].text=='Հետ'

def test_recipient_buttons_keep_armenian_and_route():
    buttons={b.callback_data:b for row in d.recipient_keyboard('digital:home').inline_keyboard for b in row}
    assert buttons['digital:recipient:self'].icon_custom_emoji_id=='6181512409249750964'
    assert buttons['digital:recipient:self'].text=='Գնել ինձ համար'
    assert buttons['digital:recipient:input'].icon_custom_emoji_id=='6181440610281464581'
    assert buttons['digital:recipient:input'].text=='Մուտքագրել username'
