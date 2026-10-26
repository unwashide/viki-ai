import asyncio
import logging
import time

import brain
import memory
from config import TIMER_MAX_LATE, TIMER_POLL
from handlers import human_delay

log = logging.getLogger(__name__)


async def fire(bot, timer_id: int, chat_id: int, author: str, note: str, due_ts: float):
    # сначала закрываем таймер, чтобы он не сработал дважды, даже если дальше что-то упадёт
    await memory.finish_timer(timer_id)

    late = time.time() - due_ts
    if late > TIMER_MAX_LATE:
        log.info("таймер %s просрочен на %.0f мин, пропускаю", timer_id, late / 60)
        return

    t0 = time.monotonic()
    parts = await brain.generate_nudge(chat_id, author, note)
    if not parts:
        return
    for i, part in enumerate(parts):
        spent = time.monotonic() - t0 if i == 0 else 0
        await human_delay(bot, chat_id, part, spent)
        await bot.send_message(chat_id, part)


async def run(bot):
    """фоновый цикл: раз в TIMER_POLL секунд смотрит, не истёк ли чей-то таймер"""
    while True:
        try:
            for timer in await memory.due_timers(time.time()):
                try:
                    await fire(bot, *timer)
                except Exception:
                    log.exception("упал таймер %s", timer[0])
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("упал цикл таймеров")
        await asyncio.sleep(TIMER_POLL)
