from string import Formatter
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
import pytest
from tgbot.data.config import BotTexts,DB
from tgbot.keyboards.users import InlineButtons
from tgbot.handlers.users import digital_shop as digital

def test_profile_fields_and_armenian_text():
    text=BotTexts.Hy.TEXTS.profile_text
    assert {name for _,name,_,_ in Formatter().parse(text) if name} == {'username','user_id','balance','curr','total_refill','reg_date'}
    for id,emoji,label in [('6183468706723537731','👤','Ձեր էջը'),('6181478659396739452','👤','Օգտատեր'),('6181548602939155001','👤','ID'),('6181423645160646167','👛','Հաշվեկշիռ'),('6183559145849890138','🪙','Ընդամենը լիցքավորված'),('6181440610281464581','✍','Գրանցման ամսաթիվ')]:
        assert f'<tg-emoji emoji-id="{id}">{emoji}</tg-emoji> {label}՝' in text
    rendered=text.format(username='Fixture',user_id=123,balance='100.00',curr='֏',total_refill='250.00',reg_date='28.09.2026')
    for value in ['Fixture','123','100.00֏','250.00֏','28.09.2026']:assert value in rendered

def test_support_refill_and_stars_headers():
    assert '<tg-emoji emoji-id="6183774199157367778">🆘</tg-emoji> Աջակցությանը' in BotTexts.Hy.TEXTS.support_text
    assert '<tg-emoji emoji-id="6181612022426247965">💸</tg-emoji> Ընտրեք' in BotTexts.Hy.TEXTS.choose_refill_method
    assert "<tg-emoji emoji-id='6181365645922281493'>⭐</tg-emoji> Գնեք" in digital.DIGITAL_HOME_TEXT

@pytest.mark.asyncio
@pytest.mark.parametrize('ref',[True,False])
async def test_profile_actions(monkeypatch,ref):
    monkeypatch.setattr(DB,'get_settings',AsyncMock(return_value=Obj(is_ref=ref)))
    menu=(await InlineButtons().profile_menu(BotTexts.Hy)).as_markup()
    buttons={b.callback_data:b for row in menu.inline_keyboard for b in row}
    assert ('ref_system' in buttons)==ref
    for callback,label,id in [('activate_promo','Պրոմոկոդ','6183777454742577008'),('purchases_history','Պատմություն','6181724391655613194')]+([('ref_system','Հրավիրումների համակարգ','6181676644504185221')] if ref else []):
        assert buttons[callback].text==label
        assert buttons[callback].icon_custom_emoji_id==id
    assert buttons['back_to_user_menu'].text=='Հետ'

@pytest.mark.asyncio
@pytest.mark.parametrize('enabled',[True,False])
async def test_digital_buttons_visibility_and_ids(monkeypatch,enabled):
    monkeypatch.setattr(digital.digital_shop_repository,'product_enabled',AsyncMock(side_effect=lambda product:enabled and product in ('stars','premium')))
    menu=await digital.digital_home_keyboard()
    buttons={b.callback_data:b for row in menu.inline_keyboard for b in row}
    assert ('digital:stars' in buttons)==enabled
    assert ('digital:premium' in buttons)==enabled
    expected=[('digital:orders','Իմ պատվերները','6181208703522317605')]
    if enabled:expected += [('digital:stars','Գնել Stars','6181597355112932310'),('digital:premium','Գնել Premium','6181700898184503901')]
    for callback,label,id in expected:
        assert buttons[callback].text==label
        assert buttons[callback].icon_custom_emoji_id==id
