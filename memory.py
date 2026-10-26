import aiosqlite
from collections import defaultdict, deque

from config import DB_PATH, HISTORY_SIZE

_db: aiosqlite.Connection | None = None
_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))


async def init():
    """открыть базу и подгрузить последние N сообщений каждого чата"""
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    await _db.execute(
        """create table if not exists messages (
            id integer primary key autoincrement,
            chat_id integer not null,
            author text not null,
            text text not null,
            ts real not null default (strftime('%s','now'))
        )"""
    )
    await _db.execute("create index if not exists idx_chat on messages(chat_id, id)")
    await _db.commit()

    async with _db.execute(
        """select chat_id, author, text from (
               select *, row_number() over (partition by chat_id order by id desc) as rn
               from messages
           ) where rn <= ? order by chat_id, id""",
        (HISTORY_SIZE,),
    ) as cur:
        async for chat_id, author, text in cur:
            _history[chat_id].append(f"{author}: {text}")


def viki_replies(chat_id: int, n: int = 8) -> list[str]:
    own = [l[len("имя ии: "):] for l in _history[chat_id] if l.startswith("имя ии: ")]
    return own[-n:]


async def close():
    if _db:
        await _db.close()


async def add(chat_id: int, author: str, text: str):
    _history[chat_id].append(f"{author}: {text}")
    await _db.execute(
        "insert into messages (chat_id, author, text) values (?, ?, ?)",
        (chat_id, author, text),
    )
    await _db.commit()


def get_log(chat_id: int) -> str:
    return "\n".join(_history[chat_id])


async def clear(chat_id: int):
    _history[chat_id].clear()
    await _db.execute("delete from messages where chat_id = ?", (chat_id,))
    await _db.commit()