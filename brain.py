import asyncio
import random
import time
import re
import logging
from collections import defaultdict, Counter
from pathlib import Path

import memory
from config import COOLDOWN, RANDOM_CHANCE

log = logging.getLogger(__name__)
from llm import complete

PERSONA = Path("prompts/persona.txt").read_text(encoding="utf-8")

_last_reply: dict[int, float] = defaultdict(float)
_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

MODES_OTHERS = [
    (35, "ответь по делу, спокойно, без подколок"),
    (10, "ответь очень коротко, 1-4 слова"),
    (45, "ответь острой подколкой, зацепившись за смысл или поступок из последнего сообщения. если зацепиться не за что, просто ответь коротко в тон"),
    (10, "ответь сухо, без тепла и без сарказма"),         # как ии будет отвечать для остальных, можно настроить под себя при желании
]

MODES_OWNER = [
    (45, "ответь по делу, спокойно и мягко, без колкостей"),
    (15, "ответь очень коротко, 1-4 слова"),
    (10, "ответь с лёгкой беззлобной подколкой, зацепившись за смысл или поступок из последнего сообщения. если зацепиться не за что, просто ответь коротко в тон"),
    (30, "ответь тепло, с заботой, но по-своему сдержанно, без сюсюканья"),      # как ии будет отвечать для owner, можно настроить под себя при желании
]


def pick_mode(is_owner: bool) -> str:
    table = MODES_OWNER if is_owner else MODES_OTHERS
    return random.choices(
        [m for _, m in table], weights=[w for w, _ in table]
    )[0]

MIN_GAP = 3                      # минимум чужих сообщений между её репликами
_since_reply: dict[int, int] = defaultdict(int)


def should_reply(chat_id: int, is_private: bool, text: str,
                 mentioned: bool, reply_to_bot: bool) -> tuple[bool, bool]:
    if is_private or mentioned or reply_to_bot or "имя ии" in text.lower():
        return True, False
    _since_reply[chat_id] += 1
    if (_since_reply[chat_id] >= MIN_GAP
            and time.time() - _last_reply[chat_id] > COOLDOWN
            and random.random() < RANDOM_CHANCE):
        return True, True       # второй False = SKIP запрещён, раз уж решили вклиниться
    return False, False


def repeated_phrases(replies: list[str], limit: int = 6) -> list[str]:
    c = Counter()
    for r in replies:
        words = re.findall(r"\w+", r.lower())
        grams = {" ".join(words[i:i + 2]) for i in range(len(words) - 1)
                 if max(len(words[i]), len(words[i + 1])) >= 5}
        c.update(grams)
    return [g for g, k in c.most_common() if k >= 2][:limit]


async def generate(chat_id: int, allow_skip: bool, target: str) -> str | None:
    async with _locks[chat_id]:   # не отвечаем дважды параллельно
        tail = ("\nесли добавить нечего или сообщение не к тебе, "
                "ответь ровно SKIP.") if allow_skip else ""
        banned = repeated_phrases(memory.viki_replies(chat_id))
        avoid = (f"\nты уже затёрла эти обороты, не используй их и похожие: "
                 f"{', '.join(banned)}.") if banned else ""
        is_owner = "['статус']" in target

        user_msg = (
            "последние сообщения чата:\n"
            f"{memory.get_log(chat_id)}\n\n"
            f"отвечай на последнее сообщение: {target}\n"
            "напиши следующую реплику 'имя ии' (только текст, без имени и двоеточия)."
            f"\nнастрой этой реплики: {pick_mode(is_owner)}."
            f"{avoid}{tail}"
        )
        text = await complete([
            {"role": "system", "content": PERSONA},   # статичный префикс -> кэш
            {"role": "user", "content": user_msg},
        ])
        if not text or text.strip().upper().startswith("SKIP"):
            log.info("skip в чате %s (llm решила промолчать)", chat_id)
            return None

        text = text.strip().lower()
        parts = [p.removeprefix("имя ии:").strip() for p in text.split("\n")]
        parts = [p for p in parts if p]
        if not parts:
            return None
        if len(parts) > 3:                       # лишнее клеим в третье, чтобы не терять
            parts = parts[:2] + [" ".join(parts[2:])]

        for p in parts:                          # в истории каждое сообщение отдельной строкой
            await memory.add(chat_id, "имя ии", p)
        _last_reply[chat_id] = time.time()
        _since_reply[chat_id] = 0
        return parts
