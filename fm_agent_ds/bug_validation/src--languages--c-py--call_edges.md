# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/c-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the CodeGraph backend is available for the C language, returns a dict whose keys are canonicalized caller FQN strings and whose values are iterables of canonicalized callee FQN strings, representing static call relationships in the project. FQNs use the canonicalized format where unsafe characters are translated and components are joined by '::'. When the CodeGraph backend is unavailable for C, returns None. An empty dict is returned when the backend is available but discovers no call edges for the language.

---

### Actual Behavior

The function returns None if CodeGraphExtractor.from_proj_dir(proj_dir) fails (indicated by returning None), otherwise it returns a dictionary mapping each caller's canonicalized fully qualified name (FQN) string to an iterable of canonicalized callee FQN strings for the C language. Formally: let cg = CodeGraphExtractor.from_proj_dir(proj_dir). Then (cg is None → call_edges returns None) ∧ (cg is not None → call_edges returns cg.get_call_edges("c")), where cg.get_call_edges("c") is a dict with string keys and iterable-of-string values representing C call edges. No other side effects occur.

---

## Code Evidence

Line 4: return cg.get_call_edges("c") if cg else None

---

## Trigger Condition

When the overall CodeGraph backend is available but the C backend is not, the specification requires returning None. The code calls cg.get_call_edges('c') unconditionally if cg is not None; if 'c' is not a supported language key, get_call_edges may raise an exception or return a nondict value, violating the specification's requirement to return None for an unavailable C backend.

---

## How to trigger the bug

The bug manifests when `CodeGraphExtractor.from_proj_dir(proj_dir)` returns a non-None value (the `.codegraph/codegraph.db` exists, so the overall CodeGraph backend is available), but the C language is not supported by the backend — for example, if `_CG_LANG` does not contain the `"c"` key. In that case, `get_call_edges("c")` returns `{}` (an empty dict, per the internal fallback `if not cg_langs: return {}`), and `call_edges` returns that dict instead of `None` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory where `.codegraph/codegraph.db` exists but C is unsupported by `_CG_LANG` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`{}` (empty dict)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock, patch
from src.languages.c import call_edges

mock_cg = MagicMock()
mock_cg.get_call_edges.return_value = {}

with patch("src.languages.c.CodeGraphExtractor.from_proj_dir", return_value=mock_cg):
    result = call_edges("/fake/proj_dir")
    print(repr(result))
# actual (buggy) output: {}
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug src--languages--c-py--call_edges.

Scenario: CodeGraph backend exists (from_proj_dir returns a valid extractor),
but C backend is unavailable (not in _CG_LANG). The spec requires returning None,
but the code calls cg.get_call_edges("c") unconditionally, returning a non-None value.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the repo root is on the path so 'src' is importable.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)


def main():
    try:
        from src.languages.c import call_edges

        # Simulate: CodeGraph DB exists (from_proj_dir returns a mock extractor),
        # but get_call_edges("c") returns {} because "c" is not in _CG_LANG
        # (mirrors the actual _CG_LANG fallback: if not cg_langs → return {})
        mock_cg = MagicMock()
        mock_cg.get_call_edges.return_value = {}

        with patch(
            "src.languages.c.CodeGraphExtractor.from_proj_dir",
            return_value=mock_cg,
        ) as _mock_from:
            actual = call_edges("/fake/proj_dir")

        # Spec claim: "When the CodeGraph backend is unavailable for C, returns None."
        expected = None
        passed = actual != expected

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected: {expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: {} | expected: None
```
