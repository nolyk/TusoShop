from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from decimal import Decimal
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from tgbot.webapp import app as web


@pytest.mark.asyncio
async def test_catalog_category_description_and_photo_proxy(monkeypatch):
    monkeypatch.setattr(web.digital_shop_repository, 'product_enabled', AsyncMock(return_value=True))
    monkeypatch.setattr(web.DB, 'get_settings', AsyncMock(return_value=Obj(is_buy=True, currency=Obj(value='rub'))))
    monkeypatch.setattr(web.DB, 'get_all_positions', AsyncMock(return_value=[Obj(pos_id=7, cat_id=2, sub_cat_id=3, name='Game', description='Full details', price_rub=150, is_infinity=True, photo='telegram-file-id')]))
    monkeypatch.setattr(web.DB, 'get_category', AsyncMock(return_value=Obj(name='Games')))
    monkeypatch.setattr(web.DB, 'get_subcategory', AsyncMock(return_value=Obj(name='Keys')))
    product = (await web.digital_products())['products'][0]
    assert product['category_name'] == 'Games' and product['subcategory_name'] == 'Keys'
    assert product['description'] == 'Full details'
    assert product['image'] == '/api/shop/products/7/photo'
    assert 'telegram-file-id' not in str(product)


@pytest.mark.asyncio
async def test_photo_download_hides_token_and_serves_image(monkeypatch):
    import aiogram
    monkeypatch.setattr(web.DB, 'get_settings', AsyncMock(return_value=Obj(is_buy=True)))
    monkeypatch.setattr(web.DB, 'get_position', AsyncMock(return_value=Obj(photo='file-id')))
    async def download(path, destination, timeout):
        destination.write(b'\xff\xd8\xfffixture')
    bot = Obj(get_file=AsyncMock(return_value=Obj(file_path='photos/cover.jpg', file_size=10)), download_file=download, session=Obj(close=AsyncMock()))
    monkeypatch.setattr(aiogram, 'Bot', lambda token: bot)
    response = await web.product_photo(7)
    assert response.media_type == 'image/jpeg'
    assert response.body == b'\xff\xd8\xfffixture'
    bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('photo', ['https://internal.example/image', '-', None])
async def test_photo_endpoint_rejects_arbitrary_urls(monkeypatch, photo):
    monkeypatch.setattr(web.DB, 'get_settings', AsyncMock(return_value=Obj(is_buy=True)))
    monkeypatch.setattr(web.DB, 'get_position', AsyncMock(return_value=Obj(photo=photo)))
    with pytest.raises(HTTPException) as exc:
        await web.product_photo(7)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('product,quantity,mode', [('stars',50,'self'),('stars',123,'other'),('premium',6,'other')])
async def test_quote_recipient_price_and_payment_remains_off(monkeypatch,product,quantity,mode):
    monkeypatch.setattr(web.digital_shop_repository, 'product_enabled', AsyncMock(return_value=True))
    from tgbot.integrations.marketapp import marketapp
    monkeypatch.setattr(web.DB,'get_settings',AsyncMock(return_value=Obj(is_buy=True,is_work=False)))
    for field in ('DIGITAL_SHOP_ENABLED','DIGITAL_STARS_ENABLED','DIGITAL_PREMIUM_ENABLED'):
        monkeypatch.setattr(web.BotConfig,field,True)
    monkeypatch.setattr(marketapp,'recipient',AsyncMock(return_value={'name':'Customer'}))
    monkeypatch.setattr(marketapp,'stars_price_ton',AsyncMock(return_value=Decimal('2')))
    monkeypatch.setattr(marketapp,'premium_price_ton',AsyncMock(return_value=Decimal('2')))
    monkeypatch.setattr(marketapp,'ton_rub_rate',AsyncMock(return_value=Decimal('100')))
    monkeypatch.setattr(web.digital_shop_repository,'get_setting',AsyncMock(return_value='5'))
    user=Obj(is_ban=False,user_name='ownname')
    result=await web.digital_quote(web.DigitalQuoteRequest(product=product,quantity=quantity,recipient_mode=mode,username='friendname'),user)
    assert result['total']=='210.00' and result['payment_enabled'] is False
    assert result['recipient']==('ownname' if mode=='self' else 'friendname')


@pytest.mark.asyncio
@pytest.mark.parametrize('product,quantity', [('stars',49),('stars',5000),('premium',4)])
async def test_quote_limits_enforced_on_server(monkeypatch,product,quantity):
    monkeypatch.setattr(web.DB,'get_settings',AsyncMock(return_value=Obj(is_buy=True,is_work=False)))
    for field in ('DIGITAL_SHOP_ENABLED','DIGITAL_STARS_ENABLED','DIGITAL_PREMIUM_ENABLED'):
        monkeypatch.setattr(web.BotConfig,field,True)
    with pytest.raises(HTTPException) as exc:
        await web.digital_quote(web.DigitalQuoteRequest(product=product,quantity=quantity,recipient_mode='self'),Obj(is_ban=False,user_name='ownname'))
    assert exc.value.status_code==422


def test_fractional_stars_rejected():
    with pytest.raises(ValidationError):
        web.DigitalQuoteRequest(product='stars',quantity=50.5,recipient_mode='self')


def test_category_tiles_replace_top_filter_pills():
    from pathlib import Path
    js = Path('tgbot/webapp/static/app.js').read_text(encoding='utf-8')
    html = Path('tgbot/webapp/static/index.html').read_text(encoding='utf-8')
    css = Path('tgbot/webapp/static/styles.css').read_text(encoding='utf-8')
    assert 'class="category-grid" id="categories"' in html
    assert 'data-category=' in js and 'data-filter=' not in js
    assert "$('#products').hidden = atRoot" in js
    assert "$('#categories-back').onclick" in js
    assert '.category-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))' in css
