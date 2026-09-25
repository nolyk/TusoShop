import base64
import time
from unittest.mock import AsyncMock
import pytest
from tonsdk.boc import Cell
from tgbot.integrations.fragment import FragmentClient, FragmentCredentials, FragmentError, parse_transaction


def transaction(amount='100000001'):
    cell = Cell()
    cell.bits.write_uint(0, 32)
    cell.bits.write_string('Exact Fragment payload')
    return {'validUntil':int(time.time())+300, 'messages':[{'address':'0:'+'1'*64, 'amount':amount, 'payload':base64.b64encode(cell.to_boc()).decode()}]}


@pytest.mark.asyncio
@pytest.mark.parametrize('product,quantity,search,init,link', [
    ('stars',50,'searchStarsRecipient','initBuyStarsRequest','getBuyStarsLink'),
    ('premium',12,'searchPremiumGiftRecipient','initGiftPremiumRequest','getGiftPremiumLink')])
async def test_fragment_original_protocol_preserves_boc(product,quantity,search,init,link):
    client=FragmentClient(FragmentCredentials('fixture', {'stel_ssid':'fixture'}))
    tx=transaction()
    async def request(session,method,**values):
        if method==search:return {'found':{'recipient':'recipient-id'}}
        if method==init:return {'req_id':'request-id'}
        if method==link:return {'ok':True,'transaction':tx}
        return {'ok':True}
    client._request=AsyncMock(side_effect=request)
    plan=await client.prepare(product,'@example',quantity,max_total_nanoton=200000000,account={'address':'0:'+'2'*64})
    assert plan.total_nanoton==100000001
    assert plan.messages[0].payload_b64==tx['messages'][0]['payload']
    assert plan.request_id=='request-id' and plan.recipient=='example'
    assert client._request.call_args_list[-1].args[1]==link
    assert not hasattr(client, 'transfer')


@pytest.mark.parametrize('kind',['over_budget','float','expired','bad_payload','empty','state_init','invalid_address','aggregate_budget'])
def test_fragment_rejects_unsafe_plan(kind):
    tx=transaction();now=int(time.time())
    if kind=='over_budget':tx['messages'][0]['amount']='300000000'
    if kind=='float':tx['messages'][0]['amount']='1.5'
    if kind=='expired':tx['validUntil']=now-1
    if kind=='bad_payload':tx['messages'][0]['payload']='not valid'
    if kind=='empty':tx['messages']=[]
    if kind=='state_init':tx['messages'][0]['stateInit']='unexpected'
    if kind=='invalid_address':tx['messages'][0]['address']='not-address'
    if kind=='aggregate_budget':tx['messages']*=2
    with pytest.raises(FragmentError):parse_transaction(tx,max_total_nanoton=200000000,now=now)


def test_fragment_credentials_never_in_repr(monkeypatch):
    cred=FragmentCredentials('private-hash',{'stel_ssid':'private-cookie'})
    assert 'private' not in repr(cred)
    monkeypatch.setenv('FRAGMENT_HASH','fragment_api_hash')
    monkeypatch.setenv('FRAGMENT_COOKIES','{"stel_ssid":"fragment_session_cookie"}')
    with pytest.raises(FragmentError):FragmentCredentials.from_environment()


@pytest.mark.asyncio
async def test_fragment_bad_quantity_does_not_call_provider():
    client=FragmentClient(FragmentCredentials('fixture',{}));client._request=AsyncMock()
    with pytest.raises(FragmentError):await client.prepare('stars','example',49,max_total_nanoton=100,account={'address':'fixture'})
    client._request.assert_not_called()
