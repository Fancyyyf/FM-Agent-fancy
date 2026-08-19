def _check_codegraph_version(config):
    """Surface a missing or stale codegraph pinned build so the user knows to
    re-run ./install.sh — otherwise C/C++ extraction silently degrades to the
    regex fallback (or uses a wrong version). Non-blocking, like every check here.
    """
    import subprocess
    from src.languages.codegraph import _codegraph_cmd

    want = config.settings.codegraph.version.strip().removeprefix("v")
    if not want:
        return True, None  # no version pinned -> nothing to verify

    cmd = _codegraph_cmd()
    try:
        got = subprocess.run(
            [cmd, "--version"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        got = ""

    bin_dir = os.path.expanduser(config.settings.codegraph.bin_dir)
    if not got:
        return False, (
            f"codegraph (pinned v{want}) is not installed at {bin_dir} — run "
            "./install.sh (C/C++ extraction falls back to the regex extractor otherwise)."
        )
    if got != want:
        return False, (
            f"codegraph {got} is installed but v{want} is pinned in fm-agent.toml — "
            "re-run ./install.sh to install the pinned build."
        )
    return True, None
