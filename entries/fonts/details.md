Instala para todos los usuarios:

| Fuente | Origen |
|---|---|
| Microsoft core fonts (Arial, Times New Roman, Verdana…) | Paquete `ttf-mscorefonts-installer` (contrib) |
| Ubuntu | Paquete `fonts-ubuntu` |
| Fira Code | Paquete `fonts-firacode` |
| JetBrainsMono Nerd Font | [Nerd Fonts](https://www.nerdfonts.com) en GitHub, en `/usr/local/share/fonts/nerd-fonts/` |

### Antes de instalar

- Las fuentes de Microsoft se descargan de sus servidores al instalar y su licencia
  (EULA) **se acepta automáticamente**.
- Si `contrib` o `non-free` no están en tus fuentes de APT, se añaden en
  `/etc/apt/sources.list.d/appforge-fonts.sources` (no se toca `debian.sources`).
- La versión de Nerd Fonts es un parámetro. La descarga se verifica con el
  `SHA-256.txt` de esa versión; sin suma publicada no se instala.

Desinstalar quita los paquetes, la Nerd Font y el fichero de fuentes de APT.
