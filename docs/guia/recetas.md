# Recetas incluidas

El paquete trae estas recetas en `/opt/appforge/appforge-entries/`, una carpeta por
receta. La ficha completa de cada una (qué instala, qué conviene saber antes, sus
parámetros y qué deja al desinstalar) está en la TUI: resáltala y pulsa ++v++. Esta
página resume el conjunto y cómo combinarlas.

| Receta | Id | Categoría | Descripción | Parámetros |
|---|---|---|---|---|
| Git y GitHub CLI | `git` | Desarrollo | git, gh (repositorio oficial) y tu configuración global de git | `user_name`, `user_email`, `default_branch`, `editor`, `aliases` |
| Neovim (IDE de terminal) | `nvim` | Desarrollo | Neovim en /opt/nvim como vi y vim, configurado como IDE ligero con plugins de la comunidad | `version`, `ts_version`, `arch` |
| Fuentes adicionales | `fonts` | Escritorio | Fuentes de Microsoft, Ubuntu, Fira Code y JetBrainsMono Nerd Font | `nerd_version` |
| Ollama (bajo demanda) | `ollama` | IA | Ollama en /opt/ollama, sin servicio de arranque; lanzador on/off con notificación | `version`, `arch`, `host`, `keep_alive`, `kv_cache`, `context_length` |
| Cortafuegos (ufw) | `firewall` | Red | ufw activo: entrada denegada, salida permitida, con las excepciones que indiques | `allow`, `allow_from` |
| Servidor SSH (endurecido) | `ssh-server` | Red | OpenSSH con acceso solo para tu usuario, sin root y, por defecto, solo con claves | `port`, `password_auth` |
| Alias de bash | `bash-aliases` | Sistema | ~/.bash_aliases modular: atajos de shell y, opcional, ls con eza | `eza`, `eza_icons` |
| Docker Engine | `docker` | Virtualización | Docker CE desde el repositorio oficial de Docker, con Buildx y Compose | — |
| Incus (contenedores y VM) | `incus` | Virtualización | Incus de Debian 13 inicializado, con tu usuario en incus-admin y la red abierta en ufw | `vms` |

Las recetas que tocan ficheros de usuario (Git, alias de bash, grupos de Incus y
Docker) usan el usuario que lanzó `sudo /opt/appforge/appforge`, no `root`.

## Repositorios de terceros

Docker y GitHub CLI se instalan desde sus repositorios APT oficiales con el mismo
patrón: la clave se descarga a `/etc/apt/keyrings/`, **se comprueba su huella** y el
repositorio se declara en un `.sources` (deb822) con `Signed-By`, de modo que esa
clave solo vale para ese repositorio. Desinstalar quita paquete, repositorio y clave.

## Combinarlas

| Situación | Qué hacer |
|---|---|
| Administras la máquina por SSH y vas a activar el cortafuegos | Añade `22/tcp` (o tu puerto) a las excepciones del **Cortafuegos**: al activarse corta lo que no esté permitido. **Servidor SSH**, aplicado después, abre su puerto si ufw está activo |
| Cortafuegos + Incus | Aplica primero el **Cortafuegos**: Incus añade las reglas de `incusbr0` solo si ufw está instalado. Sin ellas, las instancias no tienen red |
| Docker + ufw | Docker publica puertos saltándose ufw: usa `127.0.0.1:8080:80` para servicios locales |
| Docker + Incus en la misma máquina | Docker deja sin red a las instancias de Incus (política `FORWARD`). Evítalo o sigue la [guía de Incus](https://linuxcontainers.org/incus/docs/main/howto/network_bridge_firewalld/) |
| Servidor SSH solo con claves | Copia antes tu clave pública (`ssh-copy-id` desde el otro equipo): la receta falla, sin tocar nada, si no hay `~/.ssh/authorized_keys` |
| Grupos `docker` e `incus-admin` | Cierra sesión y vuelve a entrar para usarlos sin `sudo`. Pertenecer a `docker` equivale a ser root |
| Después de **Git y GitHub CLI** | Ejecuta `gh auth login` como tu usuario: la receta no inicia sesión |
| **Alias de bash** con iconos de eza | Aplica **Fuentes adicionales** (incluye JetBrainsMono Nerd Font) y elígela en las preferencias del terminal: ninguna receta lo configura |
| Alias de git | Están en **Git y GitHub CLI** (`git st`, `git lg`…), no en **Alias de bash** |

Si seleccionas varias, se aplican en el orden de la lista (alfabético), que ya pone
el **Cortafuegos** antes que **Incus** y **Servidor SSH**.

## Lo que se conserva al desinstalar

| Receta | Conserva |
|---|---|
| Cortafuegos | ufw instalado y sus reglas (solo `ufw disable`) |
| Servidor SSH | OpenSSH y la regla de ufw (borra `50-appforge.conf`) |
| Incus | Incus, instancias, imágenes y almacenamiento |
| Docker | `/var/lib/docker` (imágenes, contenedores, volúmenes) y `/etc/docker` |
| Git | `git` y tu `~/.gitconfig` |
| Alias de bash | `eza`, tus fragmentos de `~/.bash_aliases.d/` y lo que hayas cambiado; si no, restaura el `.backup` |
