from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MONEY_STEP = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class DigitalQuote:
    product_type: str
    quantity: Decimal
    currency: str
    base_amount: Decimal
    markup_percent: Decimal
    markup_amount: Decimal
    total_amount: Decimal


def calculate_quote(
    *,
    product_type: str,
    quantity: int | Decimal,
    unit_price: Decimal,
    markup_percent: Decimal = Decimal("0"),
    currency: str = "RUB",
) -> DigitalQuote:
    if product_type not in {"stars", "premium", "gift"}:
        raise ValueError("Unsupported digital product")
    quantity_value = Decimal(str(quantity))
    price_value = Decimal(str(unit_price))
    markup_value = Decimal(str(markup_percent))
    if quantity_value <= 0 or price_value < 0:
        raise ValueError("Quantity must be positive and price cannot be negative")
    if markup_value < 0 or markup_value > 500:
        raise ValueError("Markup must be between 0 and 500 percent")
    base = (quantity_value * price_value).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    markup = (base * markup_value / Decimal("100")).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    return DigitalQuote(
        product_type=product_type,
        quantity=quantity_value,
        currency=currency.upper(),
        base_amount=base,
        markup_percent=markup_value,
        markup_amount=markup,
        total_amount=base + markup,
    )
