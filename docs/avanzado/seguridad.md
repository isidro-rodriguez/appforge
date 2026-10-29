# Seguridad

Una receta ejecuta comandos como `root`. AppForge las trata **como código**:
quien pueda editar una receta puede ejecutar lo que quiera en tu equipo. Por eso
desconfía por defecto.

## Qué rechaza

Una receta con cualquiera de estos problemas aparece como *inválida* y no se puede
aplicar:

| Comprobación | Por qué |
|---|---|
| El `.toml`, su carpeta o un fichero dentro son **escribibles por el grupo u otros** | Otro usuario podría inyectar comandos |
| Pertenecen a **otro usuario** que no es `root` | Ídem |
| Hay **enlaces simbólicos** en `entries/<id>/` | Podrían apuntar a ficheros fuera de la receta |
| Una ruta de origen es absoluta o contiene `..` | Los ficheros de una receta no salen de su carpeta |
| Un parámetro se llama `PATH`, `HOME`, `LD_PRELOAD`… o empieza por `APPFORGE_` | Sustituiría variables de las que dependen los comandos |
| Claves desconocidas o de tipo incorrecto | Una errata no debe cambiar el comportamiento en silencio |

El directorio de recetas entero se comprueba igual. Para arreglar permisos:

```bash
sudo chown -R root:root appforge/entries
sudo chmod -R go-w appforge/entries
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
