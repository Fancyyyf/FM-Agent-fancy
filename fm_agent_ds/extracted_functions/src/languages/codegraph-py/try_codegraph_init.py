def try_codegraph_init(proj_dir: str, force: bool = True) -> None:
    """Build the codegraph index for proj_dir with `codegraph init`.

    By default (``force=True``) any existing index is discarded and rebuilt, so
    the index always reflects the current working tree rather than whatever code
    was present when it was last built. This is the safe default: callers read
    function bodies and spans from the index, and a stale one (e.g. after an
    incremental run's tree changed, or after `_trim_project_in_place` edited the
    sources) would yield boundaries for the wrong code. `codegraph init` on its
    own no-ops when `.codegraph/` already exists, so a rebuild requires clearing
    it first.

    Pass ``force=False`` to keep an existing index and only build when it is
    absent — an opt-in optimization for callers that know the tree is unchanged
    since the index was built.

    Silently skips when codegraph is not installed so the pipeline falls back
    to the regex-based extractor without any error.
    """
    codegraph_dir = os.path.join(proj_dir, ".codegraph")
    db_path = os.path.join(codegraph_dir, "codegraph.db")
    if os.path.exists(db_path):
        if not force:
            return
        # Existing index may reflect stale sources; remove it so `codegraph init`
        # rebuilds against the current tree instead of skipping.
        shutil.rmtree(codegraph_dir, ignore_errors=True)
        print("[Pipeline] Rebuilding codegraph index for current working tree...")
    else:
        print("[Pipeline] Building codegraph index...")
    cmd = _codegraph_cmd()
    _warn_on_codegraph_version_mismatch(cmd)
    try:
        result = subprocess.run(
            [cmd, "init"], cwd=proj_dir, capture_output=True, text=True
        )
    except FileNotFoundError:
        return  # codegraph not installed
    if result.returncode == 0:
        print("[Pipeline] codegraph index built.")
    else:
        logging.warning(
            "codegraph init failed (non-fatal, falling back to regex): %s",
            result.stderr[:300],
        )
