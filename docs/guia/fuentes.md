# Receta incluida: fuentes adicionales

Instala, para todos los usuarios, las fuentes más pedidas en un escritorio Debian:

| Fuente | Origen |
|---|---|
| Microsoft core fonts (Arial, Times New Roman, Verdana…) | Paquete `ttf-mscorefonts-installer` (contrib) |
| Ubuntu | Paquete `fonts-ubuntu` |
| Fira Code | Paquete `fonts-firacode` |
| JetBrainsMono Nerd Font | [Nerd Fonts](https://www.nerdfonts.com), en `/usr/local/share/fonts/nerd-fonts/JetBrainsMono` |

## Antes de instalar

- La licencia (EULA) de las fuentes de Microsoft **se acepta automáticamente**; el
  paquete las descarga de los servidores de Microsoft al instalar.
- Si APT no tiene los componentes `contrib` o `non-free`, la receta añade solo los
  que faltan en `/etc/apt/sources.list.d/appforge-fonts.sources`, con el mismo espejo
  y la misma clave que `debian.sources`, que no se modifica.
- La Nerd Font se descarga de GitHub y se verifica con el `SHA-256.txt` de la versión;
  sin suma publicada, no se instala.

## Parámetros

| Parámetro | Por defecto | Uso |
|---|---|---|
| `nerd_version` | `v3.4.0` | Versión (etiqueta) de Nerd Fonts; el formulario enlaza a sus [Releases](https://github.com/ryanoasis/nerd-fonts/releases) |

## Desinstalar

Quita los tres paquetes, la Nerd Font y, si la receta lo creó,
`appforge-fonts.sources`. Después regenera la caché de fuentes.
