from aiogram.fsm.state import State, StatesGroup


class UserRefills(StatesGroup):
    enter_amount = State()
    enter_receipt_for_custom_pay_method = State()


class UserPromocodes(StatesGroup):
    enter_promo = State()
    
    
class UserProducts(StatesGroup):
    enter_count_products_for_buy = State()