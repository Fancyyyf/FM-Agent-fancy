# Bug Report: function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/rust-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If codegraph is available and indexes filepath: returns a list of
    (function_name, start_line, end_line) tuples, one per top-level function
    declared in the file. Each start_line and end_line is a 0-indexed
    inclusive line number bounding the function's source span.
  - If filepath contains no top-level function declarations: returns an
    empty list.
  - If codegraph is unavailable or does not index filepath: returns None.
    A None return signals the caller to fall back to regex-based extraction.

---

### Actual Behavior

If the call `CodeGraphExtractor.from_proj_dir(proj_dir)` raises an exception, `function_spans` raises that exception. Otherwise, let `cg` be the returned value. If `cg` is `None`, the function returns `None`. If `cg` is a `CodeGraphExtractor` instance, then upon evaluating `cg.get_function_spans('rust', filepath)`: if that call raises an exception, `function_spans` raises that exception; else the function returns the result, which is either `None` (when the language key 'rust' is not recognized by the backend or the database contains no entries for `filepath`) or a list of `(name, start_idx, end_idx)` tuples for each function and method definition found in `filepath`, with 0-indexed inclusive line indices, ordered by ascending `start_idx`. The function does not modify any externally observable state beyond any internal state initialized during `from_proj_dir` and the read-only access to the codegraph backend.

---

## Code Evidence

Line 8: return cg.get_function_spans("rust", filepath) if cg else None

---

## Trigger Condition

The code returns the unfiltered list from cg.get_function_spans, which includes all function and method definitions (as documented). The specification requires only top-level function declarations; method definitions inside impl blocks must be excluded. This input contains both a top-level function and a method, causing the code to produce an output that includes the method, violating the requirement.

---

## How to trigger the bug

The `function_spans` function delegates directly to `CodeGraphExtractor.get_function_spans("rust", filepath)` without filtering out methods. The underlying `get_function_spans` queries the codegraph database for both `'function'` and `'method'` kinds (see `src/languages/codegraph.py` line 363: `WHERE kind IN ('function', 'method')`). When a Rust file contains `fn top_level()` and `impl Foo { fn bar() {} }`, the method `Foo::bar` leaks into the result alongside the top-level function, violating the spec's requirement of "one per top-level function declared in the file."

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | `/fake/proj` (mocked — any path) |
| `filepath` | `/fake/proj/src/lib.rs` (mocked — any path) |
| Mocked `get_function_spans` result | `[("top_level", 0, 2), ("Foo::bar", 4, 6)]` |

### Expected (spec-correct) Output

`[("top_level", 0, 2)]` — only the top-level function, method excluded.

### Actual (buggy) Output

`[("top_level", 0, 2), ("Foo::bar", 4, 6)]` — both the top-level function and the method are returned.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock, patch
from src.languages.rust import function_spans

# Simulate a CodeGraphExtractor that returns a mixed list
mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = [
    ("top_level", 0, 2),       # <-- top-level function
    ("Foo::bar", 4, 6),        # <-- method inside impl block
]

with patch("src.languages.rust.CodeGraphExtractor") as mock_cls:
    mock_cls.from_proj_dir.return_value = mock_cg
    result = function_spans("/fake/proj", "/fake/proj/src/lib.rs")

# actual (buggy) output: [("top_level", 0, 2), ("Foo::bar", 4, 6)]
# expected (correct) output: [("top_level", 0, 2)]
print(result)
```

---

## Probe Script

```python
"""Probe: Confirm that function_spans returns methods in addition to top-level functions.

The spec (src/languages/rust.py [SPEC] block) states that function_spans returns
"one per top-level function declared in the file". However, the implementation
delegates to CodeGraphExtractor.get_function_spans, which queries for both
'function' AND 'method' kinds from the codegraph database. Methods inside impl
blocks should be excluded per the spec but are included in practice.

This probe mocks CodeGraphExtractor to return a mixed list and verifies that
methods leak through.
"""
import sys
import os

# Ensure the project root is on sys.path so 'src' imports resolve.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _run_probe():
    from unittest.mock import MagicMock, patch

    # Simulate a Rust file with:
    #   fn top_level() {}       -- top-level function at lines 1-3 (0-indexed: 0-2)
    #   impl Foo { fn bar() {} } -- method inside impl at lines 5-7 (0-indexed: 4-6)
    mock_spans = [
        ("top_level", 0, 2),
        ("Foo::bar", 4, 6),
    ]

    mock_cg = MagicMock()
    mock_cg.get_function_spans.return_value = mock_spans

    with patch("src.languages.rust.CodeGraphExtractor") as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_cg

        from src.languages.rust import function_spans

        result = function_spans("/fake/proj", "/fake/proj/src/lib.rs")

    if result is None:
        return (
            "ERROR",
            "function_spans returned None — expected at least the mocked spans",
        )

    names = [name for name, _, _ in result]

    has_top_level = "top_level" in names
    has_method = "Foo::bar" in names

    # Per spec: only top-level function declarations should be returned.
    # If a method leaked through, the bug is confirmed.
    if has_method:
        return (
            "CONFIRMED",
            "function_spans returned method 'Foo::bar' (inside an impl block) "
            f"in addition to top-level function 'top_level'. "
            f"Spec requires only top-level functions. Full result: {result!r}",
        )
    elif has_top_level and not has_method:
        return (
            "NOT CONFIRMED",
            f"function_spans correctly filtered to only top-level functions: {result!r}",
        )
    else:
        return (
            "NOT CONFIRMED",
            f"Unexpected result (no top-level function found): {result!r}",
        )


if __name__ == "__main__":
    try:
        status, msg = _run_probe()
        print(f"{status} — {msg}")
        if status == "ERROR":
            sys.exit(1)
    except Exception as exc:
        print(f"ERROR — unhandled exception: {exc}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — function_spans returned method 'Foo::bar' (inside an impl block) in addition to top-level function 'top_level'. Spec requires only top-level functions. Full result: [('top_level', 0, 2), ('Foo::bar', 4, 6)]
```
