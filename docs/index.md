---
title: AppForge
description: Recetas de configuración repetibles desde un menú de consola.
hide:
  - navigation
  - toc
---

<div class="af-hero" markdown>

![AppForge](assets/images/logo.png){ .af-hero__logo }

<div markdown>

# App<span>Forge</span>

<p class="af-hero__lead">
Forja tu equipo a partir de recetas. Cada aplicación con configuración propia
—una VPN, un servidor de modelos, tu entorno de desarrollo— se convierte en un
fichero TOML que puedes revisar, repetir y deshacer desde un único menú.
</p>

<div class="af-hero__actions" markdown>
[Empezar](guia/instalacion.md){ .md-button .md-button--primary }
[Crear una receta](desarrollo/nueva-entrada.md){ .md-button }
</div>

</div>

</div>

<figure class="af-shot" markdown>
![Catálogo de AppForge con buscador, categorías y tres entradas seleccionadas](assets/images/screenshots/catalogo.svg)
<figcaption>El catálogo: marca varias recetas, revisa su ficha e instálalas de una vez.</figcaption>
</figure>

## Por qué AppForge

Instalar algo «a tu manera» suele acabar en una nota con veinte comandos, un
fichero de configuración retocado a mano y la duda de si lo hiciste igual la
última vez. AppForge convierte esa nota en una **receta**: un fichero que dice qué
preguntar, qué ejecutar y cómo comprobar que quedó bien.

<div class="grid cards" markdown>

-   :lucide-list-checks:{ .lg } **Siempre sabes qué está aplicado**

    Cada receta trae su propia comprobación. El catálogo marca con *aplicada* lo
    que ya está en tu sistema; no hay ficheros de estado que se desincronicen.

-   :lucide-eye:{ .lg } **Mira antes de tocar**

    El *dry-run* enseña cada comando y el diff de cada fichero que se va a
    escribir. Nada cambia hasta que confirmas.

-   :lucide-shield-check:{ .lg } **Seguro por defecto**

    Contraseña de sudo una sola vez, secretos enmascarados, copias de seguridad
    antes de sobrescribir y recetas rechazadas si alguien más puede editarlas.

-   :lucide-layers:{ .lg } **Por lotes y cancelable**

    Marca varias recetas e instálalas seguidas, con progreso, registro en vivo
    y `ctrl+c` que corta de verdad el comando en curso.

-   :lucide-file-code:{ .lg } **Recetas legibles**

    TOML con cuatro tipos de paso (`run`, `script`, `template`, `copy`). Sin
    condicionales ni bucles: si cabe en una nota, cabe en una receta.

-   :lucide-package:{ .lg } **Un solo binario**

    Copia la carpeta con el binario, `config.toml` y tus recetas a otro equipo y
    funciona igual. `appforge validate` revisa las recetas en tu CI.

</div>

## Cómo funciona

=== "1. Escribe la receta"

    ```toml title="entries/git-aliases.toml"
    name = "Alias de git"
    description = "Alias globales y editor por defecto"
    category = "Desarrollo"

    [[param]]
    name = "editor"
    prompt = "Editor por defecto"
    default = "nano"

    [check]                       # ¿ya está aplicada?
    run = "git config --global --get alias.st"

    [[step]]
    title = "Alias y editor"
    run = """
    git config --global alias.st status
    git config --global core.editor "$editor"
    """

    [remove]
    run = "git config --global --unset alias.st"
    ```

=== "2. Revísala"

    <figure class="af-shot" markdown>
    ![Página de detalle de la receta de Ollama](assets/images/screenshots/detalle.svg)
    <figcaption>Doble clic (o <kbd>v</kbd>) abre la ficha completa: descripción, parámetros, cada paso y su comprobación.</figcaption>
    </figure>

=== "3. Aplícala"

    <figure class="af-shot" markdown>
    ![Progreso de una instalación por lotes](assets/images/screenshots/progreso.svg)
    <figcaption>Progreso por receta, barra global y registro etiquetado por tipo de paso.</figcaption>
    </figure>

## Incluye

La receta **[Ollama bajo demanda](guia/ollama.md)**: modelos de lenguaje en local
sin servicio de arranque, con un lanzador que lo enciende y apaga y ajustes de
memoria pensados para GPU de consumo.

<div class="af-hero__actions" markdown>
[Instalar AppForge](guia/instalacion.md){ .md-button .md-button--primary }
[Ver todas las opciones](avanzado/configuracion.md){ .md-button }
</div>
