# Recetas incluidas

El paquete trae estas recetas en `/opt/appforge/appforge-entries/`. Cada una explica
en su [página de detalle](interfaz.md) qué instala, qué pregunta y qué deja al
desinstalar; esta página resume el conjunto y cómo combinarlas.

| Receta | Categoría | Qué hace | Parámetros |
|---|---|---|---|
| [Ollama (bajo demanda)](ollama.md) | IA | Ollama en `/opt/ollama` con versión fija verificada y lanzador on/off | Versión, arquitectura, `OLLAMA_*` |
| [Fuentes adicionales](fuentes.md) | Escritorio | Microsoft core fonts, Ubuntu, Fira Code y JetBrainsMono Nerd Font | Versión de Nerd Fonts |
| [Neovim (IDE de terminal)](nvim.md) | Desarrollo | Neovim en `/opt/nvim` con configuración de IDE ligero | Versión |
| Git y GitHub CLI | Desarrollo | `git`, `gh` (repositorio oficial) y tu `~/.gitconfig` | Nombre, email, rama inicial, editor |
| Cortafuegos (ufw) | Red | Entrada denegada y salida permitida, con excepciones | Excepciones, red de confianza |
| Servidor SSH (endurecido) | Red | OpenSSH solo para tu usuario, sin root y, por defecto, solo con claves | Puerto, contraseña sí/no |
| Incus (contenedores y VM) | Virtualización | Incus de Debian inicializado, tu usuario en `incus-admin` | Soporte de VM |
| Docker Engine | Virtualización | Docker CE con Buildx y Compose desde el repositorio oficial | — |
| Alias de bash | Sistema | `~/.bash_aliases` con atajos para listados, apt y systemd | — |

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
| Alias de bash | Tu `~/.bash_aliases` si lo cambiaste; si no, restaura el `.backup` |
