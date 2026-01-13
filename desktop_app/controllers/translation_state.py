from __future__ import annotations

from dataclasses import dataclass, field

from translate_logic.models import TranslationResult, TranslationStatus


@dataclass(slots=True)
class TranslationMemory:
    text: str = ""
    result: TranslationResult | None = None

    def reset(self) -> None:
        self.text = ""
        self.result = None

    def update(self, text: str, result: TranslationResult | None) -> None:
        self.text = text
        self.result = result

    def can_reuse(self, text: str, *, loading: bool) -> bool:
        if loading or self.result is None:
            return False
        return (
            self.result.status is TranslationStatus.SUCCESS
            and self.text.strip() == text
        )


@dataclass(slots=True)
class RequestTracker:
    current_id: int = 0
    presented_id: int | None = None

    def next_id(self) -> int:
        self.current_id += 1
        self.presented_id = None
        return self.current_id

    def is_active(self, request_id: int) -> bool:
        return request_id == self.current_id

    def should_present(self, is_visible: bool) -> bool:
        return not (self.presented_id == self.current_id and is_visible)

    def mark_presented(self) -> None:
        self.presented_id = self.current_id


@dataclass(slots=True)
class TranslationState:
    request: RequestTracker = field(default_factory=RequestTracker)
    memory: TranslationMemory = field(default_factory=TranslationMemory)
