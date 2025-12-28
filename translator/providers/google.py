from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from urllib.parse import quote_plus

from translator.http import FetchError, Fetcher
from translator.text import normalize_whitespace

GOOGLE_TRANSLATE_BASE_URL = "https://translate.googleapis.com/translate_a/single"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GoogleResult:
    translation_ru: str | None
    errors: list[str]


def build_google_url(text: str, source_lang: str, target_lang: str) -> str:
    encoded = quote_plus(text)
    params = f"client=gtx&dj=1&sl={source_lang}&tl={target_lang}&dt=t&q={encoded}"
    return f"{GOOGLE_TRANSLATE_BASE_URL}?{params}"


def translate_google(
    text: str, source_lang: str, target_lang: str, fetcher: Fetcher
) -> GoogleResult:
    errors: list[str] = []
    if not text:
        return GoogleResult(translation_ru=None, errors=["Empty input"])
    url = build_google_url(text, source_lang, target_lang)
    try:
        payload = fetcher(url)
    except FetchError as exc:
        errors.append(str(exc))
        return GoogleResult(translation_ru=None, errors=errors)
    try:
        translation = _parse_google_response(payload)
    except Exception as exc:
        logger.warning("Google parse failed: %s", exc)
        errors.append("Google parse failed")
        return GoogleResult(translation_ru=None, errors=errors)
    if translation is None:
        errors.append("Google missing translation")
    return GoogleResult(translation_ru=translation, errors=errors)


def _parse_google_response(payload: str) -> str | None:
    raw_data: object = json.loads(payload)
    if not isinstance(raw_data, dict):
        return None
    sentences_obj: object = raw_data.get("sentences")
    if not isinstance(sentences_obj, list):
        return None
    translations: list[str] = []
    for item in sentences_obj:
        item_obj: object = item
        if not isinstance(item_obj, dict):
            continue
        trans_value: object = item_obj.get("trans")
        if isinstance(trans_value, str):
            translations.append(trans_value)
    combined = normalize_whitespace("".join(translations))
    return combined or None
