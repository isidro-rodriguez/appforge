# Instalación

AppForge funciona en **Linux** (usa bash, `sudo` e `install`) y está pensado para
Debian y derivadas. Hay dos formas de usarlo: el paquete con el binario ya
compilado o desde el código con `uv`.

## Paquete con el binario

Cada versión publica en **Releases** del repositorio un
`appforge-<versión>-linux-x86_64.tar.gz` con todo lo necesario:

```text
appforge/
├── appforge        # binario (incluye Python y Textual)
├── appforge.png    # icono para el lanzador de escritorio
├── config.toml
└── entries/        # recetas de ejemplo (Ollama, alias de git)
```

```bash
sha256sum -c appforge-<versión>-linux-x86_64.tar.gz.sha256   # opcional
tar -xzf appforge-<versión>-linux-x86_64.tar.gz -C ~/.local/opt
~/.local/opt/appforge/appforge
```

El binario se compila en Debian 12, así que funciona en Debian 12, 13 y
distribuciones más nuevas. Busca `config.toml` **junto a sí mismo**: la carpeta entera
es portable.

## Desde el código

Necesitas [uv](https://docs.astral.sh/uv/) y Python 3.13 o superior (uv lo descarga
si no lo tienes).

```bash
git clone https://github.com/<usuario>/appforge.git
cd appforge
uv sync
uv run appforge
```

`uv run appforge` busca `config.toml` en el directorio actual. Para usar otra carpeta
de recetas, apunta `APPFORGE_HOME` a ella:

```bash
APPFORGE_HOME=~/mis-recetas uv run appforge
```

## Compilar el binario

`uv run python scripts/build.py` deja la misma carpeta en `dist/appforge/`. Más
detalles, y cómo añadirlo al menú de aplicaciones, en
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
