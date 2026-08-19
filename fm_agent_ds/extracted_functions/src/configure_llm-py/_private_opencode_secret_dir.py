def _private_opencode_secret_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg_state = os.environ.get("XDG_STATE_HOME")
        xdg_state_path = Path(xdg_state).expanduser() if xdg_state else None
        base_dir = (
            xdg_state_path
            if xdg_state_path and xdg_state_path.is_absolute()
            else Path.home() / ".local" / "state"
        )
    return base_dir / "fm-agent" / "opencode"
