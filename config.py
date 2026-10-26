# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TG_TOKEN = os.environ["TG_TOKEN"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
ONLY_OWNER = False   # функция что бы отвечать только на сообщения владельца, было сделано для тестов, но можно включить если надо)

LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-flash"
LLM_TIMEOUT = 30        # секунд на один запрос
LLM_MAX_TOKENS = 300    # потолок длины ответа вашей ии
HISTORY_SIZE = 20       # сколько последних сообщений чата помним
RANDOM_CHANCE = 1       # шанс вклиниться самой в группе (реальный шанс зависит от того, скипнет ли ии на моменте should_reply)
COOLDOWN = 0.1          # секунд между "самовольными" репликами
DB_PATH = "name_ai.db"       # если надо поменять название базы данных, то тут можно поменять, вместо "name_ai" укажи имя твоей ии, если бд уже создавалась то просто удали файл с бд и запусти уже с ее именем
OWNER_ID = int(os.environ["OWNER_ID"])
ALLOWED_CHATS = {int(x) for x in os.environ["ALLOWED_CHATS"].split(",")}
MAX_INPUT_LEN = 500

# таймеры: ии сама решает, когда поставить (человек сказал "напишу позже")
TIMERS_ENABLED = True
TIMER_POLL = 20             # как часто (сек) проверять, не пора ли писать
TIMER_MIN_MINUTES = 1       # минимум, на сколько можно поставить таймер
TIMER_MAX_MINUTES = 1440    # максимум (сутки), всё что больше обрезается
TIMER_MAX_LATE = 3 * 3600   # если бот был выключен и таймер просрочен дольше этого, молча выкидываем