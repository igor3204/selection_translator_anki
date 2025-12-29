from __future__ import annotations

import argparse
import asyncio

from translator.engine import translate_async
from translator.models import TranslationResult


def _format_summary(result: TranslationResult, empty_for_none: bool = False) -> str:
    def _format_value(value: str | None) -> str | None:
        if value is None and empty_for_none:
            return ""
        return value

    lines = [
        f"translation_ru: {_format_value(result.translation_ru)}",
        f"ipa_uk: {_format_value(result.ipa_uk)}",
        f"example_en: {_format_value(result.example_en)}",
        f"example_ru: {_format_value(result.example_ru)}",
    ]
    return "\n".join(lines)


def _print_summary(result: TranslationResult, empty_for_none: bool = False) -> None:
    print(_format_summary(result, empty_for_none))


async def _translate_with_partial(text: str) -> tuple[TranslationResult, bool]:
    partial_printed = False

    def on_partial(result: TranslationResult) -> None:
        nonlocal partial_printed
        if partial_printed:
            return
        partial_printed = True
        _print_summary(result, empty_for_none=True)

    result = await translate_async(text, on_partial=on_partial)
    return result, partial_printed


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate text with Cambridge first.")
    parser.add_argument("text", nargs="+", help="Text to translate")
    args = parser.parse_args()
    text = " ".join(args.text)
    result, _ = asyncio.run(_translate_with_partial(text))
    _print_summary(result)


if __name__ == "__main__":
    main()
