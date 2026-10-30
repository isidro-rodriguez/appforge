Instala [Incus](https://linuxcontainers.org/incus/) desde los paquetes de Debian 13
para crear contenedores y máquinas virtuales.

### Qué hace

- Paquete `incus` y, si marcas el soporte de **máquinas virtuales**, `qemu-system-x86` y `ovmf`
  (máquinas virtuales con UEFI).
- `incus admin init --minimal` solo si Incus no está inicializado: almacenamiento
  `dir` y el puente `incusbr0` con NAT.
- Añade tu usuario al grupo `incus-admin`. **Cierra sesión y vuelve a entrar** para
  usar `incus` sin `sudo`.
- Si ufw está instalado, permite el tráfico del puente (`ufw allow in on incusbr0`
  y `ufw route allow in/out on incusbr0`); sin estas reglas las instancias no
  obtienen IP ni salen a Internet.

### ⚠ Docker en la misma máquina

Docker pone la política `FORWARD` de iptables en `DROP` y deja sin red a las
instancias de Incus. Si necesitas los dos, consulta la
[guía de Incus sobre Docker](https://linuxcontainers.org/incus/docs/main/howto/network_bridge_firewalld/) (apartado sobre Docker).

Desinstalar quita las reglas de ufw y saca a tu usuario de `incus-admin`.
**No** desinstala Incus ni borra instancias, imágenes o almacenamiento.
