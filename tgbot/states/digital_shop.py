from aiogram.fsm.state import State, StatesGroup


class DigitalPurchase(StatesGroup):
    stars_amount = State()
    recipient = State()


class DigitalAdmin(StatesGroup):
    mnemonic = State()
