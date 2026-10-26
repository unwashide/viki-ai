# main.py
import asyncio
import logging
import memory
import scheduler

from aiogram import Bot, Dispatcher

from config import TG_TOKEN, TIMERS_ENABLED
from handlers import router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(TG_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # выкидываем сообщения, накопившиеся пока бот был выключен,
    # иначе ваша ии после рестарта начнёт отвечать на вчерашний чат
    await bot.delete_webhook(drop_pending_updates=True)
    await memory.init()
    timers = asyncio.create_task(scheduler.run(bot)) if TIMERS_ENABLED else None
    try:
        await dp.start_polling(bot)
    finally:
        if timers:
            timers.cancel()
        await memory.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())