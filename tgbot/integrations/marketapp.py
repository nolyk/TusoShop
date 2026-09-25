import time
from decimal import Decimal
from typing import Any

import httpx

from tgbot.data.config import BotConfig


class MarketAppError(RuntimeError):
    pass


class MarketAppClient:
    def __init__(self) -> None:
        self.base_url = BotConfig.MARKETAPP_API_URL
        self.token = BotConfig.MARKETAPP_API_TOKEN
        self.timeout = BotConfig.MARKETAPP_TIMEOUT
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        if not self.token:
            raise MarketAppError("MarketApp не настроен")
        headers = {"Authorization": self.token, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=self.timeout) as client:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MarketAppError("MarketApp временно недоступен") from exc
        if not isinstance(data, dict):
            raise MarketAppError("MarketApp вернул неизвестный формат")
        return data

    async def cached_request(self, key: str, ttl: int, method: str, path: str, **kwargs) -> dict[str, Any]:
        cached = self._cache.get(key)
        if cached and time.time() - cached[0] < ttl:
            return cached[1]
        data = await self.request(method, path, **kwargs)
        self._cache[key] = (time.time(), data)
        return data

    async def stars_price_ton(self, quantity: int) -> Decimal:
        data = await self.cached_request(
            f"stars:{quantity}", 600, "POST", "/v1/fragment/stars/price/", json={"quantity": quantity}
        )
        value = Decimal(str(data.get("gram", data.get("ton", "0"))))
        if value <= 0:
            raise MarketAppError("Цена Stars временно недоступна")
        return value

    async def premium_price_ton(self, months: int) -> Decimal:
        data = await self.cached_request("premium", 21600, "POST", "/v1/fragment/premium/price/")
        option = data.get(f"months{months}") or {}
        value = Decimal(str(option.get("gram", option.get("ton", "0"))))
        if value <= 0:
            raise MarketAppError("Цена Premium временно недоступна")
        return value

    async def recipient(self, product: str, username: str) -> dict[str, Any]:
        if product not in {"stars", "premium"}:
            raise MarketAppError("Неизвестный цифровой продукт")
        return await self.request(
            "POST", f"/v1/fragment/{product}/recipient/", json={"username": username.lstrip("@").strip()}
        )

    async def ton_rub_rate(self) -> Decimal:
        headers = {"Authorization": f"Bearer {BotConfig.TONAPI_KEY}"} if BotConfig.TONAPI_KEY else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://tonapi.io/v2/rates?tokens=ton&currencies=rub", headers=headers
                )
                response.raise_for_status()
                value = Decimal(str(response.json()["rates"]["TON"]["prices"]["RUB"]))
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise MarketAppError("Курс TON/RUB временно недоступен") from exc
        if value <= 0:
            raise MarketAppError("Получен некорректный курс TON/RUB")
        return value


marketapp = MarketAppClient()
