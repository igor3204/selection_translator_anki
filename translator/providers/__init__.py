from __future__ import annotations

from translator.providers.cambridge import CambridgeResult, translate_cambridge
from translator.providers.google import GoogleResult, translate_google

__all__ = ["translate_cambridge", "translate_google", "CambridgeResult", "GoogleResult"]
