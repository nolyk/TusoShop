import asyncio
import colorama

from tgbot.handlers import userRouter, adminRouter
from tgbot.data.loader import dp, bot, adButtonRouter, scheduler
from tgbot.middlewares import setup_middlewares
from tgbot.utils.utils import check_rates, check_contests, check_updates, clear_stats_day, clear_stats_week
from tgbot.utils.models import async_main

colorama.init()

async def scheduler_start():
    scheduler.add_job(clear_stats_week, "cron", day_of_week="mon", hour=00)
    scheduler.add_job(clear_stats_day, "cron", hour=00)
    scheduler.add_job(check_rates, 'cron', hour=00)

async def main(*, initialize_database=True, handle_signals=True):
    # Запускаем настройку и проверку базы данных
    if initialize_database:
        await async_main()
        from tgbot.utils.mini_app_menu import sync_mini_app_menu
        from tgbot.data.config import DB, BotConfig
        await sync_mini_app_menu(bot, await DB.get_settings(), BotConfig.WEBAPP_URL)
    
    # Запускаем задания
    loop = asyncio.get_event_loop()
    tasks = [loop.create_task(job()) for job in (check_contests, check_rates, check_updates)]
    
    # Подключаем мидлвари к роутерам
    setup_middlewares(userRouter)
    setup_middlewares(adButtonRouter)
    setup_middlewares(adminRouter, admin_panel=True)
    
    # Запуск заданий
    await scheduler_start()
    scheduler.start()
    print(colorama.Fore.GREEN + "=====================================")
    print(colorama.Fore.RED + "Bot Was Started")
    print(colorama.Fore.LIGHTBLUE_EX + "Developer: https://t.me/nnolyk")
    print(colorama.Fore.GREEN + "=====================================" + colorama.Fore.RESET)
    
    # Удаляем ненужный нам вебхук
    await bot.delete_webhook(drop_pending_updates=False)
    
    # В дистпетчер включаем наши роутеры и запускаем бота
    dp.include_routers(userRouter, adminRouter, adButtonRouter)    
    try:
        await dp.start_polling(bot, handle_signals=handle_signals, close_bot_session=False)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
