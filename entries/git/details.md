Instala `git` (Debian) y [GitHub CLI](https://cli.github.com) (`gh`) desde su
repositorio APT oficial, y configura git para tu usuario.

### Repositorio de GitHub CLI

Mismo patrón que la receta de Docker: la clave se descarga a
`/etc/apt/keyrings/githubcli-archive-keyring.gpg` tras **comprobar su huella**
(publicadas en la
[guía de instalación](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)),
y el repositorio va en `/etc/apt/sources.list.d/github-cli.sources` con `Signed-By`.

### Configuración global (`~/.gitconfig`)

| Ajuste | Valor |
|---|---|
| `user.name`, `user.email` | Parámetros |
| `init.defaultBranch` | Parámetro (`main`) |
| `pull.rebase` | `false` (merge al hacer `pull`) |
| `core.editor` | Parámetro; `-` = no se toca |
| Credenciales de github.com | `gh` (`gh auth setup-git`) |

### Iniciar sesión en GitHub

La receta no inicia sesión. Después de aplicarla, como tu usuario (sin `sudo`):

```bash
gh auth login
```

Desde entonces `git push` y `git pull` contra github.com usan las credenciales de
`gh`.

Desinstalar quita `gh`, su repositorio y su clave. **No** desinstala `git` ni toca
tu `~/.gitconfig`.
