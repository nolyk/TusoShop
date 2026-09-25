from tgbot.webapp.app import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    from tgbot.data.config import BotConfig

    uvicorn.run("web_main:app", host=BotConfig.WEBAPP_HOST, port=BotConfig.WEBAPP_PORT)
