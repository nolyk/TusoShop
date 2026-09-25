from aiogram import Router
from tgbot.middlewares.exists_user import ExistsUserMiddleware
from tgbot.middlewares.language import UserLanguageMiddleware
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.middlewares.switchers import SwitchersMiddleware


def setup_middlewares(router: Router, admin_panel: bool = False):
    router.message.middleware(ThrottlingMiddleware())
    router.callback_query.middleware(ThrottlingMiddleware())
    ###
    router.message.middleware(ExistsUserMiddleware())
    router.callback_query.middleware(ExistsUserMiddleware())
    ###
    router.message.middleware(UserLanguageMiddleware(admin_panel=admin_panel))
    router.callback_query.middleware(UserLanguageMiddleware(admin_panel=admin_panel))
    ###
    router.message.middleware(SwitchersMiddleware())
    router.callback_query.middleware(SwitchersMiddleware())
    
