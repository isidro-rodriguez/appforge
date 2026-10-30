Instala `openssh-server` y escribe el endurecimiento en
`/etc/ssh/sshd_config.d/50-appforge.conf`, sin editar `sshd_config`:

| Ajuste | Valor |
|---|---|
| `Port` | Parámetro (22) |
| `PermitRootLogin` | `no` |
| `PasswordAuthentication` | Parámetro (`no` salvo que lo permitas) |
| `KbdInteractiveAuthentication` | `no` |
| `X11Forwarding` | `no` |
| `MaxAuthTries` | `3` |
| `AllowUsers` | El usuario que ejecutó `sudo appforge` |

### Para no quedarte fuera

- Con `PasswordAuthentication no`, la receta **falla antes de tocar nada** si tu
  `~/.ssh/authorized_keys` no existe o está vacío. Copia antes tu clave pública
  (`ssh-copy-id` desde el otro equipo) o aplica la receta permitiendo la contraseña.
- La configuración se valida con `sshd -t` antes de recargar el servicio; si no es
  válida, se restaura la anterior y la receta falla.
- Si ufw está activo, se abre `<puerto>/tcp`. Al cambiar de puerto, la regla del
  anterior se queda: bórrala tú con `sudo ufw delete allow 22/tcp`.
- En `sshd_config.d` gana el primer valor leído: si otro fichero anterior a
  `50-appforge.conf` fija lo mismo, la receta avisa con el valor efectivo
  (`sshd -T`).

Desinstalar borra `50-appforge.conf` y recarga el servicio; no desinstala OpenSSH
ni cierra el puerto en ufw.
