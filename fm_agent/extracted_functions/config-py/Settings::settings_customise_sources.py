# [SPEC]
# Unit: config.py
#
# Settings.settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings)
#
# Pre-condition:
#   - settings_cls is a subclass of BaseSettings with typed fields declared via pydantic Field annotations
#   - init_settings is a PydanticBaseSettingsSource carrying keyword-argument values passed to Settings()
#   - _CONFIG_PATH is a pathlib.Path pointing to the fm-agent.toml configuration file
#
# Post-condition:
#   - Returns a 2-tuple of PydanticBaseSettingsSource instances defining the complete field-resolution priority chain
#   - The first element (init_settings) has highest priority; any field value provided via keyword arguments to Settings(...) is used as-is and never overridden by any other source
#   - The second element is a _LayeredSource that resolves each field in the following order of descending priority:
#       1. Process environment variables whose names appear as keys in _ENV_MAP
#       2. Values from the TOML file at _CONFIG_PATH
#       3. The pydantic Field default declared on the field in settings_cls
#   - The env_settings, dotenv_settings, and file_secret_settings sources are discarded; they do not participate in field resolution
#   - Every field of the Settings model is resolved through exactly one of the two returned sources
# [SPEC]

# [INFO]
# _LayeredSource(settings_cls, path)
#   Pre-condition: settings_cls is a BaseSettings subclass; path is a pathlib.Path
#   Post-condition: When invoked as a callable, returns a dict whose top-level keys are TOML section names (str) and whose values are dicts mapping field names to their resolved values
#   Post-condition: Values in the returned dict originate from two layers in descending priority: (1) process environment variables found in _ENV_MAP for the corresponding (section, field) pair, then (2) the TOML file at path
#   Post-condition: If path does not point to an existing file, the TOML layer contributes no values and only environment variable overrides appear in the returned dict
#   Post-condition: The returned dict is suitable as a merged data source for pydantic-settings field resolution, where pydantic Field defaults serve as the final fallback below all values present in the dict
# [INFO]

    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # init (programmatic) wins; everything else is folded into _LayeredSource,
        # which already applies env > toml > field defaults.
        return (init_settings, _LayeredSource(settings_cls, _CONFIG_PATH))
