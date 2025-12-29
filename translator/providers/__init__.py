from __future__ import annotations

from translator.providers.cambridge import CambridgeResult, translate_cambridge
from translator.providers.dictionary_api import (
    DictionaryApiResult,
    translate_dictionary_api,
)
from translator.providers.google import GoogleResult, translate_google
from translator.providers.tatoeba import TatoebaResult, translate_tatoeba

__all__ = [
    "translate_cambridge",
    "translate_dictionary_api",
    "translate_google",
    "translate_tatoeba",
    "CambridgeResult",
    "DictionaryApiResult",
    "GoogleResult",
    "TatoebaResult",
]
