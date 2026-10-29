# Crear una receta

Vamos a escribir una receta completa: **endurecer el servidor SSH** con un fichero en
`/etc/ssh/sshd_config.d/`. Usa casi todo el formato: parámetros, una plantilla,
pasos con root, comprobación y eliminación.

## 1. Los ficheros

Una receta es `entries/<id>.toml`. Si necesita ficheros (plantillas, scripts,
iconos), van en `entries/<id>/`. El `<id>` es el nombre del fichero y es lo que usa la
CLI.

```text
entries/
├── ssh-hardening.toml
└── ssh-hardening/
    └── hardening.conf.tpl
```

## 2. La cabecera

```toml title="entries/ssh-hardening.toml"
name = "SSH endurecido"
description = "Sin contraseñas ni root por SSH; puerto y usuarios propios"
category = "Sistema"
requires_root = true
details = """
Escribe `/etc/ssh/sshd_config.d/50-appforge.conf` con una configuración
restrictiva y recarga el servicio **solo si la sintaxis es válida**.

Asegúrate de tener tu clave pública en `~/.ssh/authorized_keys` antes de
aplicarla: se desactiva el acceso con contraseña.
"""
```

`requires_root` hace que los pasos y `[remove]` se ejecuten con `sudo`. `details` es
Markdown y se ve en la [página de detalle](../guia/interfaz.md#página-de-detalle).

## 3. Los parámetros

```toml
[[param]]
name = "port"
prompt = "Puerto de SSH"
default = "22"

[[param]]
name = "users"
prompt = "Usuarios con acceso (separados por espacios)"
```

`users` no tiene `default`, así que es obligatorio. Los parámetros llegan a los
comandos como variables (`$port`, `$users`) y a las plantillas como `$port`.

## 4. La plantilla

```text title="entries/ssh-hardening/hardening.conf.tpl"
# Generado por AppForge (receta ssh-hardening)
Port $port
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
AllowUsers $users
```

!!! warning "El `$` literal"

    En una plantilla cada `$nombre` debe ser un parámetro declarado; si no,
    la receta es inválida. Para un `$` literal escribe `$$`. Un script de shell con
    `$VARIABLES` propias no es una plantilla: cópialo con `copy`.

## 5. Los pasos

```toml
[[step]]
title = "Configuración de sshd"
template = "hardening.conf.tpl"
dest = "/etc/ssh/sshd_config.d/50-appforge.conf"
mode = "0644"

[[step]]
title = "Validar y recargar"
run = "sshd -t && systemctl reload ssh"
```

El primer paso solo escribe si el contenido cambia, y guarda una copia del anterior.
El segundo usa `sshd -t` para no recargar nunca una configuración rota.

## 6. Comprobación y eliminación

```toml
[check]
run = "test -f /etc/ssh/sshd_config.d/50-appforge.conf"

[remove]
run = "rm -f /etc/ssh/sshd_config.d/50-appforge.conf && systemctl reload ssh"
```

!!! info "`[check]` no ve tus parámetros"

    La comprobación se ejecuta **sin root** y con los valores **por defecto** de los
    parámetros (al pintar el catálogo no hay otros). Comprueba que el resultado
    existe, no que tenga un valor concreto de un parámetro.

## 7. Comprueba la receta

```bash
chmod -R go-w entries                       # AppForge rechaza recetas editables por otros
uv run appforge show ssh-hardening           # sin problemas → código 0
uv run appforge apply ssh-hardening -n --no-input -s users="$USER"
```

El *dry-run* muestra el diff del fichero y los comandos (`#` = con root):

```text
  Estado actual: no aplicada
==> [1/2] Configuración de sshd [dry-run]
  crear /etc/ssh/sshd_config.d/50-appforge.conf (modo 0644, 150 bytes)
  │ --- /etc/ssh/sshd_config.d/50-appforge.conf
  │ +++ /etc/ssh/sshd_config.d/50-appforge.conf (nuevo)
  │ @@ -0,0 +1,6 @@
  │ +# Generado por AppForge (receta ssh-hardening)
  │ +Port 22
  │ +PermitRootLogin no
  │ +PasswordAuthentication no
  │ +KbdInteractiveAuthentication no
  │ +AllowUsers isidro
==> [2/2] Validar y recargar [dry-run]
  │ # sshd -t && systemctl reload ssh
✔ Dry-run completado: no se ha cambiado nada
```

En la TUI aparece con su categoría y se puede revisar con doble clic antes de
instalar.

## 8. Un test (opcional)

Si la receta va al repositorio, añade `tests/test_<id>.py`. La fixture `home` copia
`config.toml` y `entries/` a un directorio temporal:

```python title="tests/test_ssh_hardening.py"
from appforge.engine import Engine
from appforge.entry import load_entries


def test_dry_run(config, sink) -> None:
    entries, _ = load_entries(config.entries_dir)
    entry = next(e for e in entries if e.id == "ssh-hardening")
    assert entry.valid, entry.problems
    assert Engine(config, sink).apply(entry, {"users": "ana"}, dry_run=True)
    assert "+AllowUsers ana" in sink.text()
```

Los tests nunca deben tocar rutas reales del sistema: usa *dry-run*.

## Siguiente

- Referencia completa del [formato](formato.md).
- [Buenas prácticas](buenas-practicas.md) para recetas fiables y seguras.
