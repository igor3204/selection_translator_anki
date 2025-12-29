from __future__ import annotations

from translator.engine import translate, translate_async
from translator.models import Example, TranslationResult

__all__ = ["translate", "translate_async", "TranslationResult", "Example"]
