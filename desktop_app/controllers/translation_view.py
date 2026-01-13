from __future__ import annotations

from collections.abc import Callable

from desktop_app.application.view_state import (
    TranslationPresenter,
    TranslationViewState,
)
from desktop_app.notifications import Notification
from desktop_app.ui.translation_window import TranslationWindow
from desktop_app import gtk_types
from translate_logic.models import TranslationResult


class TranslationViewCoordinator:
    def __init__(
        self,
        *,
        app: gtk_types.Gtk.Application,
        on_close: Callable[[], None],
        on_copy_all: Callable[[], None],
        on_add: Callable[[], None],
    ) -> None:
        self._app = app
        self._on_close = on_close
        self._on_copy_all = on_copy_all
        self._on_add = on_add
        self._translation_view: TranslationWindow | None = None
        self._presenter = TranslationPresenter()
        self._view_state = self._presenter.state

    @property
    def state(self) -> TranslationViewState:
        return self._view_state

    def ensure_window(self) -> None:
        if self._translation_view is not None:
            return
        self._translation_view = TranslationWindow(
            app=self._app,
            on_close=self._on_close,
            on_copy_all=self._on_copy_all,
            on_add=self._on_add,
        )
        self._translation_view.apply_state(self._view_state)

    def hide(self) -> None:
        if self._translation_view is None:
            return
        self._translation_view.hide()

    def is_visible(self) -> bool:
        if self._translation_view is None:
            return False
        return self._translation_view.is_visible()

    def apply_state(self, state: TranslationViewState) -> None:
        self._view_state = state
        if self._translation_view is not None:
            self._translation_view.apply_state(state)

    def begin(self, original: str) -> None:
        self.apply_state(self._presenter.begin(original))

    def reset_original(self, original: str) -> None:
        self.apply_state(self._presenter.reset_original(original))

    def apply_partial(self, result: TranslationResult) -> None:
        self.apply_state(self._presenter.apply_partial(result))

    def apply_final(self, result: TranslationResult) -> None:
        self.apply_state(self._presenter.apply_final(result))

    def mark_error(self) -> None:
        self.apply_state(self._presenter.mark_error())

    def set_anki_available(self, available: bool) -> None:
        self.apply_state(self._presenter.set_anki_available(available))

    def notify(self, notification: Notification) -> None:
        if self._translation_view is None:
            return
        self._translation_view.show_banner(notification)

    def present(self, *, should_present: bool) -> bool:
        self.ensure_window()
        if self._translation_view is None:
            return False
        if not should_present:
            return False
        self._translation_view.present()
        return True

    def window(self) -> gtk_types.Gtk.ApplicationWindow | None:
        if self._translation_view is None:
            return None
        return self._translation_view.window
