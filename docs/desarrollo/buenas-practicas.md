# Buenas prácticas

Reglas para que una receta sea **repetible**, **verificable** y **segura**. Son las
mismas que siguen los agentes de IA que añaden recetas (`AGENTS.md`).

## Repetible

**Cada paso debe poder ejecutarse otra vez.** Si una receta falla en el paso 4, se
corrige y se vuelve a aplicar desde el principio: los pasos 1–3 no deben romper nada
ni duplicar trabajo.

| En vez de… | Usa… |
|---|---|
| `mkdir /opt/x` | `mkdir -p /opt/x` |
| `ln -s a b` | `ln -sf a b` |
| `echo "x" >> fichero` | un paso `template` o `copy` (solo escribe si cambia) |
| `useradd x` | `id x \|\| useradd x` |

Para lógica de verdad (decidir, iterar), escribe un `script` con
`set -euo pipefail` y hazlo idempotente.

## Verificable

- **`[check]` comprueba el resultado final**, no un paso intermedio: que el binario
  existe y es ejecutable, no que se descargó.
- Debe ser de **solo lectura** y funcionar **sin root** (`test -e`, `command -v`,
  `grep -q` sobre ficheros legibles).
- Tras `[remove]`, `[check]` debe fallar.

## Ficheros mejor que comandos

Los ficheros de configuración van en `entries/<id>/` como `template` o `copy`, no como
`cat <<EOF` dentro de un `run`: así el *dry-run* enseña el diff y AppForge guarda una
copia del anterior.

## Seguro

- **Nada de `curl … | bash`.** Descarga a un fichero con `curl -fsSL`, verifica la
  suma si el proyecto la publica y luego ejecuta.
- **Secretos**: `secret = true`, sin `default`. Si acaban en un fichero, `mode = "0600"`.
- **Rutas**: todo lo que instala una receta, bajo un prefijo (`/opt/<app>`) siempre
  que se pueda; `[remove]` queda simple.
- **`[remove]` conserva los datos del usuario** (modelos, bases de datos,
  documentos) y lo dice en un comentario.
- **Permisos**: `chmod -R go-w entries`, sin enlaces simbólicos dentro de
  `entries/<id>/`.

## Debian

AppForge no abstrae el gestor de paquetes: cada receta hace lo que necesita. En
Debian, `DEBIAN_FRONTEND=noninteractive apt-get install -y …`.

## Categorías

Reutiliza una categoría existente (el panel de categorías de la TUI las muestra) antes de crear una
casi igual: «Desarrollo» y «Programación» acaban partiendo el catálogo.

## Lista de comprobación

- [ ] `appforge validate --strict <id>` no muestra errores ni avisos.
- [ ] El *dry-run* enseña exactamente lo esperado y ningún secreto en claro.
- [ ] `[check]` falla antes de aplicar y pasa después (la TUI muestra ✔).
- [ ] Aplicar dos veces seguidas deja todo «sin cambios».
- [ ] `[remove]` deshace la receta y `[check]` vuelve a fallar.
- [ ] Si necesita algo que aporta el usuario (un icono, una clave), lo dice en
      `details`.
