# Solución de problemas

Mensajes habituales, su causa y qué hacer.

`appforge: No existe …/config.toml`
:   AppForge no encuentra su configuración en el [directorio base](configuracion.md#dónde-busca-appforge-su-configuración).
    Ejecútalo desde la carpeta que tiene `config.toml` o define `APPFORGE_HOME`.

`El directorio de entradas no existe: …`
:   `entries_dir` apunta a una carpeta que no existe. Es relativo al directorio base.

`claves desconocidas en [ui]: …` / `[ui].search debe ser true/false`
:   Errata o tipo incorrecto en `config.toml`. Los valores booleanos van sin comillas.

Una receta aparece como `inválida`
:   Su ficha (o `appforge show <id>`) dice por qué. La causa más frecuente son los
    permisos: `… escribible por grupo u otros (-rw-rw-r--)`. Arréglalo con
    `chmod -R go-w entries`. Ver [seguridad](seguridad.md).

`falta el fichero <id>/<fichero>`
:   Un paso `template`, `copy` o `script` usa un fichero que no está en
    `entries/<id>/`.

`la plantilla usa parámetros inexistentes: …`
:   La plantilla tiene `$nombre` sin el `[[param]]` correspondiente. Si es un `$`
    literal (por ejemplo, en un script de shell), escríbelo `$$` o usa `copy`.

`Faltan parámetros: owner`
:   En la CLI con `--no-input`, da el valor con `-s owner=…`.

`No puedo pedir la contraseña aquí. Ejecuta 'sudo -v' antes de abrir AppForge.`
:   La terminal no permite suspender la TUI (por ejemplo, dentro de algunos
    multiplexores o IDE). Ejecuta `sudo -v` antes y vuelve a intentarlo: la
    credencial en caché basta.

`Pasos completados, pero [check] sigue fallando`
:   Todos los pasos terminaron bien, pero la comprobación no ve el resultado. O la
    receta está mal (`[check]` comprueba otra cosa) o algo externo deshizo el cambio.
    Revisa el registro (++l++).

`Detenido en el paso 3/7 …`
:   Ese paso devolvió un código de error; su salida está justo encima en el registro.
    Corrige la causa y vuelve a aplicar: los pasos ya hechos no deberían repetir
    trabajo.

La TUI se ve con caracteres extraños
:   La terminal no tiene una fuente con caracteres de dibujo de cajas o no usa UTF-8.
    Prueba con otra fuente monoespaciada o `LANG=es_ES.UTF-8`.
