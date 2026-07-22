# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::_codegraph_cmd` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: (none).

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
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
```

## Specs of this function's callers

### src::env_check-py::_check_codegraph_version

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

### src::languages::codegraph-py::try_codegraph_init

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

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::env_check-py::_check_codegraph_version

# _codegraph_cmd() -> str
#   Pre-condition: settings.codegraph.bin_dir is configured with a directory path
#   Post-condition: Returns an absolute filesystem path resolving to "codegraph" under the configured binary directory when that file exists and is executable; returns the bare string "codegraph" when the pinned binary is absent, delegating resolution to the process PATH

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_175.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
