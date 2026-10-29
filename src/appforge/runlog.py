"""Registro de ejecuciones en fichero, con rotación diaria (``acodo.logger``)."""

from pathlib import Path

from acodo.logger import Logger

from appforge.config import APP_NAME, Config
from appforge.engine import Sink

LOG_FILE = f"{APP_NAME}.log"
TAGS = {
    "run": "run ",
    "script": "scr ",
    "template": "tpl ",
    "copy": "copy",
    "remove": "rm  ",
}
CHECK_TAG = "chk "


def step_tag(kind: str | None) -> str:
    """Etiqueta de 4 caracteres para un tipo de paso.

    Args:
        kind: Tipo de paso, o ``None`` antes del primer paso.

    Returns:
        La etiqueta, p. ej. ``"tpl "``.

    Examples:
        >>> step_tag("template")
        'tpl '
        >>> step_tag(None)
        'chk '
    """
    return TAGS.get(kind or "", CHECK_TAG)


class RunLog:
    """Escribe en ``<logs_dir>/appforge.log`` (7 días de histórico).

    Nunca escribe por consola: la salida visible la dan la CLI y la TUI.
    """

    def __init__(self, config: Config) -> None:
        """Abre el registro en el directorio de logs de ``config``.

        Args:
            config: Configuración de la aplicación.
        """
        self.path: Path = config.logs_dir / LOG_FILE
        # El nombre incluye la ruta: acodo reutiliza los loggers por nombre.
        self._log = Logger(f"{APP_NAME}.run:{self.path}", file=self.path)

    def write(self, kind: str, text: str) -> None:
        """Añade una línea con el nivel que corresponde a ``kind``.

        Args:
            kind: Tipo de evento del motor (``error``, ``warn``, …).
            text: Texto, ya sin secretos.
        """
        if kind == "error":
            self._log.error(text, console=False)
        elif kind == "warn":
            self._log.warning(text, console=False)
        else:
            self._log.info(text, console=False)

    def tee(self, sink: Sink, prefix: str = "") -> Sink:
        """Devuelve un sink que además escribe en el registro.

        Args:
            sink: Sink original.
            prefix: Texto que se antepone en el fichero (p. ej. el id).

        Returns:
            El sink combinado.
        """

        def both(kind: str, text: str) -> None:
            sink(kind, text)
            self.write(kind, f"{prefix}{text}")

        return both
