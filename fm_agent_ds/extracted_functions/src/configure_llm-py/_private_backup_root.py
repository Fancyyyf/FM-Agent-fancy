def _private_backup_root() -> Path:
    if hasattr(os, "getuid"):
        user_component = f"uid-{os.getuid()}"
    else:
        user_component = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", user_component).strip("._-") or "user"
    return Path(tempfile.gettempdir()) / f"fm-agent-config-backups-{safe}"
