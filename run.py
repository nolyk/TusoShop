"""One Railway service: PostgreSQL initialization, Mini App and Telegram polling."""
import asyncio
import logging
import os
from urllib.parse import urlsplit

import uvicorn
from aiogram.types import MenuButtonWebApp, WebAppInfo
from sqlalchemy import text

from main import main as run_bot
from tgbot.data.config import BotConfig
from tgbot.data.loader import bot
from tgbot.utils.models import async_main, engine
from tgbot.webapp.app import app

log = logging.getLogger("autoshop.runtime")


def validate_environment():
    if not BotConfig.ADMINS:
        raise RuntimeError("Set BOT_ADMINS to comma-separated Telegram user IDs")
    url = urlsplit(BotConfig.WEBAPP_URL)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise RuntimeError("Set WEBAPP_URL to an HTTPS URL or generate a Railway public domain")
    if os.environ.get("RAILWAY_ENVIRONMENT_ID") and not BotConfig.DATABASE_URL:
        raise RuntimeError("Set DATABASE_URL to the Railway PostgreSQL reference")


async def polling_worker():
    # Session lock prevents duplicate getUpdates consumers during rolling deploys.
    async with engine.connect() as connection:
        lock_id = int(BotConfig.BOT_TOKEN.split(":", 1)[0])
        while not await connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_id}):
            log.info("Previous deployment still owns polling; waiting")
            await asyncio.sleep(2)
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
                text="Mini App", web_app=WebAppInfo(url=BotConfig.WEBAPP_URL),
            ))
            log.info("Mini App menu configured; starting polling")
            await run_bot(initialize_database=False, handle_signals=False)
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_id})


async def supervise(server, worker):
    web_task = asyncio.create_task(server.serve(), name="miniapp")
    bot_task = asyncio.create_task(worker(), name="telegram")
    try:
        done, _ = await asyncio.wait((web_task, bot_task), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
        if bot_task in done:
            raise RuntimeError("Telegram polling exited unexpectedly")
    finally:
        server.should_exit = True
        bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)
        try:
            await asyncio.wait_for(web_task, timeout=15)
        except asyncio.TimeoutError:
            log.error("Mini App shutdown exceeded 15 seconds")


async def main():
    validate_environment()
    try:
        await async_main()
        server = uvicorn.Server(uvicorn.Config(
            app, host=BotConfig.WEBAPP_HOST, port=BotConfig.WEBAPP_PORT,
            workers=1, access_log=False, timeout_graceful_shutdown=10,
        ))
        await supervise(server, polling_worker)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
