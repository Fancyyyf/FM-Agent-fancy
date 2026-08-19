def detect_opencode_config_path(home: Path | None = None) -> Path:
    custom_config = os.environ.get("OPENCODE_CONFIG")
    if custom_config:
        return Path(custom_config).expanduser()
    custom_config_dir = os.environ.get("OPENCODE_CONFIG_DIR")
    if custom_config_dir:
        config_dir = Path(custom_config_dir).expanduser()
        jsonc = config_dir / "opencode.jsonc"
        return jsonc if jsonc.exists() else config_dir / "opencode.json"
    home = home or Path.home()
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        config_dir = (
            Path(appdata) / "opencode"
            if appdata
            else home / "AppData" / "Roaming" / "opencode"
        )
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        config_dir = Path(xdg) / "opencode" if xdg else home / ".config" / "opencode"
    jsonc = config_dir / "opencode.jsonc"
    if jsonc.exists():
        return jsonc
    return config_dir / "opencode.json"
