# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::entry_reasoning_pipeline-py::_fqn_to_ident` (language: `python`).
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
def _fqn_to_ident(fqn):
    """Return a function's class-qualified identifier: the FQN tail after the
    ``<base>-<ext>`` source-file component.

        src::storage-cpp::LocalStorage::Flush -> LocalStorage::Flush
        src::checkpoint-cpp::RunCheckpoint     -> RunCheckpoint

    This is exactly the name run_extraction wrote (as the flat filename stem)
    and _function_spans reports, so trim keeps/removes the right same-name method
    instead of collapsing LocalStorage::Flush and WriteAheadLog::Flush together.
    """
    parts = fqn.split("::")
    for i in range(len(parts) - 1, -1, -1):
        comp = parts[i]
        hyphen = comp.rfind("-")
        if hyphen > 0 and comp[hyphen + 1:] in EXT_TO_LANG:
            return "::".join(parts[i + 1:])
    return parts[-1]
```

## Specs of this function's callers

### src::entry_reasoning_pipeline-py::_select_functions_by_source

# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py
#
# _select_functions_by_source(proj_dir, entry_func, end_funcs, extra_call_edges=None) -> (dict[str, set[str]], dict[str, set[str]])
#
# Pre-condition:
#   - proj_dir is an existing directory (the project root)
#   - entry_func is a non-empty fully-qualified function name string
#   - end_funcs is an iterable of zero or more fully-qualified function name strings
#   - extra_call_edges, when provided, contributes supplemental call edges through a
#     format recognized by _build_call_graph
#
# Post-condition:
#   - proj_dir is never mutated; all mutations occur in a temporary sibling directory
#     that is destroyed before this function returns
#   - Returns a tuple (all_by_source, keep_by_source) where:
#     - all_by_source is a dict mapping each source-file relative path to the set of
#       ALL function names that were extractable from that source file
#     - keep_by_source is a dict mapping each source-file relative path to the set of
#       function names that are transitively reachable from entry_func in the static
#       call graph; when end_funcs is non-empty, this set is further restricted to
#       function names that lie on at least one call-chain path from entry_func to
#       some member of end_funcs
#   - Raises ValueError when:
#     - No extractable source files are found under proj_dir
#     - No extractable functions are found under proj_dir
#     - entry_func is not among the extracted functions
#     - end_funcs is non-empty and no member of end_funcs is reachable from entry_func
#       in the call graph
#   - When extra_call_edges is provided, its supplemental edges contribute to the call
#     graph used for reachability analysis
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_145.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
