from __future__ import annotations

import argparse
import json

from translator.engine import translate
from translator.models import TranslationResult


def _result_to_dict(result: TranslationResult) -> dict[str, object]:
    examples: list[dict[str, object]] = []
    for example in result.examples:
        examples.append({"en": example.en, "ru": example.ru})
    return {
        "source_text": result.source_text,
        "normalized_text": result.normalized_text,
        "translation_ru": result.translation_ru,
        "ipa_uk": result.ipa_uk,
        "audio_uk_url": result.audio_uk_url,
        "examples": examples,
        "provider_used": result.provider_used.value,
        "errors": result.errors,
    }


def _print_summary(result: TranslationResult) -> None:
    print(f"source_text: {result.source_text}")
    print(f"normalized_text: {result.normalized_text}")
    print(f"translation_ru: {result.translation_ru}")
    print(f"ipa_uk: {result.ipa_uk}")
    print(f"audio_uk_url: {result.audio_uk_url}")
    if result.examples:
        first_example = result.examples[0]
        print(f"example_en: {first_example.en}")
        print(f"example_ru: {first_example.ru}")
    print(f"provider_used: {result.provider_used.value}")
    if result.errors:
        print(f"errors: {', '.join(result.errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate text with Cambridge first.")
    parser.add_argument("text", nargs="+", help="Text to translate")
    args = parser.parse_args()
    text = " ".join(args.text)
    result = translate(text)
    _print_summary(result)
    print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
