# [SPEC]
# Unit: src/env_check.py
#
# _check_codegraph_version(config) -> (bool, str | None)
#
# Pre-condition:
#   - config provides access to a codegraph version string via settings.codegraph.version and a binary directory path via settings.codegraph.bin_dir
#
# Post-condition:
#   - Returns (True, None) when the configured codegraph version, after stripping whitespace and a leading "v" prefix, is the empty string — no version is pinned so verification is skipped
#   - Otherwise, attempts to obtain the installed codegraph binary's version string by executing it with a --version flag and capturing its standard output
#   - Returns (False, message) when the version string could not be obtained (binary missing, not executable, or times out), with a message identifying the configured binary directory and instructing the user to re-run ./install.sh
#   - Returns (False, message) when the obtained version string does not equal the configured pinned version (after stripping whitespace and any leading "v" prefix), with a message stating the installed and pinned versions and instructing the user to re-run ./install.sh
#   - Returns (True, None) when the obtained version string equals the configured pinned version
#   - Never raises an exception: all error paths return (False, message) with a human-readable description
# [SPEC]

# [INFO]
# _codegraph_cmd() -> str
#   Pre-condition: settings.codegraph.bin_dir is configured with a directory path
#   Post-condition: Returns an absolute filesystem path resolving to "codegraph" under the configured binary directory when that file exists and is executable; returns the bare string "codegraph" when the pinned binary is absent, delegating resolution to the process PATH
# [INFO]

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
