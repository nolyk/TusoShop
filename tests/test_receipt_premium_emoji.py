from string import Formatter
import re
from tgbot.data.config import BotTexts

def test_promocode_icon_preserves_amount():
    text=BotTexts.Hy.TEXTS.yes_promocode
    assert {n for _,n,_,_ in Formatter().parse(text) if n}=={'discount','curr'}
    assert '<tg-emoji emoji-id="6181681557946770158">✅</tg-emoji>' in text
    assert 'Պրոմոկոդն ակտիվացվել է. ստացել եք <code>50.0֏</code>։' in text.format(discount='50.0',curr='֏')

def test_receipt_icons_order_and_dynamic_values():
    template=BotTexts.Hy.TEXTS.receipt_purchase
    assert {n for _,n,_,_ in Formatter().parse(template) if n}=={'receipt','pos_name','sum','curr','count','date'}
    assert re.findall(r'emoji-id="(\d+)"',template)==['6181523988481581415','6181208703522317605','6183559145849890138','6181535786756743376','6181377573046461008','6181686548698767939']
    rendered=template.format(receipt='fixture-42',pos_name='Ապրանք | @fixture',sum='34999.0',curr='֏',count=1,date='28.09.2026 12:00:00')
    for value in ['fixture-42','Ապրանք | @fixture','34999.0֏','1 հատ','28.09.2026 12:00:00']:assert value in rendered
    for label in ['Անդորրագիր','Ապրանք՝','Գումար՝','Քանակ՝','Ամսաթիվ՝','Բովանդակություն՝']:assert label in rendered
