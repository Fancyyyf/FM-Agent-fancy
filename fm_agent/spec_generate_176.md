# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::_warn_on_codegraph_version_mismatch` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: run.

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
```

## Specs of this function's callers

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

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_176.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
