# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::opencode_trace-py::_deep_merge` (language: `python`).
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
def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` into ``base``; ``overlay`` wins on conflicting
    leaves, nested dicts are merged (mirrors OpenCode's own config merge)."""
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
```

## Specs of this function's callers

### src::opencode_trace-py::_opencode_env

# [SPEC]
# Unit: src/opencode_trace.py
#
# _opencode_env(work_dir, event_id) -> dict
#
# Pre-condition:
#   - work_dir is a path to an existing directory on the filesystem (the fm_agent/
#     workspace directory)
#   - event_id is a non-empty string uniquely identifying a trace event
#
# Post-condition:
#   - Returns a copy of the current process environment (os.environ) with several
#     additional entries applied:
#     - TRACE_DIR: absolute path of the "opencode" subdirectory under the trace
#       directory derived from work_dir; the directory at TRACE_DIR is created if it
#       does not already exist.
#     - TRACE_FILENAME: set to the value of event_id.
#     - PWD: absolute path of the parent directory of work_dir (the project root
#       directory).
#     - If `_opencode_provider_config()` returns a non‑None value (expected to be a
#       dict), then:
#         - LLM_API_KEY is set to the value of `settings.llm.api_key` at call time.
#         - OPENCODE_CONFIG_CONTENT is set to the JSON serialization of a dict
#           produced by deep‑merging any pre‑existing OPENCODE_CONFIG_CONTENT from the
#           original environment with the provider config dict returned by
#           `_opencode_provider_config()`.  The merge gives precedence to the provider
#           config for overlapping keys, while preserving other keys from the
#           original environment.  If the original OPENCODE_CONFIG_CONTENT is not a
#           valid JSON object, it is treated as an empty dict for the merge.
#     - If `_opencode_provider_config()` returns None, no LLM_API_KEY or
#       OPENCODE_CONFIG_CONTENT entries are added (the environment copy may still
#       inherit those keys from the original os.environ unchanged).
#   - All other entries present in the calling process's environment at the time of
#     the call are preserved, except where explicitly overwritten by the rules above.
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_69.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
