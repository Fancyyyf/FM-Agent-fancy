# [SPEC]
# Unit: src/languages/codegraph.py
#
# _codegraph_cmd() -> str
#
# Pre-condition:
#   - settings.codegraph.bin_dir is a string specifying a directory path, potentially beginning with a tilde (~) representing the current user's home directory.
#
# Post-condition:
#   - Returns a string suitable for use as an executable command name.
#   - When a file named "codegraph" exists within the directory obtained by expanding any leading tilde in the configured bin_dir to the user's home directory and that file has the execute permission bit set for the effective user of the current process, returns the absolute filesystem path to that file.
#   - When that file does not exist or lacks the execute permission bit, returns the bare string "codegraph", deferring resolution to the directories named by the PATH environment variable of the calling process.
#   - Never raises an exception.
# [SPEC]

def _codegraph_cmd() -> str:
    """Return the codegraph executable to invoke.

    ``install.sh`` installs the pinned fork build (from ``fm-agent.toml``'s
    ``[codegraph]``) into ``bin_dir`` (default ``~/.local/bin``); we invoke it
    from that same configured location. Invoking it by absolute path — rather than
    a bare ``codegraph`` resolved via PATH — uses the pinned build even when that
    directory is not on PATH (the macOS default) and cannot be shadowed by a
    different/older codegraph earlier on PATH. Falls back to a bare ``codegraph``
    when the pinned build is absent, so an externally provided one still works; a
    missing binary then becomes the regex-extractor fallback in the caller.
    """
    bin_dir = os.path.expanduser(settings.codegraph.bin_dir)
    local = os.path.join(bin_dir, "codegraph")
    return local if os.access(local, os.X_OK) else "codegraph"
