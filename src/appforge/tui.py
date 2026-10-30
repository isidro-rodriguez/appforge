"""TUI con Textual: catálogo de entradas, selección múltiple y progreso en vivo.

Pantallas:

- ``AppForgeApp`` (principal): buscador y categorías opcionales (``[ui]`` en
  ``config.toml``), lista con casillas, detalle y resumen de lo marcado.
- ``ProgressScreen``: progreso por entrada, barra global y registro en vivo.
"""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from rich.console import Group
from rich.markup import escape
from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    ProgressBar,
    RichLog,
    Static,
)

from appforge import __version__
from appforge.config import Config
from appforge.engine import Engine, EngineError, invoking_user, resolve_values
from appforge.entry import Entry, Step, load_catalog
from appforge.runlog import RunLog, step_tag
from appforge.theme import (
    ANVIL_DARK,
    BACKGROUND,
    STYLES,
    SUCCESS,
    TEXTUAL_THEME,
    THEME_NAME,
)

type State = bool | None

ALL = "Todas"
NO_CATEGORY = "Sin categoría"
_PREFIX = {"ok": "✔ ", "warn": "! ", "error": "✘ "}
# (acción, dry_run) -> (verbo, gerundio para la cabecera, resultado)
_VERBS = {
    ("apply", False): ("Instalar", "Instalando", "aplicada"),
    ("apply", True): ("Dry-run", "Dry-run", "dry-run correcto"),
    ("remove", False): ("Desinstalar", "Desinstalando", "eliminada"),
    ("remove", True): ("Dry-run", "Dry-run", "dry-run correcto"),
}

# Acciones del catálogo: no deben verse ni dispararse sobre otras pantallas.
_MAIN_ACTIONS = {
    "toggle_mark",
    "run",
    "show_details",
    "focus_search",
    "leave_search",
    "reload",
    "quit",
    "focus_next",
}

CSS = """
TopBar { height: 3; border: round $border-blurred; padding: 0 1; }
TopBar #tb-title { width: 1fr; content-align: center middle; text-style: bold; }
TopBar #tb-left, TopBar #tb-right { width: 16; color: $text-muted; }
TopBar #tb-right { content-align: right middle; }

.panel {
    border: round $border-blurred;
    border-title-color: $accent;
    border-title-style: bold;
    border-subtitle-color: $text-muted;
    background: $background;
}
.panel:focus-within { border: round $border; }

#search {
    border: round $border-blurred;
    border-title-color: $accent;
    border-title-style: bold;
    background: $background;
    height: 3;
}
#search:focus { border: round $border; }

#categories { width: 24; }
#apps { width: 1fr; }
#detail-panel { width: 36; padding: 0 1; }
#selected { margin-top: 1; }

ListView { background: $background; }
AppRow > Horizontal, CategoryRow > Horizontal { height: 1; }
AppRow .box { width: 4; }
AppRow .name { width: 1fr; }
AppRow .tag { width: auto; padding: 0 1; color: $text-muted; }
CategoryRow .name { width: 1fr; padding-left: 1; }
CategoryRow .count { width: auto; padding-right: 1; color: $text-muted; }

/* Diálogos con el mismo aspecto que los paneles: fondo de la app y borde redondo. */
ConfirmScreen, ParamsScreen { align: center middle; }
#dialog {
    width: 70; max-width: 90%; height: auto; max-height: 90%;
    padding: 1 2; border: round $border; background: $background;
}
#fields {
    height: auto; max-height: 55vh;
    scrollbar-size-vertical: 1; scrollbar-background: $background;
}
#dialog Input { background: $panel; border: tall $border-blurred; }
#dialog Input:focus { border: tall $border; }
.prompt { margin-top: 1; }
.link { color: $text-muted; }
.buttons { height: auto; margin-top: 1; align-horizontal: right; }
.buttons Button {
    margin-left: 1; min-width: 12;
    color: $foreground; background: $panel; border: tall $border-blurred;
}
.buttons Button:hover { border: tall $border; }
.buttons Button.-primary {
    color: $background; background: $primary; border: tall $primary;
}
.buttons Button:focus { text-style: bold; border: tall $accent; }

#progress { height: auto; max-height: 50%; padding: 0 1; }
#rows { height: auto; max-height: 12; }
ItemRow { height: 1; }
ItemRow .icon { width: 2; }
ItemRow .name { width: 24; }
ItemRow .action { width: 1fr; color: $text-muted; }
ItemRow .time { width: 9; content-align: right middle; color: $text-muted; }
/* El Bar interno de ProgressBar ya usa id="bar": no reutilizarlo. */
#progress-bar { width: 100%; margin-top: 1; }
#progress-bar Bar { width: 1fr; }
#progress-bar Bar > .bar--bar { color: $primary; background: $panel; }
#progress-bar Bar > .bar--complete { color: $success; }
#detail-page { height: 1fr; padding: 0 2; }
#detail-page Markdown { background: $background; }
#detail-page MarkdownH1 { content-align: left middle; color: $accent; }
#detail-page MarkdownH2, #detail-page MarkdownH3 { color: $accent; }
#registro { height: 1fr; }
#registro RichLog { background: $background; scrollbar-size-vertical: 1; }
"""


def _discard(kind: str, text: str) -> None:
    """Sink que descarta la salida."""


# --------------------------------------------------------------------------- #
# Widgets comunes
# --------------------------------------------------------------------------- #
class TopBar(Horizontal):
    """Cabecera: título centrado y un texto de estado a la derecha."""

    def __init__(self, right: str) -> None:
        """Crea la cabecera con ``right`` a la derecha."""
        super().__init__()
        self._right = right

    def compose(self) -> ComposeResult:
        """Compone los tres huecos de la cabecera."""
        yield Static("", id="tb-left")
        yield Static("AppForge", id="tb-title")
        yield Static(self._right, id="tb-right")

    def set_right(self, text: str) -> None:
        """Cambia el texto de la derecha.

        Args:
            text: Nuevo texto.
        """
        self.query_one("#tb-right", Static).update(text)


class AppRow(ListItem):
    """Fila de la lista: casilla, nombre y etiqueta de estado."""

    def __init__(self, entry: Entry) -> None:
        """Crea la fila para ``entry``."""
        super().__init__()
        self.entry = entry
        self._view: tuple[bool, State, bool] = (False, None, False)

    def compose(self) -> ComposeResult:
        """Compone casilla, nombre y etiqueta."""
        with Horizontal():
            yield Label("", classes="box")
            yield Label(escape(self.entry.name), classes="name")
            yield Label("", classes="tag")

    class Clicked(Message):
        """Clic sobre una fila; ``chain`` es 2 en un doble clic."""

        def __init__(self, row: "AppRow", chain: int) -> None:
            """Crea el mensaje para ``row``."""
            super().__init__()
            self.row = row
            self.chain = chain

    def on_mount(self) -> None:
        """Pinta el último estado recibido antes de estar montada."""
        self._paint()

    def on_click(self, event: events.Click) -> None:
        """Resalta la fila; el doble clic abre su detalle.

        Evita el comportamiento de ``ListItem`` (seleccionar con un clic), que
        marcaría y desmarcaría la entrada en cada doble clic.
        """
        event.prevent_default()
        event.stop()
        self.post_message(self.Clicked(self, event.chain))

    def render_state(self, marked: bool, state: State, checked: bool) -> None:
        """Pinta la casilla y la etiqueta.

        Se puede llamar antes de que la fila haya compuesto sus etiquetas (justo
        después de reconstruir la lista): el estado se guarda y se pinta al
        montarse.

        Args:
            marked: Si la entrada está seleccionada.
            state: Resultado de ``[check]``.
            checked: ``False`` mientras ``[check]`` no ha terminado.
        """
        self._view = (marked, state, checked)
        self._paint()

    def _paint(self) -> None:
        """Aplica ``_view`` si las etiquetas ya existen."""
        marked, state, checked = self._view
        try:
            box_label = self.query_one(".box", Label)
            tag_label = self.query_one(".tag", Label)
        except NoMatches:
            return  # aún sin componer: on_mount lo pintará
        box_label.update(
            Text(" ✔ ", style=f"bold {BACKGROUND} on {SUCCESS}")
            if marked
            else Text("   ", style=f"on {ANVIL_DARK}")
        )
        tag_label.update(_tag(self.entry, state, checked))


def _tag(entry: Entry, state: State, checked: bool) -> Text:
    """Etiqueta de la derecha de una fila."""
    if not entry.valid:
        return Text("inválida", style=STYLES["invalid"])
    if not checked:
        return Text("…", style=STYLES["muted"])
    if state:
        return Text("aplicada", style=STYLES["applied"])
    return Text("·", style=STYLES["muted"])  # no aplicada


class CategoryRow(ListItem):
    """Fila del panel de categorías."""

    def __init__(self, name: str, count: int) -> None:
        """Crea la fila ``name`` con ``count`` entradas."""
        super().__init__()
        self.category = name
        self.count = count

    def compose(self) -> ComposeResult:
        """Compone nombre y contador."""
        with Horizontal():
            yield Label(escape(self.category), classes="name")
            yield Label(str(self.count), classes="count")


def describe(entry: Entry, state: State, checked: bool = True) -> Group:
    """Ficha de una entrada para el panel de detalle.

    Args:
        entry: Entrada a describir.
        state: Resultado de ``[check]``.
        checked: ``False`` mientras ``[check]`` no ha terminado.

    Returns:
        Grupo de Rich listo para un ``Static``.
    """
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style=STYLES["muted"], no_wrap=True)
    grid.add_column(overflow="fold")
    if checked:
        labels = {True: ("aplicada", "applied"), False: ("no aplicada", "warn")}
        text, style = labels.get(state, ("sin [check]", "muted"))
    else:
        text, style = "comprobando…", "muted"
    grid.add_row("Estado", Text(text, style=STYLES[style]))
    grid.add_row("Categoría", entry.category or "—")
    grid.add_row("Parámetros", ", ".join(p.name for p in entry.params) or "—")
    kinds = ", ".join(sorted({s.kind for s in entry.steps}))
    grid.add_row("Pasos", f"{len(entry.steps)} ({kinds})" if kinds else "0")
    grid.add_row("Eliminar", "sí" if entry.remove else "no")
    grid.add_row("Carpeta", entry.source)
    parts: list[Text | Table] = [Text(entry.name + "\n", style=STYLES["title"]), grid]
    if entry.description:
        parts.append(Text("\n" + entry.description))
    parts.extend(Text(f"⚠ {p}", style=STYLES["invalid"]) for p in entry.problems)
    return Group(*parts)


def _selected_summary(names: list[str], width: int = 32) -> Text:
    """Separador y lista de entradas seleccionadas."""
    t = Text("─" * width + "\n", style=STYLES["muted"])
    t.append(f"Seleccionadas: {len(names)}\n", style=STYLES["applied"])
    for name in names:
        t.append(f"{name}\n")
    return t


# --------------------------------------------------------------------------- #
# Diálogos
# --------------------------------------------------------------------------- #
class ConfirmScreen(ModalScreen[bool]):
    """Diálogo de confirmación Sí/No."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("y,s", "answer(True)", "Sí"),
        ("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, message: str) -> None:
        """Crea el diálogo con ``message``."""
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Compone mensaje y botones."""
        with Vertical(id="dialog"):
            yield Label(self.message)
            with Horizontal(classes="buttons"):
                yield Button("Sí", variant="primary", id="yes")
                yield Button("No", id="no")

    def action_answer(self, value: bool) -> None:
        """Cierra con la respuesta ``value``."""
        self.dismiss(value)

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed) -> None:
        """Cierra según el botón pulsado."""
        self.dismiss(event.button.id == "yes")


def param_link(url: str) -> Text:
    """Enlace de un parámetro, pulsable en las terminales que lo admiten.

    Args:
        url: Dirección (http/https).

    Returns:
        Texto con estilo de enlace.
    """
    return Text.assemble(
        ("↗ ", STYLES["muted"]), (url, Style.parse(STYLES["link"]) + Style(link=url))
    )


class ParamsScreen(ModalScreen[dict[str, str] | None]):
    """Formulario con los parámetros de una entrada."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancelar")]

    def __init__(self, entry: Entry, position: str = "") -> None:
        """Crea el formulario para ``entry``.

        Args:
            entry: Entrada cuyos parámetros se piden.
            position: Texto opcional del tipo ``1/3`` para lotes.
        """
        super().__init__()
        self.entry = entry
        self.position = position

    def compose(self) -> ComposeResult:
        """Compone un campo por parámetro y los botones."""
        suffix = f" ({self.position})" if self.position else ""
        with Vertical(id="dialog"):
            yield Label(f"[b]{escape(self.entry.name)}[/b]: parámetros{suffix}")
            with VerticalScroll(id="fields"):
                for p in self.entry.params:
                    placeholder = ""
                    if p.default:
                        placeholder = "(por defecto)" if p.secret else p.default
                    yield Label(escape(p.prompt), classes="prompt")
                    if p.link:
                        yield Label(param_link(p.link), classes="link")
                    yield Input(
                        placeholder=placeholder, password=p.secret, id=f"p_{p.name}"
                    )
            # Fuera del scroll: los botones siempre visibles.
            with Horizontal(classes="buttons"):
                yield Button("Aceptar", variant="primary", id="ok")
                yield Button("Cancelar", id="cancel")

    def _values(self) -> dict[str, str]:
        """Valores escritos en el formulario."""
        return {
            p.name: self.query_one(f"#p_{p.name}", Input).value
            for p in self.entry.params
        }

    def _submit(self) -> None:
        """Valida y cierra con los valores."""
        values = self._values()
        try:
            resolve_values(self.entry, values)
        except EngineError as e:
            self.notify(str(e), severity="error")
            return
        self.dismiss(values)

    @on(Input.Submitted)
    def submitted(self, event: Input.Submitted) -> None:
        """Enter pasa al siguiente campo; en el último, acepta."""
        inputs = list(self.query(Input))
        index = inputs.index(event.input)
        if index + 1 < len(inputs):
            inputs[index + 1].focus()
        else:
            self._submit()

    @on(Button.Pressed, "#ok")
    def accept(self) -> None:
        """Botón Aceptar."""
        self._submit()

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Cierra sin valores."""
        self.dismiss(None)


def _md_code(code: str, lang: str = "bash") -> str:
    """Bloque de código Markdown con una valla que no choca con el contenido."""
    fence = "````" if "```" in code else "```"
    return f"{fence}{lang}\n{code.strip()}\n{fence}"


def entry_markdown(entry: Entry, state: State, checked: bool = True) -> str:
    """Página de detalle de una entrada en Markdown.

    Args:
        entry: Entrada a describir.
        state: Resultado de ``[check]``.
        checked: ``False`` mientras ``[check]`` no ha terminado.

    Returns:
        El documento Markdown.
    """
    if not checked:
        status = "comprobando…"
    else:
        status = {True: "aplicada", False: "no aplicada"}.get(state, "sin [check]")
    parts = [f"# {entry.name}"]
    if entry.description:
        parts.append(entry.description)
    parts.append(
        "| Estado | Categoría | Carpeta |\n|---|---|---|\n"
        f"| {status} | {entry.category or '—'} | `{entry.source}` |"
    )
    if entry.problems:
        parts.append("## Problemas")
        parts.append("\n".join(f"- {p}" for p in entry.problems))
    parts.append("## Descripción")
    parts.append(entry.details or "_Esta entrada no tiene descripción detallada._")
    if entry.params:
        rows = []
        for p in entry.params:
            if p.secret:
                default = "_(secreto)_"
            else:
                default = f"`{p.default}`" if p.default else "—"
            prompt = f"{p.prompt} ([{p.link}]({p.link}))" if p.link else p.prompt
            rows.append(f"| `{p.name}` | {prompt} | {default} |")
        parts.append("## Parámetros")
        parts.append(
            "| Nombre | Pregunta | Por defecto |\n|---|---|---|\n" + "\n".join(rows)
        )
    parts.append("## Pasos")
    for i, step in enumerate(entry.steps, 1):
        parts.append(f"**{i}. {step.title}** · `{step.kind}`")
        if step.kind == "run":
            parts.append(_md_code(step.value))
        elif step.kind == "script":
            parts.append(f"Ejecuta `{entry.id}/{step.value}` con bash.")
        else:
            mode = f" (modo `{step.mode:04o}`)" if step.mode is not None else ""
            verb = "Genera" if step.kind == "template" else "Copia"
            parts.append(f"{verb} `{step.dest}` desde `{entry.id}/{step.value}`{mode}.")
    if entry.check:
        parts.append("## Comprobación")
        parts.append(_md_code(entry.check))
    if entry.remove:
        parts.append("## Eliminación")
        parts.append(_md_code(entry.remove))
    return "\n\n".join(parts) + "\n"


class DetailScreen(Screen[None]):
    """Página con la descripción detallada de una entrada."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape,q,v", "close", "Volver")]

    def __init__(self, entry: Entry, state: State, checked: bool) -> None:
        """Crea la página para ``entry``.

        Args:
            entry: Entrada a mostrar.
            state: Resultado de ``[check]``.
            checked: ``False`` mientras ``[check]`` no ha terminado.
        """
        super().__init__()
        self.entry = entry
        self.state = state
        self.checked = checked

    def compose(self) -> ComposeResult:
        """Compone cabecera y documento."""
        yield TopBar("Detalle")
        panel = VerticalScroll(classes="panel", id="detail-page")
        panel.border_title = "Ficha"
        panel.border_subtitle = self.entry.source
        with panel:
            yield Markdown(entry_markdown(self.entry, self.state, self.checked))
        yield Footer()

    def on_mount(self) -> None:
        """Da el foco al documento para desplazarlo con el teclado."""
        self.query_one("#detail-page").focus()

    def action_close(self) -> None:
        """Vuelve al catálogo."""
        self.dismiss(None)


class LogScreen(Screen[None]):
    """Registro completo de ejecuciones."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape,q,l", "close", "Volver")]

    def __init__(self, runlog: RunLog) -> None:
        """Crea la pantalla para el fichero de ``runlog``."""
        super().__init__()
        self.runlog = runlog

    def compose(self) -> ComposeResult:
        """Compone cabecera y log."""
        yield TopBar("Registro")
        panel = Vertical(classes="panel", id="registro")
        panel.border_title = "Registro completo"
        panel.border_subtitle = _home_short(self.runlog.path)
        with panel:
            yield RichLog(wrap=True, markup=False, highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        """Carga las últimas líneas del fichero."""
        log = self.query_one(RichLog)
        try:
            lines = self.runlog.path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            log.write(Text(str(e), style=STYLES["error"]))
            return
        for line in lines[-2000:]:
            log.write(Text(line))

    def action_close(self) -> None:
        """Vuelve a la pantalla anterior."""
        self.dismiss(None)


# --------------------------------------------------------------------------- #
# Progreso
# --------------------------------------------------------------------------- #
class ItemRow(Horizontal):
    """Fila de progreso de una entrada."""

    def __init__(self, entry: Entry) -> None:
        """Crea la fila para ``entry`` en estado pendiente."""
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        """Compone icono, nombre, acción y tiempo."""
        yield Label(Text("·", style=STYLES["muted"]), classes="icon")
        yield Label(escape(self.entry.name), classes="name")
        yield Label("pendiente", classes="action")
        yield Label("", classes="time")

    def update_row(self, icon: Text, action: Text | str, seconds: float | None) -> None:
        """Actualiza la fila.

        Args:
            icon: Icono de estado.
            action: Texto de la acción en curso o del resultado.
            seconds: Duración, o ``None`` si aún no ha terminado.
        """
        self.query_one(".icon", Label).update(icon)
        self.query_one(".action", Label).update(action)
        time_text = "" if seconds is None else f"{seconds:.1f} s"
        self.query_one(".time", Label).update(time_text)


@dataclass
class Plan:
    """Lote a ejecutar.

    Attributes:
        action: ``apply`` o ``remove``.
        dry_run: Simular sin cambiar nada.
        entries: Entradas en orden de ejecución.
        values: Parámetros por id de entrada.
    """

    action: str
    dry_run: bool
    entries: list[Entry]
    values: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        """Pasos totales, para la barra de progreso."""
        if self.action == "remove":
            return len(self.entries)
        return sum(len(e.steps) for e in self.entries) or 1


class ProgressScreen(Screen[set[str]]):
    """Ejecuta un lote de entradas y muestra el progreso en vivo.

    Al cerrarse devuelve los ids de las entradas que terminaron bien.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+c", "cancel", "Cancelar", priority=True),
        Binding("l", "show_log", "Ver log completo"),
        Binding("escape", "close", "Volver"),
    ]

    def __init__(self, config: Config, plan: Plan) -> None:
        """Prepara la ejecución de ``plan``.

        Args:
            config: Configuración.
            plan: Lote a ejecutar.
        """
        super().__init__()
        self.config = config
        self.plan = plan
        self.runlog = RunLog(config)
        self.engine = Engine(config, _discard)
        self.running = True
        self.done: set[str] = set()
        _, self.heading, self.result_word = _VERBS[(plan.action, plan.dry_run)]

    def compose(self) -> ComposeResult:
        """Compone cabecera, progreso y registro."""
        yield TopBar(self.heading)
        progress = Vertical(classes="panel", id="progress")
        progress.border_title = f"Progreso 0 / {len(self.plan.entries)}"
        with progress:
            with VerticalScroll(id="rows"):
                for e in self.plan.entries:
                    yield ItemRow(e)
            yield ProgressBar(
                total=self.plan.total_steps, show_eta=False, id="progress-bar"
            )
        registro = Vertical(classes="panel", id="registro")
        registro.border_title = "Registro"
        registro.border_subtitle = f"log: {_home_short(self.runlog.path)}"
        with registro:
            yield RichLog(wrap=True, markup=False, highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        """Lanza la ejecución al mostrarse."""
        self.execute()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Muestra Cancelar mientras se ejecuta y Volver al terminar."""
        if action == "cancel":
            return self.running
        if action == "close":
            return not self.running
        return True

    # -- hilo de ejecución ----------------------------------------------- #
    @work(thread=True)
    def execute(self) -> None:
        """Ejecuta las entradas una a una en un hilo."""
        rows = list(self.query(ItemRow))
        bar = self.query_one(ProgressBar)
        done_steps = 0
        for index, (entry, row) in enumerate(zip(self.plan.entries, rows, strict=True)):
            if self.engine.cancelled:
                self._ui(
                    row.update_row, _icon("warn"), _result("cancelada", "warn"), None
                )
                continue
            self._ui(self._set_title, index + 1)
            ok = self._run_entry(entry, row, done_steps)
            done_steps += 1 if self.plan.action == "remove" else len(entry.steps)
            self._ui(bar.update, progress=done_steps)
            if ok:
                self.done.add(entry.id)
        self._ui(self._finish)

    def _run_entry(self, entry: Entry, row: ItemRow, done_steps: int) -> bool:
        """Ejecuta una entrada y actualiza su fila."""
        log = self.query_one(RichLog)
        bar = self.query_one(ProgressBar)
        current: dict[str, str | None] = {"kind": None}

        def sink(kind: str, text: str) -> None:
            tag = step_tag(current["kind"])
            line = Text(f"[{tag}] ", style=STYLES["muted"])
            if kind == "step":
                line.append(f"{entry.id}: {text}", style=STYLES["step"])
            else:
                line.append(_PREFIX.get(kind, "") + text, style=STYLES.get(kind, ""))
            self._ui(log.write, line)
            self.runlog.write(kind, f"{entry.id} [{tag}] {text}")

        def on_step(index: int, total: int, step: Step) -> None:
            current["kind"] = step.kind
            self._ui(row.update_row, _icon("run"), step.title, None)
            self._ui(bar.update, progress=done_steps + index - 1)

        self.engine.sink = sink
        self.engine.on_step = on_step
        self._ui(row.update_row, _icon("run"), "comprobando estado", None)
        start = time.monotonic()
        try:
            if self.plan.action == "apply":
                values = self.plan.values.get(entry.id, {})
                ok = self.engine.apply(entry, values, dry_run=self.plan.dry_run)
            else:
                ok = self.engine.remove(entry, dry_run=self.plan.dry_run)
        except Exception as e:  # cualquier fallo debe verse en el registro
            sink("error", f"{type(e).__name__}: {e}")
            ok = False
        elapsed = time.monotonic() - start
        if ok:
            icon, result = _icon("ok"), _result(self.result_word, "muted")
        elif self.engine.cancelled:
            icon, result = _icon("warn"), _result("cancelada", "warn")
        else:
            icon, result = _icon("error"), _result("falló: revisa el registro", "error")
        self._ui(row.update_row, icon, result, elapsed)
        return ok

    def _ui(self, fn: Callable[..., object], *args: object, **kwargs: object) -> None:
        """Ejecuta ``fn`` en el hilo de la interfaz."""
        self.app.call_from_thread(fn, *args, **kwargs)

    # -- hilo de la interfaz --------------------------------------------- #
    def _set_title(self, current: int) -> None:
        """Actualiza «Progreso i / N»."""
        panel = self.query_one("#progress")
        panel.border_title = f"Progreso {current} / {len(self.plan.entries)}"

    def _finish(self) -> None:
        """Marca el final del lote."""
        self.running = False
        total = len(self.plan.entries)
        ok = len(self.done)
        if self.engine.cancelled:
            status = "Cancelado"
        elif ok == total:
            status = "Completado"
        else:
            status = "Con errores"
        self.query_one(TopBar).set_right(status)
        self._set_title(total)
        self.refresh_bindings()
        message = f"\n{status}: {ok} de {total}. Pulsa Esc para volver."
        self.query_one(RichLog).write(Text(message, style=STYLES["info"]))

    def action_cancel(self) -> None:
        """Pide cancelar: termina el comando en curso y no sigue."""
        if self.running and not self.engine.cancelled:
            self.engine.cancel()
            self.query_one(TopBar).set_right("Cancelando…")

    def action_show_log(self) -> None:
        """Abre el registro completo."""
        self.app.push_screen(LogScreen(self.runlog))

    def action_close(self) -> None:
        """Vuelve al menú con los ids completados."""
        if not self.running:
            self.dismiss(self.done)


def _icon(kind: str) -> Text:
    """Icono de estado para una fila de progreso."""
    icons = {
        "run": ("▶", STYLES["step"]),
        "ok": ("✔", STYLES["ok"]),
        "warn": ("!", STYLES["warn"]),
        "error": ("✘", STYLES["error"]),
    }
    glyph, style = icons[kind]
    return Text(glyph, style=style)


def _result(text: str, style: str) -> Text:
    """Texto de resultado con un estilo del tema."""
    return Text(text, style=STYLES[style])


def _home_short(path: os.PathLike[str] | str) -> str:
    """Ruta con ``~`` en lugar del directorio personal."""
    text = os.fspath(path)
    home = str(Path.home())
    return "~" + text[len(home) :] if text.startswith(home + os.sep) else text


# --------------------------------------------------------------------------- #
# Aplicación
# --------------------------------------------------------------------------- #
class AppForgeApp(App[None]):
    """Pantalla principal: catálogo, detalle y selección."""

    TITLE = "AppForge"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_mark", "Marcar"),
        Binding("i", "run('apply', False)", "Instalar"),
        Binding("u", "run('remove', False)", "Desinstalar"),
        Binding("d", "run('apply', True)", "Dry-run"),
        Binding("v", "show_details", "Ver"),
        Binding("slash", "focus_search", "Buscar"),
        Binding("tab", "focus_next", "Cambiar panel", priority=True),
        Binding("escape", "leave_search", "", show=False),
        Binding("r", "reload", "Recargar", show=False),
        Binding("q", "quit", "Salir"),
    ]

    def __init__(self, config: Config) -> None:
        """Crea la aplicación con ``config``."""
        super().__init__()
        self.config = config
        self.entries: list[Entry] = []
        self.states: dict[str, State] = {}
        self.checked: set[str] = set()
        self.marked: set[str] = set()
        self.category = ALL
        self.search_text = ""

    # -- composición ----------------------------------------------------- #
    def compose(self) -> ComposeResult:
        """Compone cabecera, buscador, paneles y pie."""
        yield TopBar(f"v{__version__}")
        if self.config.ui.search:
            search = Input(placeholder="/ Buscar aplicación...", id="search")
            search.border_title = "Buscar"
            yield search
        with Horizontal():
            if self.config.ui.categories:
                categories = ListView(id="categories", classes="panel")
                categories.border_title = "Categorías"
                yield categories
            apps = ListView(id="apps", classes="panel")
            apps.border_title = "Aplicaciones"
            yield apps
            detail = VerticalScroll(id="detail-panel", classes="panel")
            detail.border_title = "Detalle"
            with detail:
                yield Static(id="detail")
                yield Static(id="selected")
        yield Footer()

    def on_mount(self) -> None:
        """Registra el tema y carga las entradas."""
        self.register_theme(TEXTUAL_THEME)
        self.theme = THEME_NAME
        self.action_reload()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Atajos del catálogo solo en la pantalla principal; «Buscar» si activo."""
        if action in _MAIN_ACTIONS and self.screen is not self.screen_stack[0]:
            return False
        if action == "focus_search":
            return self.config.ui.search
        return True

    # -- carga y filtrado ------------------------------------------------ #
    def action_reload(self) -> None:
        """Vuelve a leer las entradas y sus estados."""
        catalog = load_catalog(self.config.entries_dirs)
        self.entries, problems = catalog.entries, catalog.problems
        self.marked &= {e.id for e in self.entries}
        self.checked.clear()
        for problem in problems:
            self.notify(problem, severity="error", timeout=10)
        self._fill_categories()
        self._fill_apps()
        self.query_one("#apps", ListView).focus()
        self.refresh_states()

    @staticmethod
    def _category_of(entry: Entry) -> str:
        """Categoría que se muestra para ``entry``."""
        return entry.category or NO_CATEGORY

    def _fill_categories(self) -> None:
        """Rellena el panel de categorías, si está activo."""
        if not self.config.ui.categories:
            return
        counts: dict[str, int] = {}
        for e in self.entries:
            name = self._category_of(e)
            counts[name] = counts.get(name, 0) + 1
        names = sorted(counts, key=lambda c: (c == NO_CATEGORY, c.lower()))
        if self.category not in counts:
            self.category = ALL
        panel = self.query_one("#categories", ListView)
        panel.clear()
        panel.append(CategoryRow(ALL, len(self.entries)))
        for name in names:
            panel.append(CategoryRow(name, counts[name]))
        panel.index = [ALL, *names].index(self.category)

    def visible_entries(self) -> list[Entry]:
        """Entradas que pasan el filtro de categoría y búsqueda.

        Returns:
            Las entradas en orden de menú.
        """
        text = self.search_text.lower()
        out = []
        for e in self.entries:
            if self.category != ALL and self._category_of(e) != self.category:
                continue
            haystack = f"{e.name} {e.id} {e.description} {e.category}".lower()
            if text and text not in haystack:
                continue
            out.append(e)
        return out

    def _fill_apps(self) -> None:
        """Reconstruye la lista conservando la entrada resaltada."""
        apps = self.query_one("#apps", ListView)
        visible = self.visible_entries()
        ids = [e.id for e in visible]
        if ids == [row.entry.id for row in self.query(AppRow)]:
            self._repaint()  # mismo resultado: no hace falta reconstruir
            return
        current = self.current_entry()
        keep = current.id if current else None
        apps.clear()
        for e in visible:
            apps.append(AppRow(e))
        apps.index = ids.index(keep) if keep in ids else (0 if ids else None)
        self.call_after_refresh(self._repaint)

    def _repaint(self) -> None:
        """Repinta filas, detalle y seleccionadas."""
        for row in self.query(AppRow):
            row.render_state(
                row.entry.id in self.marked,
                self.states.get(row.entry.id),
                row.entry.id in self.checked,
            )
        self._show_detail()

    @work(thread=True, exclusive=True, group="checks")
    def refresh_states(self) -> None:
        """Ejecuta ``[check]`` de cada entrada en segundo plano."""
        engine = Engine(self.config, _discard)
        for entry in list(self.entries):
            state = engine.is_applied(entry)
            self.call_from_thread(self._set_state, entry.id, state)

    def _set_state(self, entry_id: str, state: State) -> None:
        """Guarda un estado calculado en el hilo de checks."""
        self.states[entry_id] = state
        self.checked.add(entry_id)
        self._repaint()

    # -- detalle --------------------------------------------------------- #
    def current_entry(self) -> Entry | None:
        """Entrada resaltada en la lista.

        Returns:
            La entrada, o ``None`` si la lista está vacía.
        """
        item = self.query_one("#apps", ListView).highlighted_child
        return item.entry if isinstance(item, AppRow) else None

    def _show_detail(self) -> None:
        """Muestra la ficha de la entrada resaltada y lo seleccionado."""
        entry = self.current_entry()
        detail = self.query_one("#detail", Static)
        if entry is None:
            detail.update(Text("No hay entradas que mostrar", style=STYLES["muted"]))
        else:
            state = self.states.get(entry.id)
            detail.update(describe(entry, state, entry.id in self.checked))
        names = [e.name for e in self.entries if e.id in self.marked]
        self.query_one("#selected", Static).update(_selected_summary(names))

    @on(ListView.Highlighted, "#apps")
    def app_highlighted(self) -> None:
        """Actualiza el detalle al moverse por la lista."""
        self._show_detail()

    @on(AppRow.Clicked)
    def app_clicked(self, event: AppRow.Clicked) -> None:
        """Clic: resalta la fila. Doble clic: abre su página de detalle."""
        apps = self.query_one("#apps", ListView)
        rows = list(self.query(AppRow))
        if event.row in rows:
            apps.index = rows.index(event.row)
        apps.focus()
        if event.chain >= 2:
            self.action_show_details()

    def action_show_details(self) -> None:
        """Abre la página de detalle de la entrada resaltada."""
        entry = self.current_entry()
        if entry is None:
            return
        checked = entry.id in self.checked
        self.push_screen(DetailScreen(entry, self.states.get(entry.id), checked))

    @on(ListView.Selected, "#apps")
    def app_selected(self) -> None:
        """Enter sobre una entrada: marcar o desmarcar."""
        self.action_toggle_mark()

    @on(ListView.Highlighted, "#categories")
    def category_highlighted(self, event: ListView.Highlighted) -> None:
        """Filtra por la categoría resaltada."""
        item = event.item
        if isinstance(item, CategoryRow) and item.category != self.category:
            self.category = item.category
            self._fill_apps()

    @on(Input.Changed, "#search")
    def search_changed(self, event: Input.Changed) -> None:
        """Filtra mientras se escribe (solo si el filtro cambia)."""
        text = event.value.strip()
        if text == self.search_text:
            return
        self.search_text = text
        self._fill_apps()

    @on(Input.Submitted, "#search")
    def search_submitted(self) -> None:
        """Enter en el buscador: ir a la lista."""
        self.query_one("#apps", ListView).focus()

    def action_focus_search(self) -> None:
        """Lleva el foco al buscador."""
        if self.config.ui.search:
            self.query_one("#search", Input).focus()

    def action_leave_search(self) -> None:
        """Esc en el buscador: volver a la lista."""
        if self.focused is not None and self.focused.id == "search":
            self.query_one("#apps", ListView).focus()

    # -- selección ------------------------------------------------------- #
    def action_toggle_mark(self) -> None:
        """Marca o desmarca la entrada resaltada."""
        entry = self.current_entry()
        if entry is None:
            return
        if not entry.valid:
            self.notify("Entrada inválida: revisa el detalle", severity="error")
            return
        self.marked ^= {entry.id}
        self._repaint()

    def targets(self) -> list[Entry]:
        """Entradas sobre las que actuar: las marcadas o, si no hay, la resaltada.

        Returns:
            Las entradas en orden de menú.
        """
        marked = [e for e in self.entries if e.id in self.marked]
        if marked:
            return marked
        current = self.current_entry()
        return [current] if current else []

    # -- ejecución ------------------------------------------------------- #
    def action_run(self, action: str, dry_run: bool) -> None:
        """Instala, desinstala o simula las entradas seleccionadas.

        Args:
            action: ``apply`` o ``remove``.
            dry_run: Simular sin cambiar nada.
        """
        self.run_flow(action, dry_run)

    @work(exclusive=True, group="flow")
    async def run_flow(self, action: str, dry_run: bool) -> None:
        """Parámetros, confirmación y pantalla de progreso.

        Args:
            action: ``apply`` o ``remove``.
            dry_run: Simular sin cambiar nada.
        """
        entries = self._runnable(self.targets(), action)
        if not entries:
            return
        plan = Plan(action=action, dry_run=dry_run, entries=entries)
        if action == "apply":
            with_params = [e for e in entries if e.params]
            for n, entry in enumerate(with_params, 1):
                position = f"{n}/{len(with_params)}" if len(with_params) > 1 else ""
                got = await self.push_screen_wait(ParamsScreen(entry, position))
                if got is None:
                    return
                plan.values[entry.id] = got

        if not dry_run:
            verb = _VERBS[(action, False)][0]
            names = "\n".join(f"  • {escape(e.name)}" for e in entries)
            user = invoking_user()[0]
            question = (
                f"¿{verb} {len(entries)} entrada(s)?\n\n{names}\n\n"
                f"Usuario (APPFORGE_USER): {escape(user)}"
            )
            if not await self.push_screen_wait(ConfirmScreen(question)):
                return

        done = await self.push_screen_wait(ProgressScreen(self.config, plan))
        if not dry_run:
            self.marked -= done or set()
        self.checked.clear()
        self._repaint()
        self.refresh_states()

    def _runnable(self, entries: list[Entry], action: str) -> list[Entry]:
        """Descarta (avisando) las entradas que no admiten ``action``."""
        out = []
        for e in entries:
            if not e.valid:
                self.notify(f"{e.name}: entrada inválida", severity="error")
            elif action == "remove" and not e.remove:
                self.notify(f"{e.name}: no define [remove]", severity="warning")
            else:
                out.append(e)
        return out


def run_tui(config: Config) -> int:
    """Arranca la TUI.

    Args:
        config: Configuración.

    Returns:
        Código de salida: 2 si no hay terminal, 0 en otro caso.
    """
    if os.environ.get("TERM") in (None, "", "dumb"):
        print("appforge: la TUI necesita una terminal. Usa 'appforge --help'.")
        return 2
    AppForgeApp(config).run()
    return 0
