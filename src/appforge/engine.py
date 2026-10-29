"""Ejecución de entradas: check, pasos, eliminación, copias y dry-run.

Toda la salida pasa por un ``sink(kind, text)`` para que la CLI y la TUI la
muestren a su manera. ``kind`` es uno de ``step``, ``out``, ``info``, ``ok``,
``warn`` o ``error``.
"""

import difflib
import os
import shlex
import shutil
import string
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from acodo.utils import get_env

from appforge.config import Config
from appforge.entry import Entry, Step

type Sink = Callable[[str, str], None]
# (número de paso, total, paso) justo antes de ejecutarlo.
type Progress = Callable[[int, int, Step], None]

MASK = "••••••"
SUDO_ENV = "APPFORGE_SUDO"


class EngineError(Exception):
    """Error al ejecutar una entrada (parámetros, plantillas o ficheros)."""


def _discard(kind: str, text: str) -> None:
    """Sink que descarta la salida."""


def default_sudo() -> list[str]:
    """Prefijo para los comandos privilegiados.

    La variable ``APPFORGE_SUDO`` lo sustituye; vacía significa «sin prefijo»
    y se usa en los tests.

    Returns:
        El prefijo como lista de argumentos.
    """
    env = get_env(SUDO_ENV, default=None)
    return ["sudo", "-n"] if env is None else shlex.split(env)


def sudo_overridden() -> bool:
    """``True`` si ``APPFORGE_SUDO`` sustituye a sudo."""
    return SUDO_ENV in os.environ


def resolve_values(entry: Entry, given: dict[str, str]) -> dict[str, str]:
    """Combina los valores dados con los valores por defecto.

    Args:
        entry: Entrada cuyos parámetros se resuelven.
        given: Valores introducidos. Una cadena vacía equivale a no darlo.

    Returns:
        Un valor por cada parámetro de la entrada.

    Raises:
        EngineError: Si se da un parámetro desconocido o falta uno sin
            valor por defecto.

    Examples:
        >>> from pathlib import Path
        >>> from appforge.entry import Entry, Param
        >>> e = Entry("x", Path("x.toml"), "X", params=[Param("a", "A", "1")])
        >>> resolve_values(e, {})
        {'a': '1'}
    """
    unknown = set(given) - {p.name for p in entry.params}
    if unknown:
        raise EngineError(f"Parámetros desconocidos: {', '.join(sorted(unknown))}")
    values: dict[str, str] = {}
    missing = []
    for p in entry.params:
        value = given.get(p.name) or p.default
        if value:
            values[p.name] = value
        else:
            missing.append(p.name)
    if missing:
        raise EngineError(f"Faltan parámetros: {', '.join(missing)}")
    return values


def _wrap_cancellable(script: str) -> list[str]:
    """Envuelve ``script`` para que SIGTERM mate a todos sus procesos.

    bash no atiende una señal hasta que termina el comando en primer plano, así
    que el código va en un subshell en segundo plano con su propio grupo de
    procesos (``set -m``) y el script principal espera con ``wait``, que sí se
    interrumpe. El código de salida del subshell se conserva.
    """
    return [
        "set -m",
        "(",
        script,
        ") &",
        "__af_child=$!",
        "trap 'kill -TERM -- \"-$__af_child\" 2>/dev/null' TERM INT",
        'wait "$__af_child"; __af_rc=$?',
        'wait "$__af_child" 2>/dev/null',
        'exit "$__af_rc"',
    ]


@contextmanager
def _temp_file(data: bytes) -> Generator[Path]:
    """Fichero temporal 0600 con ``data``, borrado al salir."""
    fd, name = tempfile.mkstemp(prefix="appforge-")
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        yield path
    finally:
        path.unlink(missing_ok=True)


class Runner:
    """Ejecuta comandos y escribe ficheros, con o sin privilegios."""

    def __init__(
        self, sink: Sink, secrets: list[str], sudo: list[str] | None = None
    ) -> None:
        """Crea el ejecutor.

        Args:
            sink: Destino de la salida.
            secrets: Valores que se enmascaran en toda la salida.
            sudo: Prefijo privilegiado; ``None`` usa :func:`default_sudo`.
        """
        self.sink = sink
        self.secrets = [s for s in secrets if s]
        self.sudo = default_sudo() if sudo is None else sudo
        self.proc: subprocess.Popen[str] | None = None

    def mask(self, text: str) -> str:
        """Sustituye los secretos de ``text`` por ``MASK``.

        Args:
            text: Texto a mostrar.

        Returns:
            El texto sin secretos.
        """
        for secret in self.secrets:
            text = text.replace(secret, MASK)
        return text

    def _prefix(self, privileged: bool) -> list[str]:
        """Prefijo sudo, vacío si no hace falta."""
        return list(self.sudo) if privileged and os.geteuid() != 0 else []

    def shell(
        self,
        script: str,
        env: dict[str, str],
        cwd: Path,
        privileged: bool,
        *,
        capture: bool = False,
        timeout: float | None = None,
    ) -> int:
        """Ejecuta ``script`` con bash.

        Las variables viajan dentro de un fichero temporal 0600, no en
        ``argv`` ni en el entorno (sudo lo limpia), así los secretos no se ven
        en ``ps``.

        Args:
            script: Código bash.
            env: Variables a exportar antes del script.
            cwd: Directorio de trabajo, si existe.
            privileged: Ejecutar con el prefijo sudo.
            capture: Descartar la salida en lugar de enviarla al sink.
            timeout: Segundos máximos (solo con ``capture``).

        Returns:
            Código de salida; 124 si se agota ``timeout``.
        """
        lines = [f"export {k}={shlex.quote(v)}" for k, v in env.items()]
        if cwd.is_dir():
            lines.append(f"cd {shlex.quote(str(cwd))}")
        lines.extend(_wrap_cancellable(script))
        with _temp_file(("\n".join(lines) + "\n").encode()) as tmp:
            argv = [*self._prefix(privileged), "bash", str(tmp)]
            if capture:
                with subprocess.Popen(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ) as proc:
                    try:
                        return proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        proc.terminate()  # el trap mata también a los hijos
                        proc.wait()
                        return 124
            with subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                errors="replace",
            ) as proc:
                self.proc = proc
                try:
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        self.sink("out", self.mask(line.rstrip("\n")))
                    return proc.wait()
                finally:
                    self.proc = None

    def terminate(self) -> None:
        """Termina el comando en curso, si lo hay (sudo reenvía la señal)."""
        proc = self.proc
        if proc is not None and proc.poll() is None:
            proc.terminate()

    def exists(self, path: Path, privileged: bool) -> bool:
        """``True`` si ``path`` existe, mirando con sudo si hace falta."""
        if path.exists():
            return True
        prefix = self._prefix(privileged)
        if not prefix:
            return False
        argv = [*prefix, "test", "-e", str(path)]
        return (
            subprocess.run(argv, stdin=subprocess.DEVNULL, check=False).returncode == 0
        )

    def read(self, path: Path, privileged: bool) -> bytes | None:
        """Lee ``path``, con sudo si no es legible.

        Args:
            path: Fichero a leer.
            privileged: Permitir sudo.

        Returns:
            El contenido, o ``None`` si no existe.

        Raises:
            PermissionError: Si no es legible y no se permite sudo.
            EngineError: Si sudo tampoco puede leerlo.
        """
        prefix = self._prefix(privileged)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None
        except PermissionError:
            if not prefix:
                raise
        r = subprocess.run(
            [*prefix, "cat", "--", str(path)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        if r.returncode == 0:
            return r.stdout
        if not self.exists(path, privileged):
            return None
        raise EngineError(
            f"No se pudo leer {path}: {r.stderr.decode(errors='replace')}"
        )

    def install(self, data: bytes, dest: Path, mode: int, privileged: bool) -> None:
        """Escribe ``data`` en ``dest`` con ``install -D``.

        Args:
            data: Contenido.
            dest: Destino absoluto; se crean los directorios padre.
            mode: Permisos del fichero.
            privileged: Usar sudo.

        Raises:
            EngineError: Si ``install`` falla.
        """
        with _temp_file(data) as tmp:
            argv = [
                *self._prefix(privileged),
                "install",
                "-D",
                "-m",
                f"{mode:04o}",
                str(tmp),
                str(dest),
            ]
            r = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )
        if r.returncode != 0:
            raise EngineError(f"No se pudo escribir {dest}: {r.stderr.strip()}")


class Engine:
    """Aplica, comprueba y elimina entradas."""

    def __init__(
        self, config: Config, sink: Sink, sudo: list[str] | None = None
    ) -> None:
        """Crea el motor.

        Args:
            config: Configuración de la aplicación.
            sink: Destino de la salida.
            sudo: Prefijo privilegiado; ``None`` usa :func:`default_sudo`.
        """
        self.config = config
        self.sink = sink
        self.sudo = sudo
        self.on_step: Progress | None = None
        self._cancel = threading.Event()
        self._active: Runner | None = None

    # -- cancelación ----------------------------------------------------- #
    def cancel(self) -> None:
        """Pide detener la ejecución en curso.

        Termina el comando que se esté ejecutando y no empieza más pasos. Se
        puede llamar desde otro hilo.
        """
        self._cancel.set()
        if self._active is not None:
            self._active.terminate()

    @property
    def cancelled(self) -> bool:
        """``True`` si se ha pedido cancelar."""
        return self._cancel.is_set()

    def _stop_if_cancelled(self) -> bool:
        """Informa y devuelve ``True`` si hay que dejar de ejecutar pasos."""
        if self.cancelled:
            self.sink("warn", "Cancelado por el usuario")
        return self.cancelled

    def _notify_step(self, index: int, total: int, step: Step) -> None:
        """Avisa a ``on_step`` (barra de progreso de la TUI)."""
        if self.on_step is not None:
            self.on_step(index, total, step)

    # -- privilegios ----------------------------------------------------- #
    def _sudo_bypassed(self) -> bool:
        """``True`` si no hay sudo real (root, o prefijo sustituido)."""
        return os.geteuid() == 0 or self.sudo is not None or sudo_overridden()

    def password_needed(self, entry: Entry) -> bool:
        """Indica si hay que pedir la contraseña de sudo antes de aplicar.

        Args:
            entry: Entrada a aplicar.

        Returns:
            ``False`` si no necesita root, ya somos root o la credencial de
            sudo sigue en caché.
        """
        if not entry.requires_root or self._sudo_bypassed():
            return False
        if shutil.which("sudo") is None:
            return False  # acquire_root informará del error
        r = subprocess.run(
            ["sudo", "-n", "true"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        return r.returncode != 0

    def acquire_root(self) -> bool:
        """Pide la contraseña de sudo una vez (``sudo -v``, interactivo).

        Returns:
            ``True`` si hay privilegios disponibles.
        """
        if self._sudo_bypassed():
            return True
        if shutil.which("sudo") is None:
            self.sink("error", "Esta entrada necesita root y no hay sudo instalado")
            return False
        return subprocess.run(["sudo", "-v"], check=False).returncode == 0

    # -- entorno --------------------------------------------------------- #
    @staticmethod
    def _env(entry: Entry, values: dict[str, str], dry_run: bool) -> dict[str, str]:
        """Variables que reciben los pasos."""
        return {
            **values,
            "APPFORGE_ENTRY": entry.id,
            "APPFORGE_ENTRY_DIR": str(entry.files_dir),
            "APPFORGE_DRY_RUN": "1" if dry_run else "0",
        }

    def _runner(self, entry: Entry, values: dict[str, str]) -> Runner:
        """Runner que enmascara los parámetros secretos."""
        secrets = [values.get(p.name, "") for p in entry.params if p.secret]
        self._active = Runner(self.sink, secrets, self.sudo)
        return self._active

    # -- check ----------------------------------------------------------- #
    def is_applied(self, entry: Entry, timeout: float = 15) -> bool | None:
        """Ejecuta ``[check]``.

        Se ejecuta sin privilegios (para no pedir contraseña al pintar el
        menú) y con los valores por defecto de los parámetros.

        Args:
            entry: Entrada a comprobar.
            timeout: Segundos máximos.

        Returns:
            ``True``/``False`` según el código de salida, o ``None`` si no
            tiene ``[check]`` o es inválida.
        """
        if not entry.check or not entry.valid:
            return None
        values = {p.name: p.default or "" for p in entry.params}
        runner = Runner(_discard, [], self.sudo)
        rc = runner.shell(
            entry.check,
            self._env(entry, values, False),
            entry.files_dir,
            privileged=False,
            capture=True,
            timeout=timeout,
        )
        return rc == 0

    # -- pasos ----------------------------------------------------------- #
    @staticmethod
    def render(entry: Entry, step: Step, values: dict[str, str]) -> bytes:
        """Contenido final de un paso ``template`` o ``copy``.

        Args:
            entry: Entrada del paso.
            step: Paso de fichero.
            values: Valores de los parámetros.

        Returns:
            Los bytes a escribir.

        Raises:
            EngineError: Si la plantilla usa un parámetro sin valor.
        """
        src = entry.files_dir / step.value
        if step.kind != "template":
            return src.read_bytes()
        text = src.read_text(encoding="utf-8")
        try:
            return string.Template(text).substitute(values).encode("utf-8")
        except (KeyError, ValueError) as e:
            raise EngineError(f"Plantilla {step.value}: {e}") from e

    def _backup(self, entry: Entry, dest: Path, old: bytes, stamp: str) -> Path:
        """Guarda ``old`` en el directorio de copias (0600)."""
        rel = dest.relative_to(dest.anchor)
        target = self.config.backups_dir / entry.id / stamp / rel
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(old)
        return target

    def _show_diff(
        self, runner: Runner, dest: Path, old: bytes | None, new: bytes
    ) -> None:
        """Envía al sink el diff entre ``old`` y ``new``."""
        try:
            a = (old or b"").decode("utf-8").splitlines()
            b = new.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            self.sink("info", "(contenido binario)")
            return
        for line in difflib.unified_diff(
            a, b, str(dest), f"{dest} (nuevo)", lineterm=""
        ):
            self.sink("out", runner.mask(line))

    def _file_step(
        self,
        entry: Entry,
        step: Step,
        values: dict[str, str],
        runner: Runner,
        dry_run: bool,
        stamp: str,
    ) -> bool:
        """Ejecuta un paso ``template`` o ``copy``."""
        assert step.dest is not None
        dest = Path(step.dest)
        priv = entry.requires_root
        new = self.render(entry, step, values)
        try:
            old = runner.read(dest, priv and not dry_run)
        except PermissionError:
            old = None
            self.sink("warn", f"{dest}: no legible sin root, no puedo comparar")
        mode = step.mode
        if mode is None:
            try:
                mode = dest.stat().st_mode & 0o7777 if old is not None else 0o644
            except OSError:
                mode = 0o644

        if old == new:
            self.sink("info", f"{dest}: sin cambios")
            if not dry_run:
                runner.install(new, dest, mode, priv)  # asegura el modo
            return True
        if dry_run:
            action = "crear" if old is None else "modificar (con copia de seguridad)"
            self.sink("info", f"{action} {dest} (modo {mode:04o}, {len(new)} bytes)")
            if old is not None or step.kind == "template":
                self._show_diff(runner, dest, old, new)
            return True
        if old is not None:
            self.sink(
                "info", f"copia de seguridad: {self._backup(entry, dest, old, stamp)}"
            )
        runner.install(new, dest, mode, priv)
        self.sink("info", f"escrito {dest} ({mode:04o})")
        return True

    def _shell_step(
        self,
        entry: Entry,
        script: str,
        env: dict[str, str],
        runner: Runner,
        dry_run: bool,
        label: str,
    ) -> bool:
        """Ejecuta (o muestra, en dry-run) código bash."""
        priv = entry.requires_root
        if dry_run:
            sign = "#" if priv else "$"
            for line in script.strip().splitlines():
                self.sink("out", runner.mask(f"{sign} {line}"))
            return True
        rc = runner.shell(script, env, entry.files_dir, priv)
        if rc != 0:
            self.sink("error", f"{label} terminó con código {rc}")
            return False
        return True

    def _run_step(
        self,
        entry: Entry,
        step: Step,
        values: dict[str, str],
        runner: Runner,
        dry_run: bool,
        stamp: str,
    ) -> bool:
        """Despacha un paso según su tipo."""
        if step.kind in ("template", "copy"):
            return self._file_step(entry, step, values, runner, dry_run, stamp)
        env = self._env(entry, values, dry_run)
        script = step.value
        if step.kind == "script":
            script = f"bash {shlex.quote(str(entry.files_dir / step.value))}"
        return self._shell_step(entry, script, env, runner, dry_run, step.title)

    def _report_invalid(self, entry: Entry) -> bool:
        """Envía los problemas al sink; ``True`` si la entrada es inválida."""
        for problem in entry.problems:
            self.sink("error", problem)
        return not entry.valid

    # -- API ------------------------------------------------------------- #
    def apply(
        self, entry: Entry, values: dict[str, str], dry_run: bool = False
    ) -> bool:
        """Aplica una entrada paso a paso.

        Se detiene en el primer paso que falla. Al terminar vuelve a ejecutar
        ``[check]`` para verificar el resultado.

        Args:
            entry: Entrada a aplicar.
            values: Valores de los parámetros (se completan con los defaults).
            dry_run: Mostrar lo que se haría sin cambiar nada.

        Returns:
            ``True`` si todos los pasos terminan bien (y ``[check]`` pasa).

        Raises:
            EngineError: Si faltan parámetros o hay alguno desconocido.
        """
        if self._report_invalid(entry):
            return False
        values = resolve_values(entry, values)
        runner = self._runner(entry, values)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        tag = " [dry-run]" if dry_run else ""

        state = self.is_applied(entry)
        if state is not None:
            self.sink(
                "info", f"Estado actual: {'aplicada' if state else 'no aplicada'}"
            )

        total = len(entry.steps)
        for i, step in enumerate(entry.steps, 1):
            if self._stop_if_cancelled():
                return False
            self._notify_step(i, total, step)
            self.sink("step", f"[{i}/{total}] {step.title}{tag}")
            try:
                ok = self._run_step(entry, step, values, runner, dry_run, stamp)
            except EngineError as e:
                self.sink("error", str(e))
                ok = False
            if not ok and self._stop_if_cancelled():
                return False
            if not ok:
                self.sink(
                    "error",
                    f"Detenido en el paso {i}/{total}. La entrada puede quedar a "
                    "medias; corrige y vuelve a aplicar (los pasos son reejecutables).",
                )
                return False

        if dry_run:
            self.sink("ok", "Dry-run completado: no se ha cambiado nada")
            return True
        state = self.is_applied(entry)
        if state is False:
            self.sink("warn", "Pasos completados, pero [check] sigue fallando")
            return False
        self.sink("ok", "Entrada aplicada" + (" y verificada" if state else ""))
        return True

    def remove(self, entry: Entry, dry_run: bool = False) -> bool:
        """Ejecuta ``[remove]`` y verifica con ``[check]``.

        Args:
            entry: Entrada a eliminar.
            dry_run: Mostrar el comando sin ejecutarlo.

        Returns:
            ``True`` si se eliminó (o el dry-run terminó).
        """
        if self._report_invalid(entry):
            return False
        if not entry.remove:
            self.sink("error", "Esta entrada no define [remove]")
            return False
        if self._stop_if_cancelled():
            return False
        values = {p.name: p.default or "" for p in entry.params}
        runner = self._runner(entry, {})
        env = self._env(entry, values, dry_run)
        self._notify_step(
            1, 1, Step(title="Eliminar", kind="remove", value=entry.remove)
        )
        self.sink("step", "Eliminar" + (" [dry-run]" if dry_run else ""))
        if not self._shell_step(entry, entry.remove, env, runner, dry_run, "[remove]"):
            self._stop_if_cancelled()
            return False
        if dry_run:
            self.sink("ok", "Dry-run completado: no se ha cambiado nada")
            return True
        if self.is_applied(entry):
            self.sink("warn", "[remove] terminó, pero [check] sigue indicando aplicada")
            return False
        self.sink("ok", "Entrada eliminada")
        return True
