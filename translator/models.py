from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Example:
    en: str
    ru: str | None


class Provider(Enum):
    CAMBRIDGE = "cambridge"
    GOOGLE = "google"


@dataclass(frozen=True, slots=True)
class TranslationResult:
    source_text: str
    normalized_text: str
    translation_ru: str | None
    ipa_uk: str | None
    audio_uk_url: str | None
    examples: list[Example]
    provider_used: Provider
    errors: list[str]
