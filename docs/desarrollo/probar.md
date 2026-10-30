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
scripts/try-entry.sh ruta/a/mi-receta.toml --tar appforge-0.8.0-linux-x86_64.tar.gz
```

| Opción | Efecto |
|---|---|
| `RECETA` | Id en `./entries` o ruta a su `.toml`; su subdirectorio `<id>/` va con ella |
| `--distro D` | Imagen de incus (por defecto `debian/13`). Lista: `incus image list images: debian` |
| `--container` | Contenedor en lugar de VM: no necesita KVM, pero no tiene systemd completo |
| `--keep` | No borra la máquina de prueba; entra con `incus exec appforge-try -- bash` |
| `--tar RUTA` | Paquete `appforge-*.tar.gz` a instalar (por defecto, el más reciente de `dist/`) |
| `--no-tui` | Solo prepara, sube y valida la receta (p. ej. en una CI) |

Qué hace:

1. Valida la receta en tu equipo: si falla, para antes de crear nada. Valida una copia
   sin escritura para grupo y otros, así que los permisos de tu copia de trabajo (que
   dependen de tu `umask`; git no los guarda) no la hacen fallar.
2. La primera vez por distro crea `appforge-base-<distro>`: extrae el paquete en
   `/opt/appforge` (con un enlace en `/usr/local/bin`), crea un
   usuario `usuario` con `sudo` y guarda la instantánea `limpio`. Las siguientes veces
   solo la clona (segundos); si el paquete cambia, la rehace.
3. Clona la base en `appforge-try`, sube la receta a `/opt/appforge/custom-entries/` y la
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

| Mensaje del script | Solución |
|---|---|
| `no puedo usar incus: … permission denied` | Tu sesión no tiene el grupo `incus-admin`: `newgrp incus-admin` o vuelve a iniciar sesión |
| `incus no admite VM todavía` | incus detecta QEMU al arrancar: `sudo systemctl restart incus` tras instalar `qemu-system-x86` y `ovmf` |
| `sin /dev/kvm no hay VM` | Activa la virtualización en la BIOS/UEFI o usa `--container` |
| `no tiene red` | Ver abajo |

### Sin red en la máquina

incus da red a sus máquinas con el puente `incusbr0` y su propio DHCP/DNS. Si un
cortafuegos descarta ese tráfico, la máquina arranca pero no recibe IP o no sale a
Internet.

```bash
incus exec appforge-try -- ip -4 addr          # sin IP 10.x: el DHCP está bloqueado
sudo nft list ruleset | grep -iE "policy drop|ufw|firewalld|docker"
```

| Causa | Solución |
|---|---|
| **ufw** activo (entrada y reenvío en `drop`) | `sudo ufw allow in on incusbr0`, `sudo ufw route allow in on incusbr0` y `sudo ufw route allow out on incusbr0` |
| **firewalld** activo | `sudo firewall-cmd --zone=trusted --change-interface=incusbr0 --permanent` y `sudo firewall-cmd --reload` |
| **Docker** instalado: pone la cadena `FORWARD` de iptables en `DROP` | `sudo iptables -I DOCKER-USER -i incusbr0 -j ACCEPT` y `sudo iptables -I DOCKER-USER -o incusbr0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT` |

Tras abrir el puente, borra la base que se quedó sin red
(`incus delete -f appforge-base-debian-13-vm`) y repite.

Las reglas de iptables de Docker no sobreviven a un reinicio; para hacerlas
permanentes, guárdalas con `iptables-persistent` o el mecanismo que uses.

## Límites

- Las imágenes no traen escritorio: lanzadores, notificaciones y similares no se ven.
  Para eso hay imágenes con escritorio (`--distro ubuntu/26.04/desktop`, si existe para
  esa distro) o una VM propia desde ISO.
- Solo `amd64`, como el paquete.
- Probado con Debian 13 (VM y contenedor) y Ubuntu 26.04 (contenedor).
