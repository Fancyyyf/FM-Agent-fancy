# Bug Report: _safe_staged_name

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/domain_knowledge-py/_safe_staged_name.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string not present in used_names before the call. The string is derived from the basename of source_path:
- Characters in the stem not matching [A-Za-z0-9._-] are replaced with '_'.
- Leading and trailing characters matching [._-] are stripped from the stem.
- When the stem is empty after sanitization, 'knowledge' is used as the stem.
- The extension is lowercased.
- The returned name is <stem><extension> when that string is not in used_names; otherwise it is <stem>_<n><extension> where <n> is the smallest integer >= 2 such that the resulting string avoids collision with every name in used_names.
- The returned name is added to used_names as a side effect.

---

### Actual Behavior

Let used_pre be the set of strings passed as `used_names` before execution, and used_post after execution. The function returns a string `ret` such that:
- ret ∈ used_pre
- used_post = used_pre ∪ {ret}
Define:
  base = os.path.basename(source_path)
  raw_stem, raw_ext = os.path.splitext(base)
  cleaned = (re.sub(r"[^A-Za-z0-9._-]+", "_", raw_stem).strip("._-") or "knowledge")
  ext = raw_ext.lower()
Then ret = cleaned + ext if cleaned + ext ∉ used_pre; otherwise there exists an integer n ≥ 2 such that:
  ret = cleaned + "_" + str(n) + ext
  ∀ m with 2 ≤ m < n, cleaned + "_" + str(m) + ext ∈ used_pre
  cleaned + "_" + str(n) + ext ∉ used_pre

---

## Code Evidence

Line 4: stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "knowledge"

---

## Trigger Condition

The code collapses sequences of invalid characters into a single underscore, but the specification requires each invalid character to be replaced individually, causing a different sanitized stem. For input 'a  b.txt', the code produces 'a_b.txt' while the specification expects 'a__b.txt'.

---

## How to trigger the bug

The bug is in `_safe_staged_name()` in `src/domain_knowledge.py`. The regex `[^A-Za-z0-9._-]+` uses the `+` quantifier, which causes consecutive invalid characters to be collapsed into a single underscore. The specification states that each invalid character must be individually replaced with `_`.

For input `source_path = "a  b.txt"` (two spaces between "a" and "b"), the two spaces form one sequence matched by `[^A-Za-z0-9._-]+`, resulting in a single underscore: `"a_b.txt"`. The specification requires each space to be individually replaced, producing `"a__b.txt"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| source_path | `"a  b.txt"` |
| used_names | `set()` (empty set) |

### Expected (spec-correct) Output

`"a__b.txt"`

### Actual (buggy) Output

`"a_b.txt"`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from domain_knowledge import _safe_staged_name

source_path = "a  b.txt"  # two spaces between a and b
used_names = set()

# actual (buggy) output: 'a_b.txt'
# expected (correct) output: 'a__b.txt'
print(repr(_safe_staged_name(source_path, used_names)))
```

---

## Probe Script

```python
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src"))

try:
    from domain_knowledge import _safe_staged_name

    source_path = "a  b.txt"
    used_names = set()

    actual = _safe_staged_name(source_path, used_names)
    expected = "a__b.txt"
    passed = actual != expected
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'a_b.txt' | expected: 'a__b.txt'
```
