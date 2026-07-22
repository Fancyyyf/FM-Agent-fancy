# [SPEC]
# Unit: src/languages/codegraph-py/try_codegraph_init.py
#
# try_codegraph_init(proj_dir: str, force: bool = True) -> None
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a directory path on the filesystem.
#   - force is True or False.
#
# Post-condition:
#   - Returns None; never raises an exception.
#   - When the `codegraph` executable is not found on the system PATH: returns
#     immediately without creating, modifying, or removing any files under proj_dir.
#   - When proj_dir/.codegraph/codegraph.db exists AND force is False: returns
#     immediately; the existing index file and its parent directory are preserved.
#   - Otherwise (force is True, or proj_dir/.codegraph/codegraph.db does not exist):
#     - If a proj_dir/.codegraph/ directory exists, it is removed prior to
#       rebuilding (recursively, with errors ignored).
#     - `codegraph init` is executed with proj_dir as its working directory.
#     - If `codegraph init` exits with code 0: proj_dir/.codegraph/codegraph.db
#       exists after return and reflects the file tree of proj_dir at the time
#       `codegraph init` was invoked.
#     - If `codegraph init` exits with a non-zero code: a warning is logged
#       whose message includes the first 300 characters of stderr; the function
#       returns and the contents of proj_dir/.codegraph/ are unspecified.
# [SPEC]

# [INFO]
# Unit: src/languages/codegraph.py
# _codegraph_cmd() -> str
# Pre-condition:
#   - settings.codegraph.bin_dir is a string specifying a directory path, potentially beginning with a tilde (~) representing the current user's home directory.
# Post-condition:
#   - Returns a string suitable for use as an executable command name.
#   - When a file named "codegraph" exists within the directory obtained by expanding any leading tilde in the configured bin_dir to the user's home directory and that file has the execute permission bit set for the effective user of the current process, returns the absolute filesystem path to that file.
#   - When that file does not exist or lacks the execute permission bit, returns the bare string "codegraph", deferring resolution to the directories named by the PATH environment variable of the calling process.
#   - Never raises an exception.
# Unit: src/languages/codegraph-py/_warn_on_codegraph_version_mismatch.py
# _warn_on_codegraph_version_mismatch(cmd: str) -> None
# Pre-condition:
#   - cmd is a non-empty string identifying an executable command on the system PATH.
#   - settings.codegraph.version is a string (may be empty or whitespace-only).
# Post-condition:
#   - Returns None; never raises an exception.
#   - The function has no externally observable side effect unless all of the following conditions are met:
#     (a) the configured codegraph version, after stripping leading and trailing whitespace and removing any leading "v" prefix, is non-empty;
#     (b) executing the command referred to by cmd with the argument "--version" succeeds as a subprocess and produces non-empty output after stripping leading and trailing whitespace from its captured stdout;
#     (c) that output does not equal the configured version after each has been stripped of whitespace and any leading "v" prefix.
#   - When all conditions (a), (b), and (c) are met: a log record at WARNING severity is emitted whose message identifies both the version string obtained from the command output and the configured version string from fm-agent.toml.
# [INFO]

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
