# Changelog

Todos los cambios relevantes de `appforge` se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

## [0.2.0] - 2026-10-29

### Added

- Icono de AppForge optimizado en `src/appforge/resources/` (32–512 px) y copiado junto
  al binario por `scripts/build.py`, para usarlo en un lanzador de escritorio.
- Tema común para TUI y CLI sacado de los colores del icono (`theme.py`).
- Nueva TUI: catálogo con casillas y selección múltiple, panel de detalle con las
  seleccionadas, instalación y desinstalación por lotes y pantalla de progreso con barra,
  registro en vivo y cancelación con `ctrl+c`.
- Buscador y panel de categorías opcionales (`[ui]` en `config.toml`) y clave `category`
  en las entradas.
- Registro de ejecuciones en `~/.local/state/appforge/logs/appforge.log` con rotación
  diaria (`acodo.logger`).
- Icono de la entrada `ollama` incluido.

### Changed

- La CLI usa Rich con el tema de AppForge (respeta `NO_COLOR`).
- Los pasos se ejecutan en un grupo de procesos propio para que cancelar termine también
  sus subprocesos.
- `Enter` en la lista marca la entrada en lugar de aplicarla; `i` instala.

## [0.1.0] - 2026-10-29

### Added

- Motor de recetas: entradas TOML con parámetros, `[check]`, pasos `run`, `script`,
  `template` y `copy`, y `[remove]` opcional.
- Ejecución con `sudo` pedido una sola vez, copias de seguridad antes de sobrescribir,
  enmascarado de secretos y dry-run con diff de cada fichero.
- Validación estricta de entradas (claves, tipos, rutas, plantillas y permisos), para
  tratar las entradas como código.
- CLI (`list`, `show`, `check`, `apply`, `remove`) y TUI con Textual.
- Empaquetado en un único binario con PyInstaller (`scripts/build.py`).
- Entrada de ejemplo `ollama`: instalación en `/opt/ollama` bajo demanda con lanzador
  on/off y notificaciones.
- Proyecto basado en `acodo-template` (uv, ruff, ty, pytest, pre-commit, CI).
