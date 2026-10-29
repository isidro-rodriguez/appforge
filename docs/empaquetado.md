# Empaquetado y distribución

## Binario

```bash
uv run python scripts/build.py      # o: poe build
```

Genera con [PyInstaller](https://pyinstaller.org/) `--onefile`:

```text
dist/appforge/
├── appforge        # binario (~43 MB, incluye Python y Textual)
├── config.toml
└── entries/
```

La carpeta completa se puede copiar a cualquier sitio: el binario busca `config.toml`
junto a sí mismo. El script quita la escritura de grupo y otros, porque AppForge rechaza
entradas inseguras.

## Notas

| Tema | Detalle |
|---|---|
| glibc | Compila en la distro más antigua donde vaya a ejecutarse: el binario enlaza con la glibc del sistema de compilación |
| Textual | Importa sus widgets de forma perezosa; por eso el build usa `--collect-submodules textual` y `--collect-data textual` |
| Intermedios | En `build/` (ignorado por git) |
| Sin binario | `uv run appforge` con `APPFORGE_HOME` apuntando a la carpeta con `config.toml` |

## Ejecutar desde el código

```bash
uv sync
uv run appforge                     # usa ./config.toml
APPFORGE_HOME=/ruta uv run appforge # otra carpeta
```
