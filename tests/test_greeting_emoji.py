from string import Formatter
from tgbot.data.config import BotTexts

def test_greeting_icons_keep_username():
    text=BotTexts.Hy.TEXTS.main_menu
    assert '<tg-emoji emoji-id="6183704354399200886">👑</tg-emoji>' in text
    assert '<tg-emoji emoji-id="6181530044385468714">⬇</tg-emoji>' in text
    assert {n for _,n,_,_ in Formatter().parse(text) if n}=={'username'}
    assert 'Fixture, բարի գալուստ <b>ԹույնShop</b>։' in text.format(username='Fixture')
    assert 'Ընտրեք բաժինը ցանկից՝' in text

def test_amount_prompt_has_no_trailing_mark():
    assert BotTexts.Hy.TEXTS.enter_amount_of_refill=='<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji><b> Մուտքագրեք լիցքավորման գումարը</b>'
