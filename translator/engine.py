from __future__ import annotations

from translator.http import Fetcher, fetch_text
from translator.models import Provider, TranslationResult
from translator.providers.cambridge import CambridgeResult, translate_cambridge
from translator.providers.google import GoogleResult, translate_google
from translator.text import normalize_text


def translate(
    text: str, source_lang: str = "en", target_lang: str = "ru"
) -> TranslationResult:
    return _translate_with_fetcher(text, source_lang, target_lang, fetch_text)


def _translate_with_fetcher(
    text: str, source_lang: str, target_lang: str, fetcher: Fetcher
) -> TranslationResult:
    source_text = text
    normalized_text = normalize_text(text)
    if not normalized_text:
        return TranslationResult(
            source_text=source_text,
            normalized_text=normalized_text,
            translation_ru=None,
            ipa_uk=None,
            audio_uk_url=None,
            examples=[],
            provider_used=Provider.CAMBRIDGE,
            errors=["Empty input"],
        )

    cambridge_result = _try_cambridge(normalized_text, fetcher)
    if cambridge_result.found:
        return TranslationResult(
            source_text=source_text,
            normalized_text=normalized_text,
            translation_ru=cambridge_result.translation_ru,
            ipa_uk=cambridge_result.ipa_uk,
            audio_uk_url=cambridge_result.audio_uk_url,
            examples=cambridge_result.examples,
            provider_used=Provider.CAMBRIDGE,
            errors=cambridge_result.errors,
        )

    google_result = _try_google(normalized_text, source_lang, target_lang, fetcher)
    return TranslationResult(
        source_text=source_text,
        normalized_text=normalized_text,
        translation_ru=google_result.translation_ru,
        ipa_uk=None,
        audio_uk_url=None,
        examples=[],
        provider_used=Provider.GOOGLE,
        errors=cambridge_result.errors + google_result.errors,
    )


def _try_cambridge(text: str, fetcher: Fetcher) -> CambridgeResult:
    return translate_cambridge(text, fetcher)


def _try_google(
    text: str, source_lang: str, target_lang: str, fetcher: Fetcher
) -> GoogleResult:
    return translate_google(text, source_lang, target_lang, fetcher)
