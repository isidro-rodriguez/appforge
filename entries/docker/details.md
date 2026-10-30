Instala Docker Engine desde el
[repositorio APT oficial de Docker](https://docs.docker.com/engine/install/debian/):
`docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin` y
`docker-compose-plugin`.

### Repositorio firmado

- La clave se descarga a `/etc/apt/keyrings/docker.asc` y **se comprueba su huella**
  antes de usarla; si no coincide, la receta falla.
- El repositorio se declara en `/etc/apt/sources.list.d/docker.sources` (formato
  deb822) con `Signed-By`: esa clave solo vale para este repositorio.

Si tenías `docker.io` u otros paquetes de Debian que chocan con los de Docker, APT
los sustituye.

### ⚠ Antes de usarlo

- Tu usuario entra en el grupo `docker`, lo que **equivale a ser root** en la
  máquina. Cierra sesión y vuelve a entrar para usar `docker` sin `sudo`.
- Docker **publica puertos saltándose ufw**: un `-p 8080:80` queda abierto aunque
  ufw lo deniegue. Publica en `127.0.0.1:8080:80` si solo lo usas en local.
- Docker pone la política `FORWARD` de iptables en `DROP` y deja sin red a las
  instancias de **Incus** en la misma máquina.

Desinstalar quita los paquetes, el repositorio y la clave. **Conserva**
`/var/lib/docker` (imágenes, contenedores y volúmenes) y `/etc/docker`.
