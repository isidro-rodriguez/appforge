# Instalación

AppForge es un binario autocontenido para **Debian 13**. Se distribuye como un
paquete `.tar.gz` con todo lo necesario.

## Descarga

En [Releases](https://github.com/isidro-rodriguez/appforge/releases) descarga
`appforge-<versión>-linux-x86_64.tar.gz` y su `.sha256`:

```text
appforge/
├── appforge        # binario (incluye Python y Textual)
├── appforge.png    # icono para el lanzador de escritorio
├── config.toml     # configuración
└── entries/        # recetas de ejemplo (Ollama, fuentes adicionales)
```

## Instalar

```bash
sha256sum -c appforge-<versión>-linux-x86_64.tar.gz.sha256
sudo tar -xzf appforge-<versión>-linux-x86_64.tar.gz -C /opt
```

Queda en `/opt/appforge/`. La carpeta es portable: el binario busca `config.toml`
**junto a sí mismo**, así que puedes ponerla en otro sitio.

!!! warning "Extrae como superusuario"

    AppForge solo carga recetas que no puede modificar otro usuario: deben ser de
    `root` y no escribibles por grupo ni otros. `sudo tar` las deja así. Si alguna
    aparece como *inválida* por sus permisos:

    ```bash
    sudo chown -R root:root /opt/appforge
    sudo chmod -R go-w /opt/appforge/entries
    ```

## Ejecutar

AppForge instala y configura software del sistema, así que **solo funciona como
superusuario**:

```bash
sudo /opt/appforge/appforge
```

Sin `sudo` sale con un aviso y el comando exacto para repetirlo. Para no escribir la
ruta cada vez:

```bash
sudo ln -s /opt/appforge/appforge /usr/local/bin/appforge
sudo appforge
```

## Lanzador de escritorio

Para tener AppForge en el menú de aplicaciones, crea un lanzador que abra una
terminal y pida la contraseña de `sudo`:

```ini title="/usr/local/share/applications/appforge.desktop"
[Desktop Entry]
Type=Application
Name=AppForge
Comment=Recetas de configuración
Exec=sudo /opt/appforge/appforge
Icon=/opt/appforge/appforge.png
Terminal=true
Categories=System;Utility;
```

## Requisitos de las recetas

Cada receta instala lo que necesita. La de [Ollama](ollama.md) usa `apt-get` para
`curl`, `zstd` y `libnotify-bin`.

## Siguiente paso

[Primeros pasos](primeros-pasos.md): un recorrido por la interfaz.
