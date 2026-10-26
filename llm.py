# llm.py
import logging

from openai import AsyncOpenAI, APIError, APITimeoutError

from config import (
    DEEPSEEK_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS,
)

log = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=DEEPSEEK_KEY,
    base_url=LLM_BASE_URL,
    timeout=LLM_TIMEOUT,
    max_retries=2,  # sdk сам ретраит сетевые ошибки и 429/5xx
)


async def complete(
    messages: list[dict],
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = 1.3,
) -> str | None:
    """возвращает текст ответа или None, если что-то сломалось.
    None = 'имя ии' просто промолчит, а не уронит бота."""
    try:
        r = await _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"thinking": {"type": "disabled"}},
            frequency_penalty=0.5,
            presence_penalty=0.3,
        )
    except APITimeoutError:
        log.warning("deepseek: таймаут")
        return None
    except APIError as e:
        log.warning("deepseek: ошибка api: %s", e)
        return None

    text = (r.choices[0].message.content or "").strip()

    # логируем кэш, чтобы видеть, работает ли экономия на префиксе
    u = r.usage
    hit = getattr(u, "prompt_cache_hit_tokens", None)
    miss = getattr(u, "prompt_cache_miss_tokens", None)
    log.info("tokens: in=%s out=%s cache_hit=%s cache_miss=%s",
             u.prompt_tokens, u.completion_tokens, hit, miss)

    return text or None