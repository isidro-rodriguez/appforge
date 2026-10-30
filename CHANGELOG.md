# Changelog

Todos los cambios relevantes de `appforge` se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

## [0.12.2] - 2026-10-30

### Fixed

- `scripts/try-entry.sh` se detiene si el paquete de `dist/` es de otra versión que el
  código (antes probaba la receta con un AppForge antiguo, que rechazaba claves nuevas
  como `type` o `choices`) y avisa si `src/` cambió después de construirlo.
- En los diálogos, ++tab++ y ++shift+tab++ pasan de un campo a otro (la tecla
  estaba reservada al catálogo y no hacía nada); el formulario empieza en el primer
  campo.

### Changed

- `scripts/try-entry.sh` sin receta abre la TUI en la máquina de prueba con las
  recetas del paquete.

## [0.12.1] - 2026-10-30

### Changed

- Requiere `acodo>=0.4`, que trae `valid_cidr`, `valid_int` y `valid_path`.

## [0.12.0] - 2026-10-30

### Added

- Parámetros con tipo: `type` (`bool`, `int`, `port`, `email`, `path`, `ip`, `url`,
  `domain`) y `choices` (valores fijos). La TUI muestra una casilla, un desplegable o
  un campo que se marca en rojo y no deja aceptar un valor no válido; el motor lo
  vuelve a comprobar y `appforge validate` revisa los `default`. Un `bool` llega a los
  pasos como `yes`/`no`.

### Changed

- Las recetas incluidas usan tipos: puerto y contraseña de SSH, email de Git,
  arquitectura y caché K/V de Ollama y Neovim, contexto de Ollama y VM de Incus.

## [0.11.0] - 2026-10-30

### Changed

- **Incompatible:** cada receta es una carpeta `<id>/` con `entry.toml` (la receta),
  `details.md` (su ficha, obligatoria) y los ficheros de sus pasos. La clave `details`
  ya no existe en el TOML. Las recetas en el formato anterior (`<id>.toml` suelto) se
  ignoran y `appforge validate` avisa de cómo moverlas; revisa tu `custom-entries/`.
- Para sustituir una receta de ejemplo basta copiar su carpeta a `custom-entries/`.
- `scripts/try-entry.sh` recibe el id o la ruta a la carpeta de la receta.
- Documentación: la portada usa la receta del servidor SSH en los tres pasos de
  «Cómo funciona» y la parrilla de tarjetas queda alineada. Las capturas solo
  muestran recetas reales (el progreso es un *dry-run*).
- Documentación: una sola página «Recetas incluidas»; la información de Ollama,
  Neovim y fuentes pasa a la ficha de cada receta. Un test comprueba que la tabla
  de esa página coincide con las recetas.

## [0.10.0] - 2026-10-30

### Added

- Receta **Cortafuegos (ufw)** (`firewall`): entrada denegada y salida permitida, con excepciones y una red de confianza validadas antes de cambiar nada.
- Receta **Servidor SSH (endurecido)** (`ssh-server`): OpenSSH con `50-appforge.conf` en `sshd_config.d`, validado con `sshd -t`; no se aplica sin claves autorizadas si se desactiva la contraseña. Abre su puerto en ufw si está activo.
- Receta **Incus (contenedores y VM)** (`incus`): paquete de Debian 13 (con QEMU y OVMF opcionales), `incus admin init --minimal` si hace falta, usuario en `incus-admin` y reglas de ufw para `incusbr0`.
- Receta **Docker Engine** (`docker`): repositorio APT oficial con clave de huella verificada y `.sources` deb822 con `Signed-By`; usuario en el grupo `docker`. Desinstalar conserva `/var/lib/docker`.
- Receta **Git y GitHub CLI** (`git`): `gh` desde su repositorio APT oficial (clave verificada), configuración global de git del usuario y `gh` como gestor de credenciales.
- Receta **Alias de bash** (`bash-aliases`): `~/.bash_aliases` con atajos para listados, apt y systemd; guarda el anterior en `.backup` y lo restaura al desinstalar.

### Changed

- Los diálogos (parámetros y confirmación) usan el fondo y el borde de los paneles;
  los botones secundarios ya no se confunden con el fondo y el foco se marca con el
  color de acento.
- Documentación: página «Recetas incluidas» con el catálogo, cómo combinarlas
  (cortafuegos, SSH, Incus y Docker) y qué conserva cada una al desinstalar.

## [0.9.0] - 2026-10-30

### Added

- `appforge update`: actualiza AppForge desde la última Release de GitHub (o desde un
  `.tar.gz` con `--from`), verificando `SHA256SUMS`. Conserva tu `config.toml` y las
  recetas que hayas modificado (la versión nueva queda en `<fichero>.new`), no recrea
  las que borraste y no toca `custom-entries/` ni `logs/`. Con `--dry-run` solo
  muestra el plan; `--force` reinstala la misma versión.
- `entries_dirs` en `config.toml`: varios directorios de recetas; si dos traen el
  mismo id, gana el último. `appforge validate` lo avisa y admite `--dir` repetido.

### Changed

- El paquete trae `appforge-entries/` (recetas de ejemplo), `custom-entries/` (las
  tuyas, vacío) y `.manifest.json` (sumas de cada fichero, para `update`).
- **Incompatible:** `entries_dir` pasa a ser `entries_dirs` (lista). Una instalación
  0.8.0 se reinstala a mano.
- `scripts/try-entry.sh` sube la receta a `custom-entries/`.

## [0.8.0] - 2026-10-30

### Added

- Receta **Neovim (IDE de terminal)**: Neovim en `/opt/nvim` (versión fija,
  verificada con el SHA-256 de la Release de GitHub) en lugar de `vi` y `vim`, con
  una configuración de IDE ligero (`vim.pack`, LSP con Mason, tree-sitter,
  autocompletado, buscador, git y formateo) y su página «Receta incluida: Neovim».
- `scripts/try-entry.sh`: prueba una receta en una VM o contenedor desechable con
  incus, en Debian 13 u otra distro, y su página «Probar una receta».

### Changed

- Vuelve el paquete `.tar.gz` que se extrae en `/opt/appforge`: todo en una carpeta
  (programa, `config.toml`, `entries/` y el registro en `logs/`). El binario encuentra
  su configuración aunque se lance desde un enlace. La Release se prueba extraída en
  un Debian 13 limpio y publica `SHA256SUMS` y su procedencia.
- `scripts/try-entry.sh` usa ese paquete (`--tar` en lugar de `--deb`).

### Removed

- Paquete `.deb`, con su configuración en `/etc/appforge` y su registro en
  `/var/log/appforge`: repartía la aplicación por el sistema y la hacía más opaca.
- Página `man appforge`, lanzador de escritorio e iconos instalados.

## [0.7.0] - 2026-10-29

### Added

- Paquete **`.deb`** como forma de distribución: binario en `/opt/appforge` con
  enlace en `/usr/bin/appforge`, configuración y recetas en `/etc/appforge` (se
  conservan tus cambios al actualizar), registro en `/var/log/appforge`, página
  `man appforge`, lanzador en el menú de aplicaciones (abre una terminal con `sudo`)
  e iconos. Cada Release se prueba en un Debian 13 limpio y publica `SHA256SUMS` y
  la procedencia del paquete (`gh attestation verify`).
- Clave opcional `link` en `[[param]]`: la TUI la muestra bajo la pregunta y la
  página de detalle la enlaza.
- Desde el código, `uv run appforge` sin root pide la contraseña de `sudo` y se
  relanza.
- Documentación del modelo de confianza (AppForge no es un sandbox) y de los fallos
  parciales.

### Changed

- Ollama se instala de una **versión fija** (parámetro `version`, `v0.40.13` por
  defecto, con enlace a sus Releases) y se verifica con su `sha256sum.txt` oficial;
  sin suma no se instala. Si esa versión ya está instalada no se descarga de nuevo.
- La Nerd Font de la receta de fuentes exige su `SHA-256.txt` y su parámetro enlaza a
  las Releases de Nerd Fonts.
- `config.toml` se rechaza si es un enlace simbólico o lo pueden modificar otros.

### Removed

- Paquete `.tar.gz` y `scripts/build.py --archive`: lo sustituye el `.deb`.

## [0.6.1] - 2026-10-29

### Changed

- Se aceptan las entradas cuyo propietario es quien ejecutó `sudo` (`SUDO_UID`),
  además de `root`: el paquete se puede descomprimir sin `sudo`. Siguen rechazándose
  las de otros usuarios y las escribibles por grupo u otros.
- `appforge validate` ya no exige superusuario: solo lee ficheros. La TUI sí.
- La documentación ya no tiene página de instalación: Primeros pasos indica
  descargar y descomprimir el paquete.

## [0.6.0] - 2026-10-29

### Added

- Entrada `fonts`: fuentes de Microsoft, Ubuntu, Fira Code y JetBrainsMono Nerd Font
  para todos los usuarios. Añade `contrib`/`non-free` a APT solo si faltan, en un
  fichero propio, y verifica la Nerd Font con su `SHA-256.txt`. Probada de principio
  a fin en Debian 13.
- Variables `APPFORGE_USER` y `APPFORGE_USER_HOME` (quien ejecutó `sudo appforge`) en
  los pasos, `[check]`, `[remove]` y las plantillas, para los ficheros que deben ser
  del usuario. La confirmación de la TUI muestra ese usuario.

### Changed

- La entrada `ollama` ya no pide `owner`: la carpeta de modelos es del usuario que
  ejecutó `sudo appforge`.

### Removed

- Entrada de ejemplo `git-alias`.

## [0.5.0] - 2026-10-29

### Changed

- AppForge **solo se ejecuta como superusuario**: la TUI y `validate` salen con un
  error claro (y el comando con `sudo` para repetirlo) si no. `--help` y `--version`
  funcionan para cualquiera.
- Todo (pasos, `[check]` y `[remove]`) se ejecuta como `root`: desaparecen el manejo
  de `sudo`, la petición de contraseña a mitad de lote y las etiquetas `root`/`user`
  del catálogo.
- La copia de seguridad de un fichero que `template` o `copy` sobrescribe se guarda
  junto al original como `<fichero>.backup`, con sus mismos permisos, y reemplaza la
  copia anterior. Queda anotada en el registro.
- El registro de ejecuciones está en `logs/appforge.log`, junto al binario.
- La entrada de ejemplo `git-alias` configura los alias para todo el sistema
  (`/etc/gitconfig`).
- Documentación de usuario centrada en el binario empaquetado; `uv` y la ejecución
  desde el código pasan a la sección de desarrollo. Empaquetado se mueve allí.

### Removed

- Clave `requires_root` de las entradas (ahora es una clave desconocida).
  **Incompatible.**
- Clave `backups_dir` de `config.toml` y variables de entorno `APPFORGE_HOME`,
  `APPFORGE_SUDO` y `XDG_STATE_HOME`: `config.toml` se lee siempre junto al binario.

## [0.4.0] - 2026-10-29

### Added

- `appforge validate [ID...] [--dir DIR] [--strict]`: revisa las entradas sin
  ejecutarlas. Detecta errores de sintaxis de bash, referencias
  `$APPFORGE_ENTRY_DIR/...` a ficheros que no existen, ficheros y parámetros sin usar,
  entradas sin `description`, `[check]` o `[remove]`, nombres repetidos y
  subdirectorios sin su `.toml`. La CI lo ejecuta con `--strict`.
- Paquete `appforge-<versión>-linux-x86_64.tar.gz` (binario, `config.toml` y
  entradas de ejemplo, con su `.sha256`) publicado en una Release de GitHub con cada
  etiqueta `vX.Y.Z`; se compila en Debian 13, la estable actual.
  `scripts/build.py --archive` lo genera en local.
- Entrada de ejemplo `git-alias` (sin root).
- Capturas de la línea de comandos en la documentación.

### Changed

- La CLI pasa a [Typer](https://typer.tiangolo.com/), con la ayuda en español y los
  colores de AppForge.
- La documentación, los ejemplos y los tests usan valores genéricos (`usuario`) en
  lugar de datos personales.

### Removed

- Subcomandos `list`, `show`, `check`, `apply` y `remove`: repetían lo que ya hace la
  TUI, que también funciona en consola. **Incompatible** con scripts que los usaran.

## [0.3.0] - 2026-10-29

### Added

- Página de detalle de cada entrada (doble clic o `v`) con la descripción larga, los
  parámetros, cada paso con su comando o destino, `[check]` y `[remove]`, para saber
  exactamente qué hará antes de instalar.
- Clave opcional `details` (Markdown) en las entradas; la de Ollama la usa.
- Sitio de documentación con Zensical y el tema de la aplicación: portada, guía de
  uso con capturas, uso avanzado, sección para desarrolladores con tutorial de
  recetas y referencia de la API.
- Publicación automática del sitio en GitHub Pages.
- `scripts/screenshots.py` para regenerar las capturas de la TUI.

### Changed

- Un clic simple en la lista solo resalta la entrada; se marca con espacio o Enter.

### Fixed

- La TUI ya no se cierra con `NoMatches` al borrar en el buscador mientras termina
  una comprobación en segundo plano.

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
