from __future__ import annotations

import asyncio
from typing import Callable

import aiohttp

from translator.cache import LruTtlCache
from translator.http import AsyncFetcher, build_async_fetcher
from translator.models import Example, QueryLimit, TranslationResult
from translator.providers.cambridge import CambridgeResult, translate_cambridge
from translator.providers.dictionary_api import (
    DictionaryApiResult,
    translate_dictionary_api,
)
from translator.providers.google import translate_google
from translator.providers.tatoeba import TatoebaResult, translate_tatoeba
from translator.text import count_words, normalize_text
from translator.translation import (
    combine_translations,
    merge_translations,
    partition_translations,
    select_primary_translation,
)

DEFAULT_CACHE = LruTtlCache()


def translate(
    text: str, source_lang: str = "en", target_lang: str = "ru"
) -> TranslationResult:
    return asyncio.run(translate_async(text, source_lang, target_lang))


async def translate_async(
    text: str,
    source_lang: str = "en",
    target_lang: str = "ru",
    fetcher: AsyncFetcher | None = None,
    on_partial: Callable[[TranslationResult], None] | None = None,
) -> TranslationResult:
    if fetcher is not None:
        return await _translate_with_fetcher_async(
            text, source_lang, target_lang, fetcher, on_partial
        )
    async with aiohttp.ClientSession() as session:
        async_fetcher = build_async_fetcher(session, cache=DEFAULT_CACHE)
        return await _translate_with_fetcher_async(
            text, source_lang, target_lang, async_fetcher, on_partial
        )


async def _translate_with_fetcher_async(
    text: str,
    source_lang: str,
    target_lang: str,
    fetcher: AsyncFetcher,
    on_partial: Callable[[TranslationResult], None] | None = None,
) -> TranslationResult:
    normalized_text = normalize_text(text)
    if not normalized_text:
        return TranslationResult(
            translation_ru=None,
            ipa_uk=None,
            example_en=None,
            example_ru=None,
        )

    word_count = count_words(normalized_text)
    if word_count > QueryLimit.MAX_CAMBRIDGE_WORDS.value:
        cambridge_result = CambridgeResult(
            found=False,
            translations=[],
            ipa_uk=None,
            examples=[],
        )
        translation_ru, ipa_uk, example = await _translate_with_google_fallback_async(
            normalized_text,
            cambridge_result,
            source_lang,
            target_lang,
            fetcher,
            on_partial,
        )
        return TranslationResult(
            translation_ru=translation_ru,
            ipa_uk=ipa_uk,
            example_en=example.en if example else None,
            example_ru=example.ru if example else None,
        )

    cambridge_result = await translate_cambridge(normalized_text, fetcher)
    if cambridge_result.found:
        translation_ru = await _resolve_cambridge_translation_async(
            normalized_text,
            cambridge_result.translations,
            source_lang,
            target_lang,
            fetcher,
        )
        _emit_partial(on_partial, translation_ru)
        ipa_uk, example = await _supplement_pronunciation_and_examples_async(
            normalized_text,
            cambridge_result.ipa_uk,
            cambridge_result.examples,
            source_lang,
            target_lang,
            fetcher,
        )
        return TranslationResult(
            translation_ru=translation_ru,
            ipa_uk=ipa_uk,
            example_en=example.en if example else None,
            example_ru=example.ru if example else None,
        )

    translation_ru, ipa_uk, example = await _translate_with_google_fallback_async(
        normalized_text,
        cambridge_result,
        source_lang,
        target_lang,
        fetcher,
        on_partial,
    )
    return TranslationResult(
        translation_ru=translation_ru,
        ipa_uk=ipa_uk,
        example_en=example.en if example else None,
        example_ru=example.ru if example else None,
    )


async def _translate_with_google_fallback_async(
    text: str,
    cambridge_result: CambridgeResult,
    source_lang: str,
    target_lang: str,
    fetcher: AsyncFetcher,
    on_partial: Callable[[TranslationResult], None] | None = None,
) -> tuple[str | None, str | None, Example | None]:
    google_task = asyncio.create_task(
        translate_google(text, source_lang, target_lang, fetcher)
    )
    dictionary_task = asyncio.create_task(translate_dictionary_api(text, fetcher))
    tatoeba_task = asyncio.create_task(translate_tatoeba(text, fetcher))

    google_result = await google_task
    translation_ru = _resolve_google_translation(google_result.translations)
    _emit_partial(on_partial, translation_ru)

    dictionary_result, tatoeba_result = await asyncio.gather(
        dictionary_task, tatoeba_task
    )
    ipa_uk, example = await _supplement_pronunciation_and_examples_async(
        text,
        cambridge_result.ipa_uk,
        cambridge_result.examples,
        source_lang,
        target_lang,
        fetcher,
        dictionary_result,
        tatoeba_result,
    )
    return translation_ru, ipa_uk, example


async def _supplement_pronunciation_and_examples_async(
    text: str,
    ipa_uk: str | None,
    examples: list[Example],
    source_lang: str,
    target_lang: str,
    fetcher: AsyncFetcher,
    dictionary_result: DictionaryApiResult | None = None,
    tatoeba_result: TatoebaResult | None = None,
) -> tuple[str | None, Example | None]:
    available_examples = examples
    needs_dictionary = ipa_uk is None or not available_examples
    needs_tatoeba = _select_example_with_ru(available_examples) is None

    dictionary_task: asyncio.Task[DictionaryApiResult] | None = None
    tatoeba_task: asyncio.Task[TatoebaResult] | None = None
    if dictionary_result is None and needs_dictionary:
        dictionary_task = asyncio.create_task(translate_dictionary_api(text, fetcher))
    if tatoeba_result is None and needs_tatoeba:
        tatoeba_task = asyncio.create_task(translate_tatoeba(text, fetcher))

    if dictionary_task is not None:
        dictionary_result = await dictionary_task
    if dictionary_result is not None:
        if ipa_uk is None:
            ipa_uk = dictionary_result.ipa_uk
        if not available_examples:
            available_examples = dictionary_result.examples

    if tatoeba_task is not None:
        tatoeba_result = await tatoeba_task

    paired_example = _select_example_with_ru(available_examples)
    if paired_example is None and tatoeba_result is not None:
        paired_example = _select_example_with_ru(tatoeba_result.examples)

    fallback_example = _select_any_example(available_examples)
    final_example = paired_example or fallback_example
    if final_example is None:
        return ipa_uk, None

    if final_example.ru is None:
        translated = await translate_google(
            final_example.en, source_lang, target_lang, fetcher
        )
        translation_ru = select_primary_translation(translated.translations)
        if translation_ru:
            final_example = Example(en=final_example.en, ru=translation_ru)

    return ipa_uk, final_example


async def _resolve_cambridge_translation_async(
    text: str,
    translations: list[str],
    source_lang: str,
    target_lang: str,
    fetcher: AsyncFetcher,
) -> str | None:
    non_meta, meta = partition_translations(translations)
    if non_meta:
        return combine_translations(non_meta)
    google_result = await translate_google(text, source_lang, target_lang, fetcher)
    google_non_meta, google_meta = partition_translations(google_result.translations)
    if google_non_meta:
        return combine_translations(google_non_meta)
    merged = merge_translations(meta, google_meta)
    return combine_translations(merged)


def _emit_partial(
    on_partial: Callable[[TranslationResult], None] | None,
    translation_ru: str | None,
) -> None:
    if on_partial is None or translation_ru is None:
        return
    on_partial(
        TranslationResult(
            translation_ru=translation_ru,
            ipa_uk=None,
            example_en=None,
            example_ru=None,
        )
    )


def _select_example_with_ru(examples: list[Example]) -> Example | None:
    for example in examples:
        if example.ru:
            return example
    return None


def _select_any_example(examples: list[Example]) -> Example | None:
    if examples:
        return examples[0]
    return None


def _resolve_google_translation(translations: list[str]) -> str | None:
    non_meta, meta = partition_translations(translations)
    preferred = non_meta if non_meta else meta
    return combine_translations(preferred)
