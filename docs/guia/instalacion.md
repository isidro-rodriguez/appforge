# Instalación

AppForge funciona en **Linux** (usa bash, `sudo` e `install`) y está pensado para
Debian y derivadas. Hay dos formas de usarlo: desde el código con `uv` o como un
binario autocontenido.

## Desde el código

Necesitas [uv](https://docs.astral.sh/uv/) y Python 3.13 o superior (uv lo descarga
si no lo tienes).

```bash
git clone https://github.com/isidro-rodriguez/appforge.git
cd appforge
uv sync
uv run appforge
```

`uv run appforge` busca `config.toml` en el directorio actual. Para usar otra carpeta
de recetas, apunta `APPFORGE_HOME` a ella:

```bash
APPFORGE_HOME=~/mis-recetas uv run appforge
```

## Binario autocontenido

Genera una carpeta lista para copiar a cualquier equipo:

```bash
uv run python scripts/build.py
```

```text
dist/appforge/
├── appforge        # binario (incluye Python y Textual)
├── appforge.png    # icono para el lanzador de escritorio
├── config.toml
└── entries/
```

El binario busca `config.toml` **junto a sí mismo**, así que la carpeta entera es
portable. Más detalles, y cómo añadirlo al menú de aplicaciones, en
[Empaquetado](../avanzado/empaquetado.md).

!!! warning "Permisos de las recetas"

    Las recetas ejecutan comandos, a veces como root. AppForge **rechaza** cualquier
    receta que puedan modificar otros usuarios (escribible por grupo u otros, o de
    otro propietario). Si copias la carpeta y una receta aparece como *inválida*:

    ```bash
    chmod -R go-w entries
    ```

## Requisitos de las recetas

Cada receta instala lo que necesita. La de ejemplo, [Ollama](ollama.md), usa `apt-get`
para `curl`, `zstd` y `libnotify-bin`.

## Siguiente paso

[Primeros pasos](primeros-pasos.md): un recorrido por la interfaz.
