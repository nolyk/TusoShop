from string import Formatter
import re
from tgbot.data.config import BotTexts

def test_referral_icons_and_dynamic_fields():
    texts=BotTexts.Hy.TEXTS
    assert {n for _,n,_,_ in Formatter().parse(texts.ref_text) if n}=={'ref_link','ref_percent','reffer','ref_earn','curr','ref_count','convert_ref','ref_lvl','mss'}
    assert re.findall(r'emoji-id="(\d+)"',texts.ref_text)==['6181676644504185221','6181491892190978963','6181612022426247965','6181512409249750964','6181405799571531484','6181405799571531484','6181319861570905738']
    assert '<tg-emoji emoji-id="6183489966811653469">📝</tg-emoji>' in texts.next_lvl_remain
    rendered=texts.ref_text.format(ref_link='<code>https://t.me/FixtureBot?start=789</code>',ref_percent='12.5',reffer='Fixture',ref_earn='250.0',curr='֏',ref_count=7,convert_ref='հրավիրված օգտատեր',ref_lvl=2,mss=texts.next_lvl_remain.format(remain_refs=3,person_s='մարդ'))
    for value in ['https://t.me/FixtureBot?start=789','12.5%','250.0֏','<code>7</code>','<code>2</code>','3 մարդ','Fixture']:assert value in rendered
    assert 'Հրավիրումների համակարգ' in rendered
    assert rendered.count('<b>')==rendered.count('</b>')

def test_referral_max_level_still_renders():
    texts=BotTexts.Hy.TEXTS
    rendered=texts.ref_text.format(ref_link='LINK',ref_percent=10,reffer=texts.nobody,ref_earn=0,curr='֏',ref_count=100,convert_ref='հրավիրված օգտատեր',ref_lvl=3,mss=texts.cur_max_lvl)
    assert 'Դուք առավելագույն մակարդակում եք։' in rendered
    assert 'Հաջորդ մակարդակին' not in rendered
    assert rendered.count('<b>')==rendered.count('</b>')
