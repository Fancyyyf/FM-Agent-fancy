def _resolve_bug_validator_path(raw_path):
    """Resolve a custom bug-validator prompt path from the launch directory."""
    if not raw_path:
        return None

    path = os.path.abspath(os.path.expanduser(raw_path))
    if not os.path.isfile(path):
        raise ValueError(
            "--bug-validator must point to a file: "
            f"{raw_path}"
        )

    try:
        with open(path, "r"):
            pass
    except OSError as exc:
        raise ValueError(
            f"--bug-validator file is not readable: {exc}"
        ) from exc

    return path
