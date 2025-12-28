from __future__ import annotations

from dataclasses import dataclass
import logging

from translator.html_parser import (
    HtmlNode,
    find_all,
    find_first,
    has_ancestor_with_class,
    parse_html,
)
from translator.http import FetchError, Fetcher
from translator.models import Example
from translator.text import normalize_whitespace, to_cambridge_slug

CAMBRIDGE_BASE_URL = "https://dictionary.cambridge.org"
CAMBRIDGE_ENGLISH_URL = f"{CAMBRIDGE_BASE_URL}/dictionary/english/"
CAMBRIDGE_ENGLISH_RUSSIAN_URL = f"{CAMBRIDGE_BASE_URL}/dictionary/english-russian/"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CambridgeUrls:
    english: str
    english_russian: str


@dataclass(frozen=True, slots=True)
class CambridgePageData:
    has_di_body: bool
    has_entry: bool
    ipa_uk: str | None
    audio_uk_url: str | None
    translations: list[str]
    examples: list[Example]


@dataclass(frozen=True, slots=True)
class CambridgeResult:
    found: bool
    translation_ru: str | None
    ipa_uk: str | None
    audio_uk_url: str | None
    examples: list[Example]
    errors: list[str]


def build_cambridge_urls(text: str) -> CambridgeUrls:
    slug = to_cambridge_slug(text)
    return CambridgeUrls(
        english=f"{CAMBRIDGE_ENGLISH_URL}{slug}",
        english_russian=f"{CAMBRIDGE_ENGLISH_RUSSIAN_URL}{slug}",
    )


def translate_cambridge(text: str, fetcher: Fetcher) -> CambridgeResult:
    urls = build_cambridge_urls(text)
    errors: list[str] = []
    try:
        english_html = fetcher(urls.english)
        russian_html = fetcher(urls.english_russian)
    except FetchError as exc:
        errors.append(str(exc))
        return CambridgeResult(
            found=False,
            translation_ru=None,
            ipa_uk=None,
            audio_uk_url=None,
            examples=[],
            errors=errors,
        )

    try:
        english_data = parse_cambridge_page(english_html)
        russian_data = parse_cambridge_page(russian_html)
    except Exception as exc:
        logger.warning("Cambridge parse failed: %s", exc)
        errors.append("Cambridge parse failed")
        return CambridgeResult(
            found=False,
            translation_ru=None,
            ipa_uk=None,
            audio_uk_url=None,
            examples=[],
            errors=errors,
        )

    translation_ru = russian_data.translations[0] if russian_data.translations else None
    ipa_uk = english_data.ipa_uk or russian_data.ipa_uk
    audio_uk_url = english_data.audio_uk_url or russian_data.audio_uk_url
    examples = russian_data.examples or english_data.examples

    core_found = (
        russian_data.has_di_body
        and russian_data.has_entry
        and translation_ru is not None
    )
    if not core_found:
        return CambridgeResult(
            found=False,
            translation_ru=None,
            ipa_uk=None,
            audio_uk_url=None,
            examples=[],
            errors=errors,
        )

    if ipa_uk is None:
        errors.append("Cambridge missing UK IPA")
    if audio_uk_url is None:
        errors.append("Cambridge missing UK audio")
    if not examples:
        errors.append("Cambridge missing examples")

    return CambridgeResult(
        found=True,
        translation_ru=translation_ru,
        ipa_uk=ipa_uk,
        audio_uk_url=audio_uk_url,
        examples=examples,
        errors=errors,
    )


def parse_cambridge_page(html: str) -> CambridgePageData:
    root = parse_html(html)
    has_di_body = find_first(root, _is_di_body) is not None
    has_entry = bool(find_all(root, _is_entry_block))
    ipa_uk = _extract_ipa_uk(root)
    audio_uk_url = _extract_audio_uk(root)
    translations = _extract_translations(root)
    examples = _extract_examples(root)
    return CambridgePageData(
        has_di_body=has_di_body,
        has_entry=has_entry,
        ipa_uk=ipa_uk,
        audio_uk_url=audio_uk_url,
        translations=translations,
        examples=examples,
    )


def _is_di_body(node: HtmlNode) -> bool:
    return node.tag == "div" and "di-body" in node.classes()


def _is_entry_block(node: HtmlNode) -> bool:
    classes = node.classes()
    if not classes:
        return False
    return (
        "entry-body__el" in classes
        or "pv-block" in classes
        or ("pr" in classes and "dictionary" in classes)
        or ("pr" in classes and "idiom-block" in classes)
    )


def _extract_ipa_uk(root: HtmlNode) -> str | None:
    nodes = find_all(
        root,
        lambda node: node.tag == "span"
        and {"pron", "dpron"}.issubset(node.classes())
        and has_ancestor_with_class(node, "uk"),
    )
    for node in nodes:
        text = normalize_whitespace(node.text_content())
        if text:
            return text
    return None


def _extract_audio_uk(root: HtmlNode) -> str | None:
    nodes = find_all(
        root,
        lambda node: node.tag == "source"
        and node.attrs.get("type") == "audio/mpeg"
        and has_ancestor_with_class(node, "uk"),
    )
    for node in nodes:
        src = node.attrs.get("src", "").strip()
        if src:
            if src.startswith("http://") or src.startswith("https://"):
                return src
            return f"{CAMBRIDGE_BASE_URL}{src}"
    return None


def _extract_translations(root: HtmlNode) -> list[str]:
    translations: list[str] = []
    nodes = find_all(
        root,
        lambda node: node.tag == "span" and "trans" in node.classes(),
    )
    for node in nodes:
        if has_ancestor_with_class(node, "examp") or has_ancestor_with_class(
            node, "dexamp"
        ):
            continue
        text = normalize_whitespace(node.text_content())
        if text and text not in translations:
            translations.append(text)
    return translations


def _extract_examples(root: HtmlNode) -> list[Example]:
    examples: list[Example] = []
    nodes = find_all(
        root,
        lambda node: node.tag == "div" and "examp" in node.classes(),
    )
    for node in nodes:
        en_text = _extract_example_text(node, "eg")
        if not en_text:
            en_text = normalize_whitespace(node.text_content())
        if not en_text:
            continue
        ru_text = _extract_example_text(node, "trans")
        examples.append(Example(en=en_text, ru=ru_text))
    return examples


def _extract_example_text(node: HtmlNode, class_name: str) -> str | None:
    matches = find_all(
        node, lambda target: target.tag == "span" and class_name in target.classes()
    )
    for match in matches:
        text = normalize_whitespace(match.text_content())
        if text:
            return text
    return None
