from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Example:
    en: str
    ru: str | None


@dataclass(frozen=True, slots=True)
class TranslationResult:
    translation_ru: str | None
    ipa_uk: str | None
    example_en: str | None
    example_ru: str | None


class TranslationLimit(Enum):
    PRIMARY = 3


class QueryLimit(Enum):
    MAX_CHARS = 200
    MAX_CAMBRIDGE_WORDS = 5
