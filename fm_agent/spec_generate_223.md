# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::prompts-py::_parse_spec_check_json::_nonempty_string` (language: `python`).
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
def _nonempty_string(value):
        return isinstance(value, str) and bool(value.strip())
```

## Specs of this function's callers

### src::prompts-py::_parse_spec_check_json

# [SPEC]
# Unit: src/prompts-py/_parse_spec_check_json.py
#
# _parse_spec_check_json(response)
#
# Pre-condition:
#   - response is a non-empty string
#
# Post-condition:
#   - Raises ValueError if response is not valid JSON text
#   - Raises ValueError if the parsed JSON value is not a mapping (dict)
#   - Raises ValueError if the parsed mapping does not contain all of the required keys: "verdict", "counterexample", "offending_statements", "reason"
#   - Raises ValueError if the "verdict" value, after conversion to uppercase, is neither "MATCH" nor "MISMATCH"
#   - Raises ValueError if "counterexample" is present and not null-valued but is not a string
#   - Raises ValueError if "offending_statements" is present and not null-valued but is not a string
#   - Raises ValueError if "reason" is not a string value
#   - For "MISMATCH" verdict: raises ValueError if any of counterexample, offending_statements, or reason is empty or consists only of whitespace; otherwise returns a tuple (True, offending_statements_with_leading_trailing_whitespace_removed, reason_with_whitespace_removed, data) where data is the parsed dict with verdict uppercased, counterexample set to the stripped value, offending_statements set to the stripped value, and reason set to the stripped value
#   - For "MATCH" verdict: raises ValueError if counterexample or offending_statements is a non-empty string; otherwise returns a tuple (False, None, None, data) where data is the parsed dict with verdict uppercased, counterexample set to None, offending_statements set to None, and reason set to its stripped value
# [SPEC]

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_223.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
