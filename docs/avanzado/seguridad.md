# Seguridad

Una receta ejecuta comandos como `root`. AppForge las trata **como código**:
quien pueda editar una receta puede ejecutar lo que quiera en tu equipo. Por eso
desconfía por defecto.

## Modelo de confianza

- **AppForge no es un sandbox.** Una receta es código que se ejecuta como `root`, con
  todo el acceso al sistema.
- Las comprobaciones de abajo protegen la **integridad del catálogo** (que nadie sin
  permiso cambie una receta), no hacen fiable una receta por sí misma.
- Ejecutar AppForge equivale a ser `root`. **No permitas `sudo appforge` en
  `sudoers` a usuarios que no deban tener `root`:** quien lo lance puede usar sus
  propias recetas.

| Uso | Dónde están las recetas | Quién puede cambiarlas |
|---|---|---|
| **Instalación del paquete** (normal) | `/etc/appforge/entries/` | Solo `root` |
| **Desarrollo** (desde el código) | `entries/` de tu copia del repositorio | Tú, que ya ejecutas con `sudo` |

## Qué rechaza

Una receta con cualquiera de estos problemas aparece como *inválida* y no se puede
aplicar:

| Comprobación | Por qué |
|---|---|
| El `.toml`, su carpeta o un fichero dentro son **escribibles por el grupo u otros** | Otro usuario podría inyectar comandos |
| Pertenecen a **otro usuario** que no es `root` ni quien ejecutó `sudo` | Ídem |
| Hay **enlaces simbólicos** en `entries/<id>/` | Podrían apuntar a ficheros fuera de la receta |
| Una ruta de origen es absoluta o contiene `..` | Los ficheros de una receta no salen de su carpeta |
| Un parámetro se llama `PATH`, `HOME`, `LD_PRELOAD`… o empieza por `APPFORGE_` | Sustituiría variables de las que dependen los comandos |
| Claves desconocidas o de tipo incorrecto | Una errata no debe cambiar el comportamiento en silencio |

El directorio de recetas entero y `config.toml` se comprueban igual (este, además,
no puede ser un enlace). Para arreglar permisos:

```bash
sudo chown -R root:root /etc/appforge
sudo chmod -R go-w /etc/appforge
```

## Qué garantiza al ejecutar

- AppForge solo arranca como superusuario: no maneja contraseñas ni mezcla pasos con
  y sin privilegios.
- Los parámetros no aparecen en la lista de procesos y los secretos se enmascaran
  en pantalla, registro y diffs.
- Antes de sobrescribir un fichero se guarda una copia (`<fichero>.backup`, con sus
  mismos permisos) y queda anotada en el registro.
- El *dry-run* enseña todo antes de cambiar nada.

## Qué no puede garantizar

AppForge no analiza lo que hacen los comandos de una receta. Antes de aplicar una
receta que no has escrito tú:

1. Ábrela en la [página de detalle](../guia/interfaz.md#página-de-detalle) y pásale
   `appforge validate <id>`.
2. Haz un *dry-run* (++d++ en la TUI).
3. Desconfía de descargas que se ejecutan directamente (`curl … | bash`).

Para escribir recetas seguras, ver [buenas prácticas](../desarrollo/buenas-practicas.md).

## Verificar el paquete

Cada Release publica el `.deb`, su suma en `SHA256SUMS` y una **atestación de
procedencia** de GitHub: prueba que el paquete se construyó en el workflow de este
repositorio a partir de un commit concreto.

```bash
sha256sum -c SHA256SUMS
gh attestation verify appforge_<versión>_amd64.deb --repo isidro-rodriguez/appforge
```

## Descargas de las recetas

Las recetas que descargan software lo hacen de una **versión fija**, elegida con un
parámetro que enlaza a las versiones publicadas, y **verifican su SHA-256** con las
sumas oficiales de esa versión; sin suma publicada no instalan nada. Ver
[buenas prácticas](../desarrollo/buenas-practicas.md).
