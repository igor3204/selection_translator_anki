from __future__ import annotations

from urllib.parse import quote


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def to_cambridge_slug(value: str) -> str:
    normalized = normalize_text(value).lower()
    slug = normalized.replace(" ", "-")
    return quote(slug)
