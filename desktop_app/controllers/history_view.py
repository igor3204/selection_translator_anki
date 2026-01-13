from __future__ import annotations

from collections.abc import Callable
from typing import Iterable

import importlib

from desktop_app.application.history import HistoryItem
from desktop_app.ui import HistoryWindow
from desktop_app import gtk_types

gi = importlib.import_module("gi")
require_version = getattr(gi, "require_version", None)
if callable(require_version):
    require_version("GLib", "2.0")
GLib = importlib.import_module("gi.repository.GLib")


class HistoryViewCoordinator:
    def __init__(
        self,
        *,
        app: gtk_types.Gtk.Application,
        history_provider: Callable[[], Iterable[HistoryItem]],
        on_settings: Callable[[], None],
        on_select: Callable[[HistoryItem], None],
        on_present_window: Callable[[gtk_types.Gtk.ApplicationWindow], None],
    ) -> None:
        self._app = app
        self._history_provider = history_provider
        self._on_settings = on_settings
        self._on_select = on_select
        self._on_present_window = on_present_window
        self._history_view: HistoryWindow | None = None
        self._history_open = False
        self._history_pending = False

    @property
    def is_open(self) -> bool:
        return self._history_open

    def show(self) -> None:
        if self._history_pending:
            return
        self._history_pending = True
        GLib.idle_add(self._open_history_window)

    def refresh(self) -> None:
        if self._history_view is None:
            return
        self._history_view.refresh(self._history_provider())

    def close(self) -> None:
        self._history_open = False
        if self._history_view is not None:
            self._history_view.hide()

    def _open_history_window(self) -> bool:
        self._history_pending = False
        self._ensure_view()
        self.refresh()
        if self._history_view is not None:
            self._history_open = True
            self._history_view.present()
            self._on_present_window(self._history_view.window)
        return False

    def _ensure_view(self) -> None:
        if self._history_view is not None:
            return
        self._history_view = HistoryWindow(
            app=self._app,
            on_close=self.close,
            on_settings=self._on_settings,
            on_select=self._on_select,
        )
