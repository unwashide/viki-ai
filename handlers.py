import logging
import random
import time
import asyncio

from config import ALLOWED_CHATS, MAX_INPUT_LEN, OWNER_ID, ONLY_OWNER
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import brain
import memory
from config import ALLOWED_CHATS, MAX_INPUT_LEN, OWNER_ID

router = Router()
log = logging.getLogger(__name__)

def label(m: Message) -> str:
    u = m.from_user
    if not u:
        return "кто-то"
    if u.id == OWNER_ID:
        return f"{u.first_name} ['статус']"
    # чужим вычищаем скобки из имени, чтобы не подделали метку
    return u.first_name.replace("[", "").replace("]", "")

def allowed(m: Message) -> bool:
    if m.chat.type == "private":
        return m.from_user.id == OWNER_ID   # пока в личке только ты
    return m.chat.id in ALLOWED_CHATS

async def human_delay(bot, chat_id: int, text: str, already_spent: float):
    """имитация набора: ~0.05с на символ + рандом, минус время, которое уже ушло на llm"""
    total = min(1 + len(text) * 0.05 + random.uniform(0, 1.5), 8)
    left = total - already_spent
    while left > 0:
        await bot.send_chat_action(chat_id, "typing")  # индикатор живёт ~5с, обновляем
        step = min(4, left)
        await asyncio.sleep(step)
        left -= step


@router.message(Command("reset"))
async def on_reset(m: Message):
    if m.from_user.id != OWNER_ID:
        return
    await memory.clear(m.chat.id)
    await m.answer("всё, забыла")


@router.message(F.text)
async def on_text(m: Message):
    if not allowed(m):
        return
    try:
        me = await m.bot.me()
        author = label(m)
        text = m.text[:MAX_INPUT_LEN].replace("\n", " ").replace("['статус']", "")
        await memory.add(m.chat.id, author, text)

        if ONLY_OWNER and (not m.from_user or m.from_user.id != OWNER_ID):
            return

        if ONLY_OWNER:
            reply, allow_skip = True, False
        else:
            reply, allow_skip = brain.should_reply(
                chat_id=m.chat.id,
                is_private=m.chat.type == "private",
                text=text,
                mentioned=f"@{me.username}" in text,
                reply_to_bot=bool(
                    m.reply_to_message
                    and m.reply_to_message.from_user
                    and m.reply_to_message.from_user.id == me.id
                ),
            )
        if not reply:
            return

        target = f"{author}: {text}"
        t0 = time.monotonic()
        ...
        await m.bot.send_chat_action(m.chat.id, "typing")
        parts = await brain.generate(m.chat.id, allow_skip, target)
        if parts:
            for i, part in enumerate(parts):
                spent = time.monotonic() - t0 if i == 0 else 0
                await human_delay(m.bot, m.chat.id, part, spent)
                await m.answer(part)

    except Exception:
        log.exception("упало на сообщении в чате %s", m.chat.id)