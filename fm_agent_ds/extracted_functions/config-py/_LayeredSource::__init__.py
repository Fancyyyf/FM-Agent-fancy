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
