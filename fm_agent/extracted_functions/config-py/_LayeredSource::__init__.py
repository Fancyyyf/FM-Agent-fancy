# [SPEC]
# Unit: config.py
#
# _LayeredSource.__init__(self, settings_cls, path) -> None
#
# Pre-condition:
#   - settings_cls is a subclass of BaseSettings with typed fields declared via pydantic Field annotations
#   - path is a pathlib.Path
#
# Post-condition:
#   - Invoking the instance as a callable returns a dict whose top-level keys are str section names and whose values are dicts mapping str field names to their values
#   - When path refers to an existing regular file containing valid TOML, every key-value pair parsed from the file is present in the returned dict
#   - When path does not refer to an existing regular file, no file-sourced entries appear in the returned dict and a diagnostic message identifying the file name and absolute path is written to stderr
#   - For each supported process environment variable that is set, the returned dict contains the corresponding (section, field) entry; an environment-sourced entry replaces any file-sourced entry for the same field
#   - A field for which no entry exists in the returned dict — neither from the file nor from any matching environment variable — is absent from the returned dict, and pydantic resolves it to the Field default declared on the settings model
# [SPEC]

    def __init__(self, settings_cls, path: Path):
        super().__init__(settings_cls)
        data: dict = {}
        if path.is_file():
            data = tomllib.loads(path.read_text())
        else:
            # A missing default fm-agent.toml is tolerated (built-in defaults are
            # kept identical to it), but warn: it usually means a broken checkout
            # or a deleted file, and silently using defaults would hide that.
            print(
                f"FM-Agent: {path.name} not found at {path}; using built-in defaults.",
                file=sys.stderr,
            )
        for env_name, (section, field) in _ENV_MAP.items():
            value = os.environ.get(env_name)
            if value is not None:
                data.setdefault(section, {})[field] = value
        self._data = data
