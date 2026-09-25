"""Fragment request protocol adapted from starshop/api.py.

This module prepares an unsigned plan only. It cannot send TON or complete orders.
Keep the raw BOC body and integer nanoTON amounts for the future wallet executor.
"""
import base64
import json
import os
import re
import time
from dataclasses import dataclass, field

import aiohttp


class FragmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class FragmentCredentials:
    api_hash: str = field(repr=False)
    cookies: dict[str, str] = field(repr=False)

    @classmethod
    def from_environment(cls):
        try:
            cookies = json.loads(os.environ.get('FRAGMENT_COOKIES', '{}'))
            api_hash = os.environ.get('FRAGMENT_HASH', '').strip()
            if not api_hash or api_hash == 'fragment_api_hash' or not isinstance(cookies, dict):
                raise ValueError
            if not cookies.get('stel_ssid') or cookies['stel_ssid'] == 'fragment_session_cookie':
                raise ValueError
            if any(not isinstance(k, str) or not isinstance(v, str) for k, v in cookies.items()):
                raise ValueError
        except (ValueError, TypeError):
            raise FragmentError('Fragment credentials are not configured') from None
        return cls(api_hash, cookies)


@dataclass(frozen=True)
class FragmentMessage:
    address: str
    amount_nanoton: int
    payload_b64: str


@dataclass(frozen=True)
class FragmentPlan:
    request_id: str
    product: str
    recipient: str
    quantity: int
    valid_until: int
    messages: tuple[FragmentMessage, ...]

    @property
    def total_nanoton(self):
        return sum(message.amount_nanoton for message in self.messages)


def parse_transaction(raw: dict, *, max_total_nanoton: int, now: int) -> tuple[int, tuple[FragmentMessage, ...]]:
    from tonsdk.boc import Cell
    from tonsdk.utils import Address
    if type(max_total_nanoton) is not int or max_total_nanoton <= 0:
        raise FragmentError('A positive approved spending limit is required')
    try:
        expiry = raw.get('validUntil', raw.get('valid_until'))
        if type(expiry) is not int or not now < expiry <= now + 3600:
            raise ValueError
        rows = raw['messages']
        if not isinstance(rows, list) or not 1 <= len(rows) <= 4:
            raise ValueError
        result = []
        for row in rows:
            if not isinstance(row, dict) or row.get('stateInit') or row.get('state_init') or row.get('extraCurrency'):
                raise ValueError
            address = row['address']
            if not isinstance(address, str):
                raise ValueError
            Address(address)
            amount = row['amount']
            if isinstance(amount, bool) or not re.fullmatch(r'[0-9]{1,20}', str(amount)):
                raise ValueError
            amount = int(amount)
            if not 0 < amount <= max_total_nanoton:
                raise ValueError
            payload = row['payload']
            if not isinstance(payload, str) or not 1 <= len(payload) <= 65536:
                raise ValueError
            body = base64.b64decode(payload + '=' * (-len(payload) % 4), validate=True)
            Cell.one_from_boc(body)  # Validate without converting binary data to a string.
            result.append(FragmentMessage(address, amount, payload))
        if sum(item.amount_nanoton for item in result) > max_total_nanoton:
            raise ValueError
        return expiry, tuple(result)
    except Exception:
        raise FragmentError('Invalid, expired or over-budget Fragment transaction') from None


class FragmentClient:
    def __init__(self, credentials: FragmentCredentials):
        self.credentials = credentials

    async def _request(self, session, method: str, **values):
        try:
            async with session.post('https://fragment.com/api', params={'hash': self.credentials.api_hash},
                                    data={'method': method, **values}, allow_redirects=False) as response:
                if response.status != 200:
                    raise FragmentError('Fragment request failed')
                body = await response.content.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise FragmentError('Fragment response is too large')
                value = json.loads(body)
                if not isinstance(value, dict) or value.get('error'):
                    raise FragmentError('Fragment rejected the request')
                return value
        except (aiohttp.ClientError, TimeoutError, ValueError):
            # Never put session cookies, API hash or provider responses into logs/errors.
            raise FragmentError('Fragment is unavailable') from None

    async def prepare(self, product: str, username: str, quantity: int, *, max_total_nanoton: int, account: dict) -> FragmentPlan:
        username = username.strip().lstrip('@')
        if product not in {'stars', 'premium'} or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,31}', username):
            raise FragmentError('Invalid product or recipient')
        if type(quantity) is not int or (product == 'stars' and not 50 <= quantity <= 4999) or (product == 'premium' and quantity not in {3, 6, 12}):
            raise FragmentError('Invalid quantity')
        if type(max_total_nanoton) is not int or max_total_nanoton <= 0:
            raise FragmentError('A positive approved spending limit is required')
        if not isinstance(account, dict) or not account.get('address'):
            raise FragmentError('Wallet account is required')
        stars = product == 'stars'
        async with aiohttp.ClientSession(cookies=self.credentials.cookies, timeout=aiohttp.ClientTimeout(total=20),
                                         headers={'User-Agent':'Mozilla/5.0'}) as session:
            await self._request(session, 'updateStarsBuyState' if stars else 'updatePremiumState', mode='new', lv='false', dh='1')
            found = await self._request(session, 'searchStarsRecipient' if stars else 'searchPremiumGiftRecipient', query=username, **({'quantity': str(quantity)} if stars else {}))
            recipient = found.get('found', {}).get('recipient') if isinstance(found.get('found'), dict) else None
            if not isinstance(recipient, str) or not recipient:
                raise FragmentError('Fragment recipient not found')
            if stars:
                await self._request(session, 'updateStarsPrices', stars='', quantity=str(quantity))
            init = await self._request(session, 'initBuyStarsRequest' if stars else 'initGiftPremiumRequest', recipient=recipient, **({'quantity':str(quantity)} if stars else {'months':str(quantity)}))
            request_id = init.get('req_id')
            if not isinstance(request_id, str) or not request_id:
                raise FragmentError('Fragment request was not created')
            device = {'platform':'browser', 'appName':'telegram-wallet', 'appVersion':'1', 'maxProtocolVersion':2,
                      'features':['SendTransaction', {'name':'SendTransaction','maxMessages':4}]}
            result = await self._request(session, 'getBuyStarsLink' if stars else 'getGiftPremiumLink',
                                         account=json.dumps(account), device=json.dumps(device), transaction='1', id=request_id, show_sender='0')
        if result.get('ok') is not True or not isinstance(result.get('transaction'), dict):
            raise FragmentError('Fragment transaction is unavailable')
        expiry, messages = parse_transaction(result['transaction'], max_total_nanoton=max_total_nanoton, now=int(time.time()))
        return FragmentPlan(request_id, product, username, quantity, expiry, messages)
