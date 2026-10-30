# Probar una receta

Antes de aplicar una receta en tu equipo, pruébala en una máquina desechable. Hay tres
niveles, de menos a más realista:

| Nivel | Qué prueba | Toca el sistema |
|---|---|---|
| `appforge validate --strict <id>` | Formato, permisos, ficheros, sintaxis de bash | No |
| *Dry-run* en la TUI (++d++) | Comandos que ejecutaría, diff de cada fichero, `[check]` | No (solo ejecuta `[check]`) |
| `scripts/try-entry.sh <id>` | Todo: instalar, comprobar, reaplicar, desinstalar | Solo una VM o contenedor desechable |

## `scripts/try-entry.sh`

Abre tu receta en una máquina limpia con [incus](https://linuxcontainers.org/incus/),
te deja probarla en la TUI y al salir la borra. Sirve para cualquier distro con imagen
en incus, no solo Debian.

```bash
scripts/try-entry.sh mi-receta                        # VM con Debian 13
scripts/try-entry.sh mi-receta --distro ubuntu/26.04   # otra distro
scripts/try-entry.sh mi-receta --container             # contenedor: más rápido
scripts/try-entry.sh mi-receta --keep                  # conservarla al salir
scripts/try-entry.sh ruta/a/mi-receta.toml --deb appforge_0.7.0_amd64.deb
```

| Opción | Efecto |
|---|---|
| `RECETA` | Id en `./entries` o ruta a su `.toml`; su subdirectorio `<id>/` va con ella |
| `--distro D` | Imagen de incus (por defecto `debian/13`). Lista: `incus image list images: debian` |
| `--container` | Contenedor en lugar de VM: no necesita KVM, pero no tiene systemd completo |
| `--keep` | No borra la máquina de prueba; entra con `incus exec appforge-try -- bash` |
| `--deb RUTA` | Paquete a instalar (por defecto, el más reciente de `dist/`) |
| `--no-tui` | Solo prepara, sube y valida la receta (p. ej. en una CI) |

Qué hace:

1. Valida la receta en tu equipo: si falla, para antes de crear nada.
2. La primera vez por distro crea `appforge-base-<distro>`: instala el `.deb`, crea un
   usuario `usuario` con `sudo` y guarda la instantánea `limpio`. Las siguientes veces
   solo la clona (segundos); si el `.deb` cambia, la rehace.
3. Clona la base en `appforge-try`, sube la receta a `/etc/appforge/entries/` y la
   valida en la distro de destino.
4. Abre AppForge como `usuario` con `sudo` (así `APPFORGE_USER` es `usuario`): aplica,
   comprueba que sale `aplicada`, vuelve a aplicar («sin cambios») y desinstala.
5. Al salir muestra el final del registro y borra `appforge-try`.

## Preparar incus (una vez)

```bash
sudo apt install incus qemu-system-x86 ovmf   # qemu y ovmf, para las VM
sudo adduser "$USER" incus-admin              # y vuelve a iniciar sesión
incus admin init --minimal
```

Las VM necesitan virtualización por hardware (`/dev/kvm`). Sin ella, usa
`--container`.

## Límites

- Las imágenes no traen escritorio: lanzadores, notificaciones y similares no se ven.
  Para eso hay imágenes con escritorio (`--distro ubuntu/26.04/desktop`, si existe para
  esa distro) o una VM propia desde ISO.
- Solo `amd64`, como el paquete.
- Probado con Debian 13 (VM y contenedor) y Ubuntu 26.04 (contenedor).
