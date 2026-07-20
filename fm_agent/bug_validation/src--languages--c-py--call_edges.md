# Bug Report: call_edges

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/c-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when no codegraph backend for the C language can be initialized
    from proj_dir; this signals the caller to fall back to regex-based call-edge
    detection for this language
  - Otherwise returns a dict where each key is a fully-qualified caller function
    name and each value is a set of fully-qualified callee function names that the
    caller directly invokes
  - An empty dict (distinct from None) indicates the backend initialized successfully
    but found zero call edges

---

### Actual Behavior

Returns either None if the internal CodeGraphExtractor initialization fails (i.e., CodeGraphExtractor.from_proj_dir(proj_dir) returns None), or a dictionary where each key is a tuple (caller_stem, caller_module) and the corresponding value is a set of callee stems representing the direct function calls from that caller to its callees, as produced by cg.get_call_edges('c'). No side effects occur.

---

## Code Evidence

Line 4: return cg.get_call_edges("c") if cg else None

---

## Trigger Condition

Condition A states the code returns a dictionary where keys are (caller_stem, caller_module) tuples and values are sets of callee stems. Specification B requires keys to be fully-qualified caller function name strings and values to be sets of fully-qualified callee function names. The output format is structurally incompatible: for any successful initialization with call edges, the keys and values are not fully-qualified names, violating the specification.

---

## How to trigger the bug

The bug report claims the function returns tuples `(caller_stem, caller_module)` as keys and stems as values. However, the actual code delegates to `CodeGraphExtractor.get_call_edges("c")`, which returns a dict with **string keys** (FQNs in the format `"dir::file-ext::name"`) and **set-of-string values** (also FQNs). This format exactly matches the specification.

The mismatch arose because the extracted function's **docstring** says `Return {(caller_stem, caller_module): {callee_stems}}`, which is inaccurate. But the actual runtime behavior of `CodeGraphExtractor.get_call_edges` (see `src/languages/codegraph.py` lines 301-376, specifically `_fqn_for` and `_node_fqn_map`) produces FQN strings, not tuples. The docstring is misleading, but the code itself is correct and matches the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot` (or any project directory with a codegraph DB) |

### Expected (spec-correct) Output

`{str_fqn: set_of_str_fqns, ...}` — keys are fully-qualified caller function name strings; values are sets of fully-qualified callee function name strings.

### Actual (buggy) Output

`{str_fqn: set_of_str_fqns, ...}` — same as expected. The actual return value matches the specification exactly. Keys are `str` (e.g. `'dashboard-py::_cost_from_usage'`), values are `set` of `str` (e.g. `{'dashboard-py::_price_for'}`).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")
from src.languages.c import call_edges

result = call_edges("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")
# result is either None (no codegraph DB) or a dict {str_fqn: {str_fqn, ...}}
# The keys and values are fully-qualified name strings, NOT tuples.
# actual (buggy) output: dict with str keys → matches spec; NOT a bug
# expected (correct) output: dict with FQN string keys → what the spec requires
```

---

## Probe Script

```python
"""Probe script for bug src--languages--c-py--call_edges.

Bug claim: call_edges() returns {(caller_stem, caller_module): {callee_stems}}
Spec requires: dict with FQN string keys → set of FQN string values

This script verifies the actual return format of get_call_edges, which is the
underlying method used by src.languages.c.call_edges (and all other languages).
"""
import sys

sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")

try:
    # Use the public entry point for C (the function in question)
    from src.languages.c import call_edges

    proj_dir = "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot"

    # Test 1: C language — call through public API
    result_c = call_edges(proj_dir)
    assert result_c is not None, "Expected non-None dict (codegraph DB exists)"
    assert isinstance(result_c, dict), f"Expected dict, got {type(result_c)}"
    # Empty dict is valid — backend initialized, zero C edges in this DB

    # Test 2: Verify the underlying get_call_edges format using Python (has edges)
    from src.languages.codegraph import CodeGraphExtractor

    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    assert cg is not None, "CodeGraphExtractor should initialize"

    result_py = cg.get_call_edges("python")
    assert isinstance(result_py, dict), f"Expected dict, got {type(result_py)}"
    assert len(result_py) > 0, "Expected non-empty dict for Python"

    # Inspect the format of keys and values
    actual_bug = False
    sample_key = next(iter(result_py.keys()))
    sample_vals = result_py[sample_key]
    sample_val = next(iter(sample_vals))

    # Spec says: keys must be FQN strings, values must be sets of FQN strings
    key_is_str = isinstance(sample_key, str)
    val_is_str = isinstance(sample_val, str)
    val_is_set = isinstance(sample_vals, set)

    # Docstring claims: keys are tuples of (stem, module), values are sets of stems
    key_is_tuple = isinstance(sample_key, tuple)

    if not key_is_tuple and key_is_str and val_is_set and val_is_str:
        # Keys are strings (FQNs), NOT tuples. Values are sets of FQN strings.
        # The actual behavior MATCHES the specification.
        # The docstring is wrong, but the code is correct.
        passed = False  # Bug NOT confirmed
    else:
        passed = True  # Bug confirmed

    spec_claim = (
        "{caller_fqn: {callee_fqn, ...}} — string keys and set-of-string values"
    )
    actual_format = f"key={type(sample_key).__name__}({repr(sample_key[:60])}), "
    actual_format += f"value_type={type(sample_vals).__name__}, "
    actual_format += f"value_element={type(sample_val).__name__}({repr(sample_val[:60])})"

    if passed:
        print(f"CONFIRMED — actual: {actual_format} | expected: {spec_claim}")
    else:
        print(
            f"NOT CONFIRMED — actual matches expected: {actual_format}"
        )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — actual matches expected: key=str('dashboard-py::_cost_from_usage'), value_type=set, value_element=str('dashboard-py::_price_for')
```
