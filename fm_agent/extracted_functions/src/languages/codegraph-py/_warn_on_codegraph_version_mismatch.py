# [SPEC]
# Unit: src/languages/codegraph-py/_warn_on_codegraph_version_mismatch.py
#
# _warn_on_codegraph_version_mismatch(cmd: str) -> None
#
# Pre-condition:
#   - cmd is a non-empty string identifying an executable command on the system PATH.
#   - settings.codegraph.version is a string (may be empty or whitespace-only).
#
# Post-condition:
#   - Returns None; never raises an exception.
#   - The function has no externally observable side effect unless all of the
#     following conditions are met:
#       (a) the configured codegraph version, after stripping leading and trailing
#           whitespace and removing any leading "v" prefix, is non-empty;
#       (b) executing the command referred to by cmd with the argument "--version"
#           succeeds as a subprocess and produces non-empty output after stripping
#           leading and trailing whitespace from its captured stdout;
#       (c) that output does not equal the configured version after each has been
#           stripped of whitespace and any leading "v" prefix.
#   - When all conditions (a), (b), and (c) are met: a log record at WARNING
#     severity is emitted whose message identifies both the version string obtained
#     from the command output and the configured version string from
#     fm-agent.toml.
# [SPEC]

# [INFO]
# subprocess.run(args, *, capture_output, text, timeout) -> CompletedProcess
#   Pre-condition: args is a list of strings where the first element is an
#   executable command name and remaining elements are arguments; capture_output
#   is True; text is True; timeout is a positive number of seconds.
#   Post-condition: If the subprocess starts and completes within timeout,
#   returns a CompletedProcess whose stdout attribute is the captured standard
#   output as a string. If the subprocess cannot be started or fails to
#   execute, raises OSError or SubprocessError.
# [SPLIT]
# logging.warning(msg, *args) -> None
#   Pre-condition: msg is a string, and any additional positional arguments
#   are values to be interpolated into msg via %-style formatting.
#   Post-condition: A log record at WARNING severity is delivered to all
#   handlers configured on the root logger. Never raises an exception.
# [INFO]

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
