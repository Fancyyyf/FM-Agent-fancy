# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::opencode_trace-py::_opencode_provider_config` (language: `python`).
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
def _opencode_provider_config():
    """Build an OpenCode ``provider`` block from FM-Agent's own LLM settings.

    ``fm-agent.toml`` is the single source of truth for provider / base URL /
    model: instead of the user hand-writing (and keeping in sync) a provider
    block in ``~/.config/opencode/opencode.json``, FM-Agent injects an equivalent
    block into the OpenCode subprocess via ``OPENCODE_CONFIG_CONTENT``. That is
    OpenCode's highest-precedence config source, so it wins over any same-named
    provider in the user's ``opencode.json``; OpenCode deep-merges per key, so
    other providers and the ``plugin`` array in that file are preserved.

    Returns ``None`` (injecting nothing) unless we have every field needed to
    build a working block — provider, base URL, model, and an API key. Without a
    key the injected ``{env:LLM_API_KEY}`` would be empty and would clobber a
    working config, so we stay out of the way and leave OpenCode's own config in
    effect.
    """
    llm = settings.llm
    if not (llm.api_key and llm.base_url and llm.name and llm.provider):
        return None
    adapter = (
        "@ai-sdk/anthropic"
        if llm.api_style == "anthropic"
        else "@ai-sdk/openai-compatible"
    )
    return {
        "provider": {
            llm.provider: {
                "npm": adapter,
                "options": {
                    "baseURL": llm.base_url,
                    # Resolved by OpenCode from the child env (set below), so the
                    # key is never written to a config file on disk.
                    "apiKey": "{env:LLM_API_KEY}",
                },
                "models": {llm.name: {}},
            }
        }
    }
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
4. Write your answer to `fm_agent/spec_generate_70.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
