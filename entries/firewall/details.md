Instala y activa [ufw](https://wiki.debian.org/Uncomplicated%20Firewall%20%28ufw%29)
con esta política:

| Tráfico | Política |
|---|---|
| Entrante | Denegado (salvo las excepciones) |
| Saliente | Permitido |

### Parámetros

- **Excepciones**: reglas de ufw separadas por espacios, p. ej. `22/tcp 80/tcp 443`
  o `60000:61000/udp` (los rangos llevan protocolo). También nombres de servicio
  de `/etc/services` (`ssh`, `https`). `-`: ninguna.
- **Red de confianza**: una red desde la que se permite todo, p. ej.
  `192.168.1.0/24`; déjala vacía para ninguna.

Todas las excepciones se validan antes de cambiar nada; si una no es válida, la
receta falla sin tocar el cortafuegos. Reaplicar no duplica reglas, pero tampoco
borra las que ya no estén en la lista (`sudo ufw status numbered` y
`sudo ufw delete <n>`).

### ⚠ Si administras la máquina por SSH

Activar el cortafuegos **sin permitir el puerto 22** (o el que use tu servidor
SSH) deja fuera las conexiones nuevas y puede cortar la sesión actual. Añade
`22/tcp` a las excepciones, o aplica antes la receta del servidor SSH, que abre
su puerto si ufw está activo.

Desinstalar ejecuta `ufw disable`: no desinstala ufw ni borra las reglas.
