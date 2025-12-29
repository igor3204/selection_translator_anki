from __future__ import annotations

from urllib.parse import quote

from translator.models import QueryLimit


def normalize_text(value: str) -> str:
    collapsed = normalize_whitespace(value)
    if len(collapsed) > QueryLimit.MAX_CHARS.value:
        collapsed = collapsed[: QueryLimit.MAX_CHARS.value].rstrip()
    return collapsed


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def count_words(value: str) -> int:
    normalized = normalize_whitespace(value)
    if not normalized:
        return 0
    return len(normalized.split())


def to_cambridge_slug(value: str) -> str:
    normalized = normalize_text(value).lower()
    slug = normalized.replace(" ", "-")
    return quote(slug)
