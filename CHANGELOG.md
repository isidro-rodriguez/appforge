# Changelog

Todos los cambios relevantes de `appforge` se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

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
