import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import (
    LLM_API_BASE,
    LLM_API_KEY,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    LLM_USE_JSON_RESPONSE_FORMAT,
    is_llm_configured,
)


class LLMClientError(RuntimeError):
    pass


def openai_compatible_chat_completion(messages: list[dict[str, str]]) -> str:
    if not is_llm_configured():
        raise LLMClientError("LLM_API_KEY and LLM_MODEL must be configured")

    payload: dict[str, object] = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_OUTPUT_TOKENS,
    }
    if LLM_USE_JSON_RESPONSE_FORMAT:
        payload["response_format"] = {"type": "json_object"}

    request = Request(
        f"{LLM_API_BASE}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ai-pr-review-assistant-local",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMClientError(f"LLM API returned {exc.code}: {detail[:360]}") from exc
    except URLError as exc:
        raise LLMClientError(f"LLM API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM API returned invalid JSON") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMClientError("LLM API returned an unexpected response shape") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMClientError("LLM API returned empty content")
    return content
