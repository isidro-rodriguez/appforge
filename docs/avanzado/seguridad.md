# Seguridad

Una receta ejecuta comandos, a menudo como root. AppForge las trata **como código**:
quien pueda editar una receta puede ejecutar lo que quiera en tu equipo. Por eso
desconfía por defecto.

## Qué rechaza

Una receta con cualquiera de estos problemas aparece como *inválida* y no se puede
aplicar:

| Comprobación | Por qué |
|---|---|
| El `.toml`, su carpeta o un fichero dentro son **escribibles por el grupo u otros** | Otro usuario podría inyectar comandos |
| Pertenecen a **otro usuario** que no es root | Ídem |
| Hay **enlaces simbólicos** en `entries/<id>/` | Podrían apuntar a ficheros fuera de la receta |
| Una ruta de origen es absoluta o contiene `..` | Los ficheros de una receta no salen de su carpeta |
| Un parámetro se llama `PATH`, `HOME`, `LD_PRELOAD`… o empieza por `APPFORGE_` | Sustituiría variables de las que dependen los comandos |
| Claves desconocidas o de tipo incorrecto | Una errata no debe cambiar el comportamiento en silencio |

El directorio de recetas entero se comprueba igual. Para arreglar permisos:

```bash
chmod -R go-w entries
```

## Qué garantiza al ejecutar

- La contraseña la pide `sudo`, nunca AppForge, y solo una vez por lote.
- `[check]` nunca se ejecuta con root.
- Los parámetros no aparecen en la lista de procesos y los secretos se enmascaran
  en pantalla, registro y diffs.
- Antes de sobrescribir un fichero se guarda una copia (`0600`).
- El *dry-run* enseña todo antes de cambiar nada.

## Qué no puede garantizar

AppForge no analiza lo que hacen los comandos de una receta. Antes de aplicar una
receta que no has escrito tú:

1. Ábrela en la [página de detalle](../guia/interfaz.md#página-de-detalle) o con
   `appforge show <id>`.
2. Haz un *dry-run* (++d++ o `appforge apply <id> -n`).
3. Desconfía de descargas que se ejecutan directamente (`curl … | bash`).

Para escribir recetas seguras, ver [buenas prácticas](../desarrollo/buenas-practicas.md).
