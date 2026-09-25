from decimal import Decimal

import pytest

from tgbot.services.digital_shop import DigitalOrderState, calculate_quote, validate_transition


def test_quote_uses_decimal_and_rounds_money():
    quote = calculate_quote(
        product_type="stars", quantity=51, unit_price=Decimal("1.505"), markup_percent=Decimal("7.5")
    )
    assert quote.base_amount == Decimal("76.76")
    assert quote.markup_amount == Decimal("5.76")
    assert quote.total_amount == Decimal("82.52")


def test_order_state_machine_accepts_happy_path():
    path = [
        DigitalOrderState.CREATED,
        DigitalOrderState.AWAITING_PAYMENT,
        DigitalOrderState.PAID,
        DigitalOrderState.PROCESSING,
        DigitalOrderState.COMPLETED,
    ]
    for current, target in zip(path, path[1:]):
        validate_transition(current, target)


def test_order_state_machine_rejects_double_fulfillment():
    with pytest.raises(ValueError):
        validate_transition(DigitalOrderState.COMPLETED, DigitalOrderState.PROCESSING)
