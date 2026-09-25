import aiohttp
import json
import hmac
import hashlib
import time
import random
import secrets

from yoomoney import Quickpay, Client


def _require(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{name} is empty")
    return value


class CryptoPay:
    def __init__(self, token: str, host: str = "pay.crypt.bot") -> None:
        self.token = _require(token, "crypto_token")
        self.base_url = f"https://{host.strip().strip('/')}/api"
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def _request(self, method: str, payload: dict | None = None) -> dict:
        headers = {
            "Crypto-Pay-API-Token": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
            async with session.post(f"{self.base_url}/{method}", json=payload or {}) as response:
                data = await response.json(content_type=None)
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or data)
        return data["result"]

    async def create_invoice(
        self,
        amount: float,
        fiat: str,
        description: str,
        success_url: str,
        payload: str,
    ) -> dict:
        return await self._request("createInvoice", {
            "currency_type": "fiat",
            "fiat": fiat.upper(),
            "amount": f"{float(amount):.2f}",
            "description": description[:1024],
            "payload": payload,
            "paid_btn_name": "callback",
            "paid_btn_url": success_url,
            "expires_in": 3600,
            "allow_comments": False,
            "allow_anonymous": True,
        })

    async def is_paid(self, invoice_id: str) -> bool:
        result = await self._request("getInvoices", {"invoice_ids": str(invoice_id), "count": 1})
        items = result.get("items", result if isinstance(result, list) else [])
        return bool(items and str(items[0].get("status")) == "paid")

    async def get_invoices(self, invoice_ids: str, count: int = 1) -> list[dict]:
        result = await self._request("getInvoices", {
            "invoice_ids": str(invoice_ids),
            "count": int(count),
        })
        return result.get("items", result if isinstance(result, list) else [])

    async def get_balance(self) -> list[dict]:
        return await self._request("getBalance")


class XRocketPay:
    def __init__(
        self,
        token: str,
        asset: str = "USDT",
        base_url: str = "https://pay.xrocket.tg",
    ) -> None:
        self.token = _require(token, "xrocket_token")
        self.asset = (asset or "USDT").upper()
        self.base_url = base_url.rstrip("/")
        self.pay_api_url = "https://pay.api.xrocket.exchange"
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        headers = {
            "Rocket-Pay-Key": self.token,
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
            async with session.request(method, f"{self.base_url}{path}", json=payload, params=params) as response:
                data = await response.json(content_type=None)
        if response.status >= 400 or (isinstance(data, dict) and data.get("success") is False):
            raise RuntimeError(data)
        return data

    async def _pay_api_request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
            async with session.request(method, f"{self.pay_api_url}{path}", json=payload, params=params) as response:
                data = await response.json(content_type=None)
                status = response.status
        if status >= 400 or (isinstance(data, dict) and data.get("type")):
            raise RuntimeError(data)
        return data

    async def create_invoice(self, amount: float, description: str, payload: str, success_url: str = "") -> dict:
        legacy_payload = {
            "amount": float(amount),
            "currency": self.asset,
            "description": description[:1024],
            "hiddenMessage": payload,
            "callbackUrl": "",
            "payload": payload,
            "expiredIn": 3600,
        }
        try:
            data = await self._request("POST", "/tg-invoices", legacy_payload)
            return data.get("data", data)
        except RuntimeError:
            data = await self._pay_api_request("POST", "/api/v1/invoices", {
                "priceAmount": f"{float(amount):.2f}",
                "priceCurrency": self.asset,
                "payCurrencies": [self.asset],
                "clientInvoiceId": payload[-64:],
                "description": description[:1024],
                "expiresIn": 3_600_000,
                "callback": {"payload": {"payload": payload}},
                "url": {"successUrl": success_url, "cancelUrl": success_url},
            })
            return data

    async def invoice(self, invoice_id: str) -> dict:
        try:
            data = await self._request("GET", f"/tg-invoices/{invoice_id}")
            return data.get("data", data)
        except RuntimeError:
            try:
                return await self._pay_api_request("GET", "/api/v1/invoice", params={"invoiceId": invoice_id})
            except RuntimeError:
                return await self._pay_api_request("GET", "/api/v1/invoice", params={"clientInvoiceId": invoice_id})

    async def is_paid(self, invoice_id: str) -> bool:
        invoice = await self.invoice(invoice_id)
        return str(invoice.get("status", "")).lower() in {"paid", "success", "finished"}

    async def get_balance(self) -> list[dict]:
        try:
            data = await self._request("GET", "/app/balance")
            result = data.get("data", data)
        except RuntimeError:
            result = await self._pay_api_request("GET", "/api/v1/balances")
        if isinstance(result, dict):
            return result.get("balances", result.get("items", result.get("results", [result])))
        return result if isinstance(result, list) else []


class Lava:
    def __init__(self, shop_id: str, secret_token: str) -> None:
        self.shop_id = shop_id
        self.secret = secret_token
        self.base_url = "https://api.lava.ru/"
        self.timeout = aiohttp.ClientTimeout(total=360)

    def _signature_headers(self, data: dict) -> dict:
        jsonStr = json.dumps(data).encode()
        sign = hmac.new(bytes(self.secret, 'UTF-8'), jsonStr, hashlib.sha256).hexdigest()
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Signature': sign
        }
        return headers

    async def create_invoice(self, amount: float, success_url: str, comment: str) -> dict:
        url = f"{self.base_url}/business/invoice/create"
        params = {
            "sum": amount,
            "shopId": self.shop_id,
            "successUrl": success_url,
            "orderId": f'{time.time()}_{secrets.token_hex(random.randint(5, 10))}',
            "comment": comment
        }
        headers = self._signature_headers(params)
        async with aiohttp.ClientSession(headers=headers, timeout=self.timeout) as session:
            response = await session.post(url=url, headers=headers, json=params)
            res = await response.json()
            await session.close()
        return res

    async def status_invoice(self, invoice_id: str) -> bool:
        url = f"{self.base_url}/business/invoice/status"
        params = {
            "shopId": self.shop_id,
            "invoiceId": invoice_id
        }
        headers = self._signature_headers(params)
        async with aiohttp.ClientSession(headers=headers, timeout=self.timeout) as session:
            response = await session.post(url=url, headers=headers, json=params)
            res = await response.json()
            await session.close()
        return res['data']['status'] == "success"

    async def get_balance(self) -> dict:
        params = {'shopId': self.shop_id}
        headers = self._signature_headers(params)
        async with aiohttp.ClientSession(headers=headers, timeout=self.timeout) as session:
            request = await session.post('https://api.lava.ru/business/shop/get-balance', json=params, headers=headers)
            response = await request.json()
            await session.close()
            return response


class YooMoney:
    def __init__(self, token, number):
        self.token = token
        self.number = number
        self.client = Client(token)

    def create_yoomoney_link(self, amount: float, comment: str) -> dict:
        payment_form = dict()
        number = self.number
        quick_pay = Quickpay(
            receiver=number,
            quickpay_form="shop",
            targets="Balance refill",
            paymentType="SB",
            sum=amount,
            label=comment
        )
        payment_form["link"] = quick_pay.base_url
        payment_form['comment'] = quick_pay.label
        payment_form["key"] = "Number"
        payment_form["value"] = number
        return payment_form

    def check_yoomoney_payment(self, comment: str) -> bool:
        for operation in self.client.operation_history(label=comment).operations:
            comment_payment = str(operation.label)
            if comment_payment == comment:
                return True
        return False

    def get_balance(self):
        return self.client.account_info().balance
