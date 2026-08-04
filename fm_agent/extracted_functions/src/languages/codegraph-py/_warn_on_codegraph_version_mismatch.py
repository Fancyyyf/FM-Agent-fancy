def _warn_on_codegraph_version_mismatch(cmd: str) -> None:
    """Warn (never fail) when the codegraph about to run is not the version pinned
    in ``fm-agent.toml``'s ``[codegraph].version`` — e.g. a stale build shadowing
    it. install.sh is what guarantees the pinned version; this is a runtime heads-up.
    """
    want = settings.codegraph.version.strip().removeprefix("v")
    if not want:
        return
    try:
        got = subprocess.run(
            [cmd, "--version"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return
    if got and got != want:
        logging.warning(
            "codegraph %r does not match the pinned %r "
            "(fm-agent.toml [codegraph].version); re-run install.sh to update.",
            got,
            want,
        )
