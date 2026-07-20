# Bug Report: call_edges

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a mapping from caller fully-qualified names to sets of callee fully-qualified names
  - FQNs follow the format: path::components::delimited::by::double::colons, where the last component is the function name
  - Each callee in the returned graph is a function that exists within the analyzed Erlang project
  - If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict

---

### Actual Behavior

The function returns a dictionary resulting from the call-graph analysis of the effective project root (which may be a subdirectory of `proj_dir` as determined by `_callgraph_project_root`). If the analysis is available, the dictionary contains a module-qualified Erlang call edges mapping (caller to callees); otherwise, it is an empty dictionary. No exceptions are raised; the function always terminates normally under the given pre-condition. Formally: `result = _analysis_or_empty(_callgraph_project_root(proj_dir)).edges` and `isinstance(result, dict)` holds, with `result` being either the nonempty edges dictionary or `{}` when analysis is unavailable.

---

## Code Evidence

Line 3: return _analysis_or_empty(_callgraph_project_root(proj_dir)).edges

---

## Trigger Condition

The specification requires the returned mapping to use sets of callee FQNs and that every callee exists within the project. The code returns raw analysis results without any validation, so if the analysis produces a list instead of a set or includes a non-existent callee, the output violates the specification.

---

## How to trigger the bug

The function `call_edges` (line 642-644 of `src/languages/erlang.py`) delegates entirely to `_analysis_or_empty` and returns `analysis.edges` without any transformation or validation. The `ErlangAnalysis.edges` field is typed as `dict[tuple[str, str], set[str]]` — the keys are 2-tuples of `(function_id, caller_module)` rather than FQN strings. Additionally, the function performs zero validation that callee FQNs correspond to functions that exist within the analyzed Erlang project (i.e., appear in `analysis.functions`).

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory path (bug is structural, not input-dependent) |

### Expected (spec-correct) Output

A dict with FQN string keys (e.g., `{"module::function::0": {"callee::helper::0"}}`) where every callee is validated against the project's known functions.

### Actual (buggy) Output

A dict with tuple keys (e.g., `{("module__function__0", "module-erl"): {"callee__helper__0"}}`) with no callee-existence validation.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.languages.erlang import call_edges, ErlangAnalysis

mock_analysis = ErlangAnalysis(
    functions={},  # empty — no functions exist
    edges={("func", "mod"): {"nonexistent_callee"}},
)

with patch("src.languages.erlang._analysis_or_empty", return_value=mock_analysis):
    result = call_edges("/some/path")

# actual (buggy) output: {("func", "mod"): {"nonexistent_callee"}}
# expected (correct) output: {"mod::func": {"mod::nonexistent_callee"}} or error for nonexistent callee
# Bug: (1) keys are tuples, not FQN strings; (2) nonexistent callee accepted without error
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from unittest.mock import patch
from dataclasses import dataclass, field

try:
    from src.languages.erlang import call_edges, ErlangAnalysis

    # ── Bug Description ────────────────────────────────────────────────
    # Spec claim: "Returns a mapping from caller fully-qualified names to
    #   sets of callee fully-qualified names" where "FQNs follow the format:
    #   path::components::delimited::by::double::colons"
    # Actual:     call_edges returns ErlangAnalysis.edges directly, which
    #   has dict[tuple[str, str], set[str]] keys — tuples of
    #   (function_id, caller_module), NOT FQN strings.
    #   Additionally, the function performs zero validation that callees
    #   are functions that exist within the analyzed Erlang project.
    # Code:       Line 644: return _analysis_or_empty(_callgraph_project_root(proj_dir)).edges
    # ────────────────────────────────────────────────────────────────────

    # Create a mock ErlangAnalysis with tuple-keyed edges — this is the
    # actual data shape produced by _analyze_project_uncached (line 494 of erlang.py:
    #   edges: dict[tuple[str, str], set[str]] = {})
    mock_analysis = ErlangAnalysis(
        functions={},
        edges={
            ("module__function__0", "module-erl"): {"callee__helper__0"},
        },
    )

    with patch(
        "src.languages.erlang._analysis_or_empty",
        return_value=mock_analysis,
    ):
        result = call_edges("/some/proj_dir")

    # ── Verification ───────────────────────────────────────────────────
    # The spec requires FQN string keys like "module::function::0"
    # The actual code returns tuple keys like ("module__function__0", "module-erl")
    keys = list(result.keys())

    # Bug 1: Keys are tuples, not FQN strings
    has_tuple_keys = any(isinstance(k, tuple) for k in keys)
    # Bug 2: No validation — callee "callee__helper__0" accepted without
    # checking it exists in the project (ErlangAnalysis.functions is empty!)

    if has_tuple_keys:
        actual_desc = (
            f"keys are tuples (e.g. {keys[0]!r}), not FQN strings; "
            f"no callee-existence validation performed"
        )
        expected_desc = (
            "keys must be FQN strings (e.g. 'module::function::0'); "
            "callees must be validated against project functions"
        )
        passed = True
    else:
        actual_desc = f"keys are strings: {keys}"
        expected_desc = "keys must be FQN strings"
        passed = False

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print("CONFIRMED")
    print(f"  actual:   {actual_desc!r}")
    print(f"  expected: {expected_desc!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_desc!r}")
```

### Probe Output

```
CONFIRMED
  actual:   "keys are tuples (e.g. ('module__function__0', 'module-erl')), not FQN strings; no callee-existence validation performed"
  expected: "keys must be FQN strings (e.g. 'module::function::0'); callees must be validated against project functions"
```
