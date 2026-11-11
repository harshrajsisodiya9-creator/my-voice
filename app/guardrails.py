import json
import re
import time
from collections import defaultdict

from app.config import (
    MAX_HISTORY_CONTENT_LENGTH,
    MAX_HISTORY_TURNS,
    MAX_REPLY_LENGTH,
    MAX_TEXT_LENGTH,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SEC,
)

# Per-IP rate limiting — best-effort only.
# On serverless platforms each instance has its own memory, so a user may
# land on a fresh instance and bypass the limit. Acceptable for this use case.
_request_log: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(ip: str) -> bool:
    """Return True if the request should be allowed."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    log = _request_log[ip]
    _request_log[ip] = [t for t in log if t > window_start]
    if len(_request_log[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    _request_log[ip].append(now)
    return True


def cap_input_text(text: str) -> str:
    """Truncate user text input to the configured limit."""
    return text[:MAX_TEXT_LENGTH]


def sanitize_history(raw: str | list | None) -> list[dict]:
    """
    Validate and sanitize client-sent conversation history.
    - Parse JSON string if needed; treat invalid JSON as empty
    - Keep only messages with role "user" or "assistant" and string content
    - Truncate each message's content to MAX_HISTORY_CONTENT_LENGTH
    - Trim to the last MAX_HISTORY_TURNS messages
    """
    if raw is None:
        return []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    if not isinstance(raw, list):
        return []

    clean = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str):
            continue
        clean.append({
            "role": role,
            "content": content[:MAX_HISTORY_CONTENT_LENGTH],
        })

    return clean[-MAX_HISTORY_TURNS:]


def clean_reply(text: str) -> str:
    """Strip markdown artifacts and emojis so TTS reads cleanly."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if len(text) > MAX_REPLY_LENGTH:
        truncated = text[:MAX_REPLY_LENGTH]
        last_period = truncated.rfind(".")
        if last_period > MAX_REPLY_LENGTH // 2:
            text = truncated[: last_period + 1]
        else:
            text = truncated.rstrip() + "..."
    return text
