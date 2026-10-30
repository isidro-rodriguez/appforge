# Crear una receta

Vamos a escribir una receta completa: **endurecer el servidor SSH** con un fichero en
`/etc/ssh/sshd_config.d/`. Usa casi todo el formato: parámetros, una plantilla,
pasos, comprobación y eliminación.

## 1. Los ficheros

Una receta es una carpeta `entries/<id>/` en el repositorio (instalada, en
`/opt/appforge/custom-entries/<id>/` si es tuya; edítala con `sudo`). El `<id>` es el
nombre de la carpeta. Dentro van la receta (`entry.toml`), su ficha (`details.md`) y
los ficheros que usen sus pasos (plantillas, scripts, iconos).

```text
entries/
└── ssh-hardening/
    ├── entry.toml
    ├── details.md
    └── hardening.conf.tpl
```

## 2. La cabecera

```toml title="entries/ssh-hardening/entry.toml"
name = "SSH endurecido"
description = "Sin contraseñas ni root por SSH; puerto y usuarios propios"
category = "Sistema"
```

Todo se ejecuta como `root`: AppForge solo arranca como superusuario.

La ficha va aparte, en Markdown, y se ve en la
[página de detalle](../guia/interfaz.md#página-de-detalle). Es obligatoria: cuenta qué
hace la receta, qué conviene saber antes y qué deja al desinstalar.

```markdown title="entries/ssh-hardening/details.md"
Escribe `/etc/ssh/sshd_config.d/50-appforge.conf` con una configuración
restrictiva y recarga el servicio **solo si la sintaxis es válida**.

Asegúrate de tener tu clave pública en `~/.ssh/authorized_keys` antes de
aplicarla: se desactiva el acceso con contraseña.
```

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

    La comprobación se ejecuta con los valores **por defecto** de los
    parámetros (al pintar el catálogo no hay otros). Comprueba que el resultado
    existe, no que tenga un valor concreto de un parámetro.

## 7. Comprueba la receta

```bash
sudo chmod -R go-w /opt/appforge/custom-entries # nadie más puede modificarlas
appforge validate --strict ssh-hardening         # sin errores ni avisos → código 0
sudo appforge                                    # TUI: márcala y pulsa d (dry-run)
```

`validate` no ejecuta nada: comprueba el formato, los ficheros de `ssh-hardening/`,
la sintaxis de bash y que cada parámetro se use. El *dry-run* de la TUI muestra el diff
del fichero y los comandos (precedidos de `#`), con `usuario` como valor de `users`:

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
  │ +AllowUsers usuario
==> [2/2] Validar y recargar [dry-run]
  │ # sshd -t && systemctl reload ssh
✔ Dry-run completado: no se ha cambiado nada
```

En la TUI aparece con su categoría y se puede revisar con doble clic antes de
instalar.

## 8. Un test (opcional)

Si la receta va al repositorio, añade `tests/test_<id>.py`. La fixture `home` copia
`entries/` a un directorio temporal con un `config.toml` por defecto:

```python title="tests/test_ssh_hardening.py"
from appforge.engine import Engine
from appforge.entry import load_entries


def test_dry_run(config, sink) -> None:
    entries, _ = load_entries(config.entries_dirs[0])
    entry = next(e for e in entries if e.id == "ssh-hardening")
    assert entry.valid, entry.problems
    assert Engine(config, sink).apply(entry, {"users": "ana"}, dry_run=True)
    assert "+AllowUsers ana" in sink.text()
```

Los tests nunca deben tocar rutas reales del sistema: usa *dry-run*.

## Siguiente

- Pruébala de verdad en una máquina desechable: [Probar una receta](probar.md).
- Referencia completa del [formato](formato.md).
- [Buenas prácticas](buenas-practicas.md) para recetas fiables y seguras.
