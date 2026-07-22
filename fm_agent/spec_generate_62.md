# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::env_check-py::_check_codegraph_version` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _codegraph_cmd, run.

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
```

## Specs of this function's callers

### src::env_check-py::run

# [SPEC]
# Unit: src/env_check-py/run.py
#
# run(proj_dir: str, config) -> bool
#
# Pre-condition:
#   - proj_dir is a directory path that exists on the filesystem.
#   - config provides access to an LLM API key (the specific accessor used is LLM_API_KEY).
#
# Post-condition:
#   - Returns True when any of the following holds: (a) all environment checks pass with no
#     warnings, (b) one or more checks fail but the session is non-interactive, (c) one or
#     more checks fail in an interactive session and the user chooses to proceed ('p'), or
#     (d) one or more checks fail in an interactive session and the user chooses to permanently
#     ignore the failing checks ('i').
#   - Returns False only when one or more checks fail in an interactive session and the user
#     chooses to quit ('q'). No persistent state is modified in this case.
#   - When the user chooses 'i', the union of all previously ignored check IDs and the IDs of
#     all currently failing checks is persisted to proj_dir/fm_agent/.env_check_memory, causing
#     all such checks to be skipped on subsequent calls.
#   - Checks whose ID appears in the persisted ignore set (loaded at the start of the call)
#     are skipped entirely: their check function is not invoked.
#   - Each failing check produces a warning logged via logging.warning in the format
#     "[!] <label>: <message>" where label identifies the check and message is the
#     reason for failure.
#   - The directory proj_dir/fm_agent/ is created if it does not already exist.
#   - In interactive mode, the function blocks on user input and does not return until a
#     valid choice (p, i, or q) is entered.
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_62.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
