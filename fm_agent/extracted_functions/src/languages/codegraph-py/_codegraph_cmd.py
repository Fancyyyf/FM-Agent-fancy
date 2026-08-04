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
