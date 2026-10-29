"""TUI con Textual: menú de entradas con ✔, parámetros y log en vivo."""

import os
from typing import ClassVar

from rich.markup import escape
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from appforge.config import Config
from appforge.engine import Engine, EngineError, resolve_values
from appforge.entry import Entry, load_entries

type State = bool | None

_STYLE = {
    "step": "bold cyan",
    "ok": "bold green",
    "warn": "bold yellow",
    "error": "bold red",
    "info": "dim",
}
_PREFIX = {"step": "==> ", "ok": "✔ ", "warn": "! ", "error": "✘ ", "out": "│ "}


def _discard(kind: str, text: str) -> None:
    """Sink que descarta la salida."""


class EntryItem(ListItem):
    """Elemento del menú: marca de estado y nombre de la entrada."""

    def __init__(self, entry: Entry) -> None:
        """Crea el elemento para ``entry`` con estado pendiente."""
        super().__init__()
        self.entry = entry
        self.state: State = None
        self.checked = False

    def compose(self) -> ComposeResult:
        """Compone la etiqueta."""
        yield Label(self._markup())

    def _markup(self) -> str:
        """Texto con marca de estado."""
        if not self.entry.valid:
            mark = "[red]⚠[/]"
        elif not self.checked:
            mark = "[dim]…[/]"
        else:
            mark = {True: "[green]✔[/]", False: " ", None: "[dim]·[/]"}[self.state]
        root = " [dim](root)[/]" if self.entry.requires_root else ""
        return f"{mark} {escape(self.entry.name)}{root}"

    def set_state(self, state: State) -> None:
        """Actualiza el estado mostrado.

        Args:
            state: Resultado de ``[check]``.
        """
        self.state = state
        self.checked = True
        self.query_one(Label).update(self._markup())


def describe(entry: Entry, state: State, checked: bool = True) -> Text:
    """Ficha de una entrada para el panel de detalle.

    Args:
        entry: Entrada a describir.
        state: Resultado de ``[check]``.
        checked: ``False`` mientras ``[check]`` no ha terminado.

    Returns:
        Texto enriquecido listo para un ``Static``.
    """
    t = Text()
    t.append(f"{entry.name}\n", style="bold")
    t.append(f"{entry.id}.toml\n", style="dim")
    if entry.description:
        t.append(f"\n{entry.description}\n")
    labels = {
        True: ("aplicada", "green"),
        False: ("no aplicada", "yellow"),
        None: ("sin [check]", "dim"),
    }
    label, style = labels[state] if checked else ("comprobando…", "dim")
    t.append("\nEstado: ")
    t.append(label, style=style)
    t.append(f"\nRoot: {'sí' if entry.requires_root else 'no'}\n")
    if entry.params:
        t.append("\nParámetros\n", style="bold")
        for p in entry.params:
            extra = (
                " (secreto)" if p.secret else (f" = {p.default}" if p.default else "")
            )
            t.append(f"  • {p.prompt}{extra}\n")
    t.append("\nPasos\n", style="bold")
    for i, s in enumerate(entry.steps, 1):
        dest = f" → {s.dest}" if s.dest else ""
        t.append(f"  {i}. {s.title} ")
        t.append(f"[{s.kind}{dest}]\n", style="dim")
    if entry.remove:
        t.append("\n[remove] disponible\n", style="dim")
    if entry.problems:
        t.append("\nProblemas\n", style="bold red")
        for problem in entry.problems:
            t.append(f"  ⚠ {problem}\n", style="red")
    return t


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


class ParamsScreen(ModalScreen[dict[str, str] | None]):
    """Formulario con los parámetros de una entrada."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancelar")]

    def __init__(self, entry: Entry) -> None:
        """Crea el formulario para ``entry``."""
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        """Compone un campo por parámetro y los botones."""
        with Vertical(id="dialog"):
            yield Label(f"[b]{escape(self.entry.name)}[/b]: parámetros")
            with VerticalScroll(id="fields"):
                for p in self.entry.params:
                    placeholder = ""
                    if p.default:
                        placeholder = "(por defecto)" if p.secret else p.default
                    yield Label(escape(p.prompt), classes="prompt")
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


class RunScreen(Screen[bool]):
    """Pantalla que ejecuta una acción y muestra su log en vivo."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape,q", "close", "Volver")]

    def __init__(
        self,
        config: Config,
        entry: Entry,
        action: str,
        values: dict[str, str],
        dry_run: bool,
    ) -> None:
        """Prepara la ejecución.

        Args:
            config: Configuración.
            entry: Entrada sobre la que actuar.
            action: ``apply`` o ``remove``.
            values: Valores de los parámetros.
            dry_run: Simular sin cambiar nada.
        """
        super().__init__()
        self.config = config
        self.entry = entry
        self.action = action
        self.values = values
        self.dry_run = dry_run
        self.running = True
        self.ok = False

    def compose(self) -> ComposeResult:
        """Compone título y log."""
        verb = "Aplicar" if self.action == "apply" else "Eliminar"
        mode = " (dry-run)" if self.dry_run else ""
        yield Header()
        yield Static(f"[b]{verb}{mode}:[/b] {escape(self.entry.name)}", id="run-title")
        yield RichLog(wrap=True, markup=False, highlight=False, id="log")
        yield Footer()

    def on_mount(self) -> None:
        """Lanza la ejecución al mostrarse."""
        self.execute()

    @work(thread=True)
    def execute(self) -> None:
        """Ejecuta el motor en un hilo y vuelca la salida al log."""
        log = self.query_one(RichLog)

        def sink(kind: str, text: str) -> None:
            line = Text(_PREFIX.get(kind, "") + text, style=_STYLE.get(kind, ""))
            self.app.call_from_thread(log.write, line)

        engine = Engine(self.config, sink)
        try:
            if self.action == "apply":
                ok = engine.apply(self.entry, self.values, dry_run=self.dry_run)
            else:
                ok = engine.remove(self.entry, dry_run=self.dry_run)
        except Exception as e:  # cualquier fallo debe verse en el log
            sink("error", f"{type(e).__name__}: {e}")
            ok = False
        self.app.call_from_thread(self._finish, ok)

    def _finish(self, ok: bool) -> None:
        """Marca el final de la ejecución."""
        self.running = False
        self.ok = ok
        self.query_one(RichLog).write(
            Text("\nPulsa Esc para volver al menú.", style="dim")
        )

    def action_close(self) -> None:
        """Vuelve al menú si ya terminó."""
        if self.running:
            self.notify("Todavía en ejecución…", severity="warning")
            return
        self.dismiss(self.ok)


class AppForgeApp(App[None]):
    """Aplicación principal: menú de entradas y panel de detalle."""

    TITLE = "AppForge"
    CSS = """
    #menu { width: 40%; min-width: 30; border-right: solid $primary-darken-2; }
    #detail { padding: 0 2; }
    #dialog { width: 70; max-width: 90%; height: auto; max-height: 90%;
              padding: 1 2; border: thick $primary; background: $surface; }
    #fields { height: auto; max-height: 55vh; }
    ConfirmScreen, ParamsScreen { align: center middle; }
    .prompt { margin-top: 1; }
    .buttons { height: auto; margin-top: 1; align-horizontal: right; }
    .buttons Button { margin-left: 1; }
    #run-title { padding: 0 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("a", "apply(False)", "Aplicar"),  # Enter también (ListView.Selected)
        Binding("d", "apply(True)", "Dry-run"),
        Binding("x", "remove", "Eliminar"),
        Binding("r", "reload", "Recargar"),
        Binding("q", "quit", "Salir"),
    ]

    def __init__(self, config: Config) -> None:
        """Crea la aplicación con ``config``."""
        super().__init__()
        self.config = config
        self.entries: list[Entry] = []

    def compose(self) -> ComposeResult:
        """Compone menú y detalle."""
        yield Header()
        with Horizontal():
            yield ListView(id="menu")
            with VerticalScroll():
                yield Static(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        """Carga las entradas al arrancar."""
        self.sub_title = str(self.config.entries_dir)
        self.action_reload()

    # -- carga y estado -------------------------------------------------- #
    def action_reload(self) -> None:
        """Vuelve a leer las entradas y sus estados."""
        self.entries, problems = load_entries(self.config.entries_dir)
        menu = self.query_one(ListView)
        menu.clear()
        for e in self.entries:
            menu.append(EntryItem(e))
        if not self.entries:
            self.query_one("#detail", Static).update(
                f"No hay entradas en {self.config.entries_dir}"
            )
        for problem in problems:
            self.notify(problem, severity="error", timeout=10)
        menu.index = 0 if self.entries else None
        menu.focus()
        self.refresh_states()

    @work(thread=True, exclusive=True, group="checks")
    def refresh_states(self) -> None:
        """Ejecuta ``[check]`` de cada entrada en segundo plano."""
        engine = Engine(self.config, _discard)
        for item in list(self.query(EntryItem)):
            state = engine.is_applied(item.entry)
            self.call_from_thread(self._set_state, item, state)

    def _set_state(self, item: EntryItem, state: State) -> None:
        """Aplica un estado calculado en el hilo de checks."""
        if not item.is_attached:
            return
        item.set_state(state)
        if self.current_item() is item:
            self._show(item)

    def current_item(self) -> EntryItem | None:
        """Elemento resaltado del menú.

        Returns:
            El elemento, o ``None`` si el menú está vacío.
        """
        item = self.query_one(ListView).highlighted_child
        return item if isinstance(item, EntryItem) else None

    def _show(self, item: EntryItem) -> None:
        """Muestra la ficha de ``item``."""
        self.query_one("#detail", Static).update(
            describe(item.entry, item.state, item.checked)
        )

    @on(ListView.Highlighted)
    def highlighted(self, event: ListView.Highlighted) -> None:
        """Actualiza el detalle al moverse por el menú."""
        if isinstance(event.item, EntryItem):
            self._show(event.item)

    @on(ListView.Selected)
    def selected(self) -> None:
        """Enter sobre una entrada: aplicar."""
        self.action_apply(False)

    # -- acciones -------------------------------------------------------- #
    def action_apply(self, dry_run: bool) -> None:
        """Aplica la entrada resaltada.

        Args:
            dry_run: Simular sin cambiar nada.
        """
        self.run_flow("apply", dry_run)

    def action_remove(self) -> None:
        """Elimina la entrada resaltada."""
        self.run_flow("remove", False)

    @work(exclusive=True, group="flow")
    async def run_flow(self, action: str, dry_run: bool) -> None:
        """Parámetros, confirmación, sudo y ejecución.

        Args:
            action: ``apply`` o ``remove``.
            dry_run: Simular sin cambiar nada.
        """
        item = self.current_item()
        if item is None:
            return
        entry = item.entry
        if not entry.valid:
            self.notify("Entrada inválida: revisa los problemas", severity="error")
            return
        if action == "remove" and not entry.remove:
            self.notify("Esta entrada no define [remove]", severity="warning")
            return

        values: dict[str, str] = {}
        if action == "apply" and entry.params:
            got = await self.push_screen_wait(ParamsScreen(entry))
            if got is None:
                return
            values = got

        if not dry_run:
            verb = "¿Aplicar" if action == "apply" else "¿Eliminar"
            question = f"{verb} «{escape(entry.name)}»?"
            if not await self.push_screen_wait(ConfirmScreen(question)):
                return
            if entry.requires_root and not self._get_root(entry):
                return

        await self.push_screen_wait(
            RunScreen(self.config, entry, action, values, dry_run)
        )
        self.refresh_states()

    def _get_root(self, entry: Entry) -> bool:
        """Obtiene privilegios suspendiendo la TUI para pedir la contraseña."""
        engine = Engine(self.config, lambda _k, t: self.notify(t, severity="error"))
        if not engine.password_needed(entry):
            return engine.acquire_root()
        try:
            with self.suspend():
                print(f"\n«{entry.name}» necesita privilegios de administrador.")
                ok = engine.acquire_root()
        except Exception:  # SuspendNotSupported fuera de una terminal real
            self.notify(
                "No puedo pedir la contraseña aquí. Ejecuta 'sudo -v' antes de abrir "
                "AppForge.",
                severity="error",
                timeout=10,
            )
            return False
        if not ok:
            self.notify(
                "No se obtuvieron privilegios de administrador", severity="error"
            )
        return ok


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
