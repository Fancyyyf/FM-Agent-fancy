# Bug Report: _plan_spec_update

**Source file:** `/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_plan_spec_update.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when any of the following holds:
       fqn is absent from file_map, or the resolved file path does not exist on disk
       the file's extension maps to no language key in EXT_TO_LANG
       after consulting the LLM, no spec change is indicated
        (result["spec_updated"] is absent or falsy)
       the new spec string produced by the LLM is empty after stripping whitespace
  - When a pre-existing spec comment block is absent, a fresh spec is generated
    by sending the full source and caller context to an LLM that writes a
    behavioral [SPEC]/[INFO] block from scratch; when a pre-existing block exists,
    a lighter LLM call determines whether the block needs rewriting
  - Otherwise returns a dict (the "apply plan") with exactly these keys:
      fqn: the input FQN (string)
      fpath: the absolute path to the extracted-function file (string)
      write_content: a string whose first byte is the new [SPEC] block, followed
        by a blank line, optionally followed by the [INFO] block and a blank line,
        and ending with the original function source code; the source portion is
        byte-for-byte identical to the input source (only leading spec comments
        are replaced)
      new_spec: the raw [SPEC] block text including its delimiters (string)
      info_updated: True if and only if an [INFO] block was either created for
        the first time or replaced with different content (bool)
      updated_callees: a list of short callee names (the last component of each
        callee FQN) whose own specs were reported as updated by the LLM that
        produced this plan (list of strings, may be empty)
  - This function performs LLM calls and disk reads but performs no file writes;
    the caller is responsible for applying write_content to the file at fpath
  - When the function returns a plan, write_content begins with a comment-prefixed
    [SPEC] marker line and ends with the line-...

---

### Actual Behavior

The function does not modify any global state. It may raise exceptions from file I/O, `_extract_leading_spec_comments`, or the LLM helper calls (`_opencode_generate_spec`, `_llm_check_spec_update`).

On normal termination, the return value `r` satisfies:

1. Early returns produce `None`:
   - If `fpath = file_map.get(fqn)` is falsy or `os.path.isfile(fpath)` is `False` (lines 1112).
   - If the file extension `ext` (from `fpath.rsplit('.')`) is not in `EXT_TO_LANG` (line 1516).
   - After obtaining `result`, if `result` is falsy or `result.get('spec_updated')` is falsy (line 4344).
   - If `new_spec = (result.get('new_spec') or '').strip()` is empty (line 4647).

2. Otherwise, a plan dictionary is constructed and returned (line 7178) with the following keys:
   - `"fqn"`: the input `fqn`.
   - `"fpath"`: the resolved file path.
   - `"write_content"`: the new spec block (and optional info block, if any) followed by two newlines and the original source code stripped of leading newlines.
   - `"new_spec"`: the stripped spec text.
   - `"info_updated"`: a boolean indicating whether the info block was updated by the LLM.
   - `"updated_callees"`: a list of callee FQNs reported as updated, or an empty list.

The logic for `new_info`, `info_block`, and `info_updated` depends on whether an existing specification was present (`leading`). When `leading` is `None` (fresh generation), any `new_info` produced by `_opencode_generate_spec` is used; `info_block` is that info or `None`; `info_updated` is `True` iff `new_info` is nonempty. When `leading` is not `None` (existing spec), the existing `old_info` is kept unless `result` indicates an update and a nonempty `new_info` is provided, in which case `info_block` is replaced and `info_updated` becomes `True`.

---

## Code Evidence

Line 77:             "updated_callees": result.get("updated_callees") or [],

---

## Trigger Condition

The specification requires updated_callees to contain short callee names (last component of each callee FQN). The code passes through the LLM response directly without extracting the short name, so if the LLM returns FQNs, the returned plan violates the specification.

---

## How to trigger the bug

The function `_plan_spec_update` (line 1625 in `src/incremental_reasoner.py`) constructs a return dict where `"updated_callees"` is set to `result.get("updated_callees") or []` at line 1708. This passes through whatever the LLM returns in `result["updated_callees"]` without transforming the values. The specification requires that this field contain **short callee names** — only the last component of each FQN (e.g., `"func_name"` from `"src::module::func_name"`).

In contrast, the same function correctly extracts short names for `callee_names` at line 1649 using:
```python
callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})
```

The same transformation (`c.split("::")[-1]`) is missing from the `updated_callees` assignment at line 1708.

### Inputs

| Parameter | Value |
|-----------|-------|
| `result["updated_callees"]` (from LLM) | `["src::network::http::send_request", "src::database::pool::_get_connection", "src::utils::parse_config", "short_name_only"]` |

### Expected (spec-correct) Output

`["send_request", "_get_connection", "parse_config", "short_name_only"]`

### Actual (buggy) Output

`["src::network::http::send_request", "src::database::pool::_get_connection", "src::utils::parse_config", "short_name_only"]`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.incremental_reasoner

# Simulate an LLM result that returns FQNs in updated_callees
mock_result = {
    "updated_callees": [
        "src::network::http::send_request",
        "src::database::pool::_get_connection",
        "src::utils::parse_config",
    ],
}

# Line 1708: the buggy code pattern
actual = mock_result.get("updated_callees") or []
# actual: ['src::network::http::send_request', 'src::database::pool::_get_connection', 'src::utils::parse_config']

# What the spec requires (short names, line 1649 pattern)
expected = [c.split("::")[-1] for c in actual]
# expected: ['send_request', '_get_connection', 'parse_config']

assert actual != expected  # bug confirmed — FQNs passed through verbatim
```

---

## Probe Script

```python
"""Probe for bug: _plan_spec_update does not extract short callee names from updated_callees.

The specification requires updated_callees to contain "short callee names (the last component
of each callee FQN)". At line 1708, the code uses:

    "updated_callees": result.get("updated_callees") or [],

which passes through whatever the LLM returns without extracting short names via split("::")[-1].

Contrast with line 1649 where callee_names is correctly derived:

    callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})

This probe demonstrates the discrepancy without invoking the full FM-Agent workflow
by testing the exact code pattern found at line 1708 against the specification.
"""

import sys

# ── Reproduce the exact code pattern from line 1708 ──────────────────────────
# This is the buggy line:
#     "updated_callees": result.get("updated_callees") or [],

# Simulate an LLM result that returns FQNs (fully-qualified names) instead
# of short names in updated_callees.  The specification demands short names.
mock_result_with_fqns = {
    "spec_updated": True,
    "new_spec": "# [SPEC]\n# Unit: src/module.py\n# some_func() -> int\n# [SPEC]",
    "updated_callees": [
        "src::network::http::send_request",       # FQN, not short name
        "src::database::pool::_get_connection",   # FQN
        "src::utils::parse_config",               # FQN
        "short_name_only",                        # already a short name
    ],
}

# What line 1708 ACTUALLY does (passes through verbatim — BUGGY):
actual_from_code = mock_result_with_fqns.get("updated_callees") or []

# What line 1649 does for callee_names (extracts short names — CORRECT pattern):
#     callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})
# The equivalent transformation for updated_callees would be:
expected_by_spec = [c.split("::")[-1] for c in actual_from_code]

# ── Classification ──────────────────────────────────────────────────────────
# The spec says updated_callees must contain "short callee names (the last
# component of each callee FQN)".  If the LLM returns FQNs, the code passes
# them through without extracting short names — a clear spec violation.

bug_reproduced = actual_from_code != expected_by_spec

if bug_reproduced:
    print(
        "CONFIRMED — "
        f"actual (raw pass-through, FQNs): {actual_from_code!r} | "
        f"expected (short names per spec): {expected_by_spec!r}"
    )
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_from_code!r}")
```

### Probe Output

```
CONFIRMED — actual (raw pass-through, FQNs): ['src::network::http::send_request', 'src::database::pool::_get_connection', 'src::utils::parse_config', 'short_name_only'] | expected (short names per spec): ['send_request', '_get_connection', 'parse_config', 'short_name_only']
```
