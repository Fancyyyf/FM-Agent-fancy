def _resolve_command(cmd: str, plugin_root: Path) -> str:
    """Rewrite relative file paths in *cmd* to absolute paths under *plugin_root*.

    Each whitespace-delimited token in *cmd* is checked: if ``plugin_root / token``
    points to an existing file, the token is replaced with its absolute path.
    Tokens starting with ``/``, ``$``, or ``-`` are left unchanged.
    """
    tokens = cmd.split()
    resolved = []
    for token in tokens:
        if token.startswith("/") or token.startswith("$"):
            resolved.append(token)
            continue
        candidate = plugin_root / token
        if candidate.is_file():
            resolved.append(str(candidate))
        else:
            resolved.append(token)
    return " ".join(resolved)
