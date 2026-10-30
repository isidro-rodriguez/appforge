from __future__ import annotations

import os
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from rich.console import Console, Group
from rich.text import Text
from textual import on
from textual.app import ComposeResult, RenderResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    ModalScreen,
    ProgressBar,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from appforge import __version__
from appforge.config import Config
from appforge.engine import Engine, EngineError, invoking_user, resolve_values
from appforge.entry import BOOL_VALUES, Entry, Param, Step, load_catalog
from appforge.runlog import RunLog, step_tag
from appforge.theme import (
    ANVIL_DARK,
    BACKGROUND,
    STYLES,
    SUCCESS,
    TEXTUAL_THEME,
    THEME_NAME,
)


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class AppForgeApp(Screen):
    """Pantalla principal con catálogo, detalle y ejecución."""

    CSS = """
    Screen { background: $background; color: $text; }
    #apps { width: 40%; }
    #details { width: 60%; }
    """

    BINDINGS = [
        Binding("space", "toggle_mark", "Marcar"),
        Binding("i", "apply", "Instalar"),
        Binding("u", "remove", "Desinstalar"),
        Binding("d", "dry_run", "Dry-run"),
        Binding("v", "show_details", "Detalle"),
        Binding("slash", "focus_search", "Buscar"),
        Binding("escape", "leave_search", "Cerrar"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.catalog = load_catalog(config.entries_dirs)
        self.entries = self.catalog.entries
        self.states: dict[str, bool] = {}
        self.checked: set[str] = set()
        self.marked: set[str] = set()
        self.category = "Todas"
        self.search_text = ""
        self.focused: Any | None = None
        self.screen: Screen | None = None
        self.result: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Static("AppForge", id="title")
        yield Input(placeholder="Buscar…", id="search")
        yield ListView(*[AppRow(e) for e in self.entries], id="apps")
        yield Static("", id="details")

    def on_mount(self) -> None:
        self._refresh_states()
        self.query_one("#search", Input).visible = False
        self.query_one("#search", Input).blur()
        self.query_one("#apps", ListView).focus()

    def _refresh_states(self) -> None:
        engine = Engine(self.config, lambda *_: None)
        for entry in self.entries:
            self.states[entry.id] = engine.is_applied(entry)
            if engine.is_applied(entry):
                self.checked.add(entry.id)

    def _toggle_mark(self) -> None:
        if not self.entries:
            return
        current = self.current_entry()
        if current is None:
            return
        if current.id in self.marked:
            self.marked.remove(current.id)
        else:
            self.marked.add(current.id)
        self._repaint()

    def current_entry(self) -> Entry | None:
        list_view = self.query_one("#apps", ListView)
        if list_view.index is None:
            return None
        try:
            item = list_view.children[list_view.index]
        except Exception:
            return None
        if isinstance(item, AppRow):
            return item.entry
        return None

    def _repaint(self) -> None:
        self.refresh()

    def action_toggle_mark(self) -> None:
        self._toggle_mark()

    def action_apply(self) -> None:
        self._run_flow("apply", dry_run=False)

    def action_remove(self) -> None:
        self._run_flow("remove", dry_run=False)

    def action_dry_run(self) -> None:
        self._run_flow("apply", dry_run=True)

    def _run_flow(self, action: str, dry_run: bool) -> None:
        entries = (
            [e for e in self.entries if e.id in self.marked] or [self.current_entry()]
            if self.current_entry()
            else []
        )
        if not entries:
            return
        self.push_screen(ConfirmScreen(entries, action, dry_run))

    def action_focus_search(self) -> None:
        search = self.query_one("#search", Input)
        search.visible = True
        search.focus()

    def action_leave_search(self) -> None:
        search = self.query_one("#search", Input)
        if self.focused is search:
            self.query_one("#apps", ListView).focus()
            search.visible = False

    def action_show_details(self) -> None:
        entry = self.current_entry()
        if entry is None:
            return
        self.push_screen(
            DetailScreen(entry, self.states.get(entry.id), entry.id in self.checked)
        )


class AppRow(ListItem):
    def __init__(self, entry: Entry) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        yield Static(self.entry.name, classes="name")
        yield Static(self.entry.id, classes="tag")


class CategoryRow(ListItem):
    def __init__(self, category: str, count: int) -> None:
        super().__init__()
        self.category = category
        self.count = count

    def compose(self) -> ComposeResult:
        yield Static(self.category, classes="name")
        yield Static(str(self.count), classes="count")


class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen { align: center middle; }
    #dialog { width: 60%; height: auto; }
    """

    def __init__(self, entries: list[Entry], action: str, dry_run: bool) -> None:
        super().__init__()
        self.entries = entries
        self.action = action
        self.dry_run = dry_run

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(
                f"¿Quieres {self.action} {len(self.entries)} entradas?", classes="title"
            )
            yield Button("Sí", id="yes", variant="primary")
            yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class DetailScreen(ModalScreen[None]):
    CSS = """
    DetailScreen { align: center middle; }
    """

    def __init__(self, entry: Entry, state: bool | None, checked: bool) -> None:
        super().__init__()
        self.entry = entry
        self.state = state
        self.checked = checked

    def compose(self) -> ComposeResult:
        yield Static(entry_markdown(self.entry, self.checked), id="detail-content")


class ParamsScreen(ModalScreen[dict[str, Any] | None]):
    CSS = """
    ParamsScreen { align: center middle; }
    #dialog { width: 70%; height: auto; }
    """

    BINDINGS = [
        Binding("tab", "focus_next_field", "Siguiente"),
        Binding("shift+tab", "focus_prev_field", "Anterior"),
        Binding("escape", "cancel", "Cancelar"),
    ]

    def __init__(self, entry: Entry, values: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.entry = entry
        self.values = values or {}
        self._field_widgets: list[Any] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"Parámetros: {self.entry.name}", classes="title")
            for param in self.entry.params:
                yield self._field_for_param(param)
            with Horizontal(classes="buttons"):
                yield Button("Aceptar", id="ok", variant="primary")
                yield Button("Cancelar", id="cancel")

    def _field_for_param(self, param: Param) -> Any:
        if param.type == "bool":
            field = Checkbox(
                param.prompt, value=self.values.get(param.name, BOOL_VALUES[0])
            )
            field.id = f"p_{param.name}"
            self._field_widgets.append(field)
            return field
        if param.choices:
            options = [(value, value) for value in param.choices]
            select = Select(
                options,
                value=self.values.get(param.name, param.default or options[0][0]),
                allow_blank=False,
            )
            select.id = f"p_{param.name}"
            self._field_widgets.append(select)
            return select
        field = Input(
            value=str(self.values.get(param.name, param.default or "")),
            placeholder=param.prompt,
        )
        field.id = f"p_{param.name}"
        self._field_widgets.append(field)
        return field

    def _focusable_widgets(self) -> list[Any]:
        widgets: list[Any] = []
        for widget in self._field_widgets:
            if hasattr(widget, "focus"):
                widgets.append(widget)
        return widgets

    def _move_focus(self, step: int) -> None:
        widgets = self._focusable_widgets()
        if not widgets:
            return
        current = self.focused
        if current is None:
            widgets[0].focus()
            return
        try:
            index = widgets.index(current)
        except ValueError:
            widgets[0].focus()
            return
        widgets[(index + step) % len(widgets)].focus()

    def action_focus_next_field(self) -> None:
        self._move_focus(1)

    def action_focus_prev_field(self) -> None:
        self._move_focus(-1)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            values: dict[str, Any] = {}
            for param in self.entry.params:
                field = self.query_one(f"#p_{param.name}")
                if isinstance(field, Checkbox):
                    values[param.name] = field.value
                elif isinstance(field, Select):
                    values[param.name] = field.value
                else:
                    values[param.name] = field.value
            self.dismiss(values)
        elif event.button.id == "cancel":
            self.dismiss(None)


class ProgressScreen(ModalScreen[None]):
    CSS = """
    ProgressScreen { align: center middle; }
    """

    def __init__(
        self, config: Config, entries: list[Entry], action: str, dry_run: bool
    ) -> None:
        super().__init__()
        self.config = config
        self.entries = entries
        self.action = action
        self.dry_run = dry_run
        self.running = True
        self.done: set[str] = set()

    def compose(self) -> ComposeResult:
        yield ProgressBar(total=1, show_eta=True, id="progress")
        yield RichLog(id="log")

    def on_mount(self) -> None:
        self.run()

    def run(self) -> None:
        engine = Engine(self.config, self.log)
        for entry in self.entries:
            try:
                result = engine.apply(entry, {}, dry_run=self.dry_run)
            except EngineError as exc:
                self.log(f"error: {exc}")
                continue
            if result:
                self.done.add(entry.id)
        self.running = False
        self.query_one("#progress", ProgressBar).update(total=1, progress=1)

    def log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(Text(message))


def entry_markdown(entry: Entry, checked: bool) -> str:
    """Genera el texto Markdown de detalle para la entrada."""
    lines = [f"# {entry.name}"]
    if entry.description:
        lines.append(entry.description)
    if entry.details:
        lines.append(entry.details)
    if entry.params:
        lines.append("\n## Parámetros")
        for param in entry.params:
            lines.append(f"- `{param.name}`: {param.prompt}")
    if checked:
        lines.append("\n✅ Instalado")
    else:
        lines.append("\n⚠ No instalada")
    return "\n".join(lines)


__all__ = [
    "AppForgeApp",
    "AppRow",
    "CategoryRow",
    "ConfirmScreen",
    "DetailScreen",
    "ParamsScreen",
    "ProgressScreen",
    "entry_markdown",
]
