from enum import Enum


class DigitalOrderState(str, Enum):
    CREATED = "created"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FULFILLMENT_FAILED = "fulfillment_failed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


ALLOWED_TRANSITIONS = {
    DigitalOrderState.CREATED: {DigitalOrderState.AWAITING_PAYMENT, DigitalOrderState.CANCELLED},
    DigitalOrderState.AWAITING_PAYMENT: {DigitalOrderState.PAID, DigitalOrderState.CANCELLED},
    DigitalOrderState.PAID: {DigitalOrderState.PROCESSING, DigitalOrderState.REFUND_PENDING},
    DigitalOrderState.PROCESSING: {DigitalOrderState.COMPLETED, DigitalOrderState.FULFILLMENT_FAILED},
    DigitalOrderState.FULFILLMENT_FAILED: {DigitalOrderState.PROCESSING, DigitalOrderState.REFUND_PENDING},
    DigitalOrderState.REFUND_PENDING: {DigitalOrderState.REFUNDED},
    DigitalOrderState.COMPLETED: set(),
    DigitalOrderState.CANCELLED: set(),
    DigitalOrderState.REFUNDED: set(),
}


def validate_transition(current: str | DigitalOrderState, target: str | DigitalOrderState) -> None:
    current_state = DigitalOrderState(current)
    target_state = DigitalOrderState(target)
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise ValueError(f"Invalid digital order transition: {current_state.value} -> {target_state.value}")
