"""Greeting logic behind SayHello (gRPC) and POST /v1/greetings (REST)."""

from __future__ import annotations

from core.errors import InvalidArgument

MAX_NAME_LENGTH = 64
MAX_SIMULATED_DELAY_MS = 5000

GREETINGS: dict[str, str] = {
    "en": "Hello, {name}!",
    "es": "¡Hola, {name}!",
    "fr": "Bonjour, {name} !",
    "de": "Hallo, {name}!",
    "hi": "नमस्ते, {name}!",
}
DEFAULT_LANGUAGE = "en"


def normalize_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise InvalidArgument("name must not be empty")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise InvalidArgument(f"name must be at most {MAX_NAME_LENGTH} characters")
    if any(not ch.isprintable() for ch in cleaned):
        raise InvalidArgument("name must not contain control characters")
    return cleaned


def validate_delay_ms(delay_ms: int) -> int:
    if not 0 <= delay_ms <= MAX_SIMULATED_DELAY_MS:
        raise InvalidArgument(f"simulated_delay_ms must be between 0 and {MAX_SIMULATED_DELAY_MS}")
    return delay_ms


def greet(name: str, language: str = "") -> str:
    """Return the greeting for `name` in `language` (empty means English)."""
    cleaned = normalize_name(name)
    code = (language or DEFAULT_LANGUAGE).lower()
    template = GREETINGS.get(code)
    if template is None:
        supported = ", ".join(sorted(GREETINGS))
        raise InvalidArgument(f"unsupported language {language!r}; use one of: {supported}")
    return template.format(name=cleaned)
