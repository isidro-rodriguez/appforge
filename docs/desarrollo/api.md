# Referencia de la API

Generada a partir de los docstrings del código.

## Recetas

::: appforge.entry
    options:
      members:
        - Entry
        - Param
        - Step
        - load_entry
        - load_entries
        - load_catalog
        - Catalog
        - insecure_reason

## Validación

::: appforge.validate
    options:
      members:
        - Validation
        - Report
        - validate_dirs
        - validate_dir
        - validate_entry
        - bash_syntax_error

## Actualización

::: appforge.update
    options:
      members:
        - Plan
        - plan_update
        - apply_update
        - read_manifest
        - check_sum
        - latest_release
        - download
        - extract

## Motor

::: appforge.engine
    options:
      members:
        - Engine
        - Runner
        - EngineError
        - resolve_values
        - backup_path

## Configuración

::: appforge.config
    options:
      members:
        - Config
        - UiConfig
        - ConfigError
        - load_config
        - base_dir
        - state_dir

## Registro

::: appforge.runlog
    options:
      members:
        - RunLog
        - step_tag

## Tema

::: appforge.theme
