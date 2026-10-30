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
| `alias.*` | Ver «Alias de git»; parámetro (sí) |

### Alias de git

Con el parámetro de alias activado (por defecto), se añaden a `~/.gitconfig`:

| Alias | Equivale a |
|---|---|
| `git st` | `git status -sb` |
| `git a` / `git c` / `git d` / `git p` | `add` / `commit` / `diff` / `push` |
| `git ds` | `git diff --staged` |
| `git lg` | `git log --oneline --graph --decorate -20` |
| `git pl` | `git pull --ff-only` |
| `git sw` | `git switch` |
| `git bc` | `git bundle create` |
| `git bundle-pull fichero.bundle [rama]` | Verifica el bundle y hace `pull --ff-only` de esa rama (`main` por defecto) |

Ninguno se llama como un comando de git, porque git ignora esos alias. Reaplicar la
receta restablece sus valores. Para quitar uno:
`git config --global --unset alias.<nombre>`. Desactivar el parámetro no borra los
que ya existan.

### Iniciar sesión en GitHub

La receta no inicia sesión. Después de aplicarla, como tu usuario (sin `sudo`):

```bash
gh auth login
```

Desde entonces `git push` y `git pull` contra github.com usan las credenciales de
`gh`.

Desinstalar quita `gh`, su repositorio y su clave. **No** desinstala `git` ni toca
tu `~/.gitconfig`.
