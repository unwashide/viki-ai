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
    await _db.execute(
        """create table if not exists timers (
            id integer primary key autoincrement,
            chat_id integer not null,
            author text not null,
            note text not null,
            due_ts real not null,
            done integer not null default 0
        )"""
    )
    await _db.execute("create index if not exists idx_timers_due on timers(done, due_ts)")
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
    await _db.execute("delete from timers where chat_id = ?", (chat_id,))
    await _db.commit()


async def set_timer(chat_id: int, author: str, note: str, due_ts: float):
    """один активный таймер на человека в чате: новый заменяет старый"""
    await _db.execute(
        "delete from timers where chat_id = ? and author = ? and done = 0",
        (chat_id, author),
    )
    await _db.execute(
        "insert into timers (chat_id, author, note, due_ts) values (?, ?, ?, ?)",
        (chat_id, author, note, due_ts),
    )
    await _db.commit()


async def due_timers(now: float) -> list[tuple[int, int, str, str, float]]:
    """таймеры, у которых время вышло: (id, chat_id, author, note, due_ts)"""
    async with _db.execute(
        "select id, chat_id, author, note, due_ts from timers "
        "where done = 0 and due_ts <= ? order by due_ts",
        (now,),
    ) as cur:
        return await cur.fetchall()


async def finish_timer(timer_id: int):
    await _db.execute("update timers set done = 1 where id = ?", (timer_id,))
    await _db.commit()