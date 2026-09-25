from pathlib import Path
import re


def test_miniapp_ui_is_armenian():
    root=Path('tgbot/webapp/static')
    for name in ('index.html','app.js'):
        text=(root/name).read_text(encoding='utf-8')
        assert not re.search('[А-Яа-яЁё]',text),name
    html=(root/'index.html').read_text(encoding='utf-8')
    assert 'lang="hy"' in html
    assert all(label in html for label in ['Խանութ','Պատմություն','Իմ էջը','Լիցքավորել'])
    js=(root/'app.js').read_text(encoding='utf-8')
    assert "button: 'Գնել'" in js
    assert 'hy-AM' in js


def test_icons_and_digital_logos_have_compact_limits():
    css=Path('tgbot/webapp/static/styles.css').read_text(encoding='utf-8')
    assert '.icon{width:18px;height:18px;max-width:24px;max-height:24px' in css
    assert '#digital-products .catalog-cover img{width:54px;height:54px' in css


def test_api_display_strings_have_no_russian():
    api=Path('tgbot/webapp/app.py').read_text(encoding='utf-8')
    assert not re.search('[А-Яа-яЁё]',api)
    assert 'Սպասում է վճարմանը' in api
    assert 'Վճարում աստղերով Telegram-ում' in api
    assert 'Պատվերը չի գտնվել' in api
