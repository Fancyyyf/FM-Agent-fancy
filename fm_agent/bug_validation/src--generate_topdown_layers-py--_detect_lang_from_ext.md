# Bug Report: _detect_lang_from_ext

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/generate_topdown_layers-py/_detect_lang_from_ext.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the programming language key string associated with the file's
    extension in the global language-to-extension mapping; the returned key
    is one of the language identifiers recognized by the FM-Agent pipeline
  - Returns None if and only if the file's extension is not present in the
    language-to-extension mapping

---

### Actual Behavior

The function returns the value from the global dictionary EXT_TO_LANG corresponding to the file's extension if the extension is a key in EXT_TO_LANG; otherwise returns None. The extension is the substring after the last '.' in the basename of filepath. Formally, let base = os.path.basename(filepath) and ext = base.rsplit('.', 1)[-1] (the pre-condition ensures '.' exists in base and ext is nonempty). Then the return value is EXT_TO_LANG[ext] if ext  dom(EXT_TO_LANG) else None.

---

## Code Evidence

Line 4: ext = base.rsplit(".", 1)[-1] if "." in base else ""

---

## Trigger Condition

The code strips the leading dot from the extension (e.g., 'py' instead of '.py'). If the global EXT_TO_LANG mapping keys include the dot (e.g., ".py"), the code returns None because it looks up 'py', but the specification requires returning the language key when the file's extension is in the mapping. This causes a mismatch where a valid mapping entry is missed.

---

## How to trigger the bug

The trigger condition is hypothetical — it describes a mismatch that would occur **only if** `EXT_TO_LANG` keys included a leading dot. In the current codebase, `EXT_TO_LANG` (defined in `src/extract.py`, lines 159–170) uses **dotless** keys exclusively (e.g., `"py"`, `"cpp"`, `"c"`, `"go"`). The function `_detect_lang_from_ext` also strips the leading dot via `rsplit(".", 1)[-1]`, producing dotless extensions (e.g., `"py"` for `"foo.py"`). Because both sides are consistent, the lookup succeeds for all current entries and the function behaves correctly.

**Root cause of the reported mismatch:** The logic verifier likely compared the spec ("associated with the file's extension") against the actual behavior (dot-stripped lookup) and flagged a semantic gap — the spec does not clarify whether extensions include the leading dot, while the code consistently uses dotless extensions. However, in the current implementation, the `EXT_TO_LANG` dictionary and the extraction logic are aligned, so the bug is **not reproducible** with the existing data.

### Inputs

| Parameter | Value |
|-----------|-------|
| `filepath` | `"test.py"` |
| `filepath` | `"foo.cpp"` |
| `filepath` | `"foo.xyz"` |
| `filepath` | `"foo"` |

### Expected (spec-correct) Output

`"python"` for `"test.py"`, `"cpp"` for `"foo.cpp"`, `None` for `"foo.xyz"` and `"foo"`

### Actual (buggy) Output

`"python"` for `"test.py"`, `"cpp"` for `"foo.cpp"`, `None` for `"foo.xyz"` and `"foo"`

The actual output matches the expected output in all cases.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.generate_topdown_layers import _detect_lang_from_ext
from src.extract import EXT_TO_LANG

# Check: does EXT_TO_LANG have any dotted keys?
dotted = [k for k in EXT_TO_LANG if k.startswith('.')]
print(f"Dotted keys in EXT_TO_LANG: {dotted}")  # currently: []

# All current lookups succeed because keys are dotless
print(_detect_lang_from_ext("test.py"))   # 'python' (correct)
print(_detect_lang_from_ext("foo.cpp"))   # 'cpp'    (correct)
print(_detect_lang_from_ext("foo.xyz"))   # None     (correct)
```

To actually trigger the bug, one would need to add a dotted key to `EXT_TO_LANG`:

```python
# Hypothetical scenario that WOULD trigger the bug:
EXT_TO_LANG[".py"] = "python"  # adding a dotted key
_detect_lang_from_ext("test.py")  # returns None (BUG) — looks up "py", not ".py"
```

---

## Probe Script

```python
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))

try:
    from src.generate_topdown_layers import _detect_lang_from_ext
    from src.extract import EXT_TO_LANG

    # Check EXT_TO_LANG key format
    dotted_keys = [k for k in EXT_TO_LANG.keys() if k.startswith('.')]
    dotless_keys = [k for k in EXT_TO_LANG.keys() if not k.startswith('.')]

    print(f"EXT_TO_LANG total keys: {len(EXT_TO_LANG)}")
    print(f"EXT_TO_LANG dotted keys (e.g. '.py'): {dotted_keys}")
    print(f"EXT_TO_LANG dotless keys (e.g. 'py'): {dotless_keys}")

    # Test 1: .py file should return "python"
    actual1 = _detect_lang_from_ext("test.py")
    expected1 = "python"
    print(f"\nTest 1: _detect_lang_from_ext('test.py')")
    print(f"  Actual:   {actual1!r}")
    print(f"  Expected: {expected1!r}")

    # Test 2: .cpp file should return "cpp"
    actual2 = _detect_lang_from_ext("foo.cpp")
    expected2 = "cpp"
    print(f"\nTest 2: _detect_lang_from_ext('foo.cpp')")
    print(f"  Actual:   {actual2!r}")
    print(f"  Expected: {expected2!r}")

    # Test 3: unknown extension should return None
    actual3 = _detect_lang_from_ext("foo.xyz")
    expected3 = None
    print(f"\nTest 3: _detect_lang_from_ext('foo.xyz')")
    print(f"  Actual:   {actual3!r}")
    print(f"  Expected: {expected3!r}")

    # Test 4: no extension should return None (empty string lookup)
    actual4 = _detect_lang_from_ext("foo")
    expected4 = None
    print(f"\nTest 4: _detect_lang_from_ext('foo')")
    print(f"  Actual:   {actual4!r}")
    print(f"  Expected: {expected4!r}")

    # Determine overall verdict
    all_passed = (
        actual1 == expected1 and
        actual2 == expected2 and
        actual3 == expected3 and
        actual4 == expected4
    )

    if all_passed:
        print("\nNOT CONFIRMED — function behaves correctly with current EXT_TO_LANG (dotless keys match dot-stripped extension lookup)")
    else:
        print(f"\nCONFIRMED — mismatch detected: function returns unexpected values")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
EXT_TO_LANG total keys: 18
EXT_TO_LANG dotted keys (e.g. '.py'): []
EXT_TO_LANG dotless keys (e.g. 'py'): ['cpp', 'cc', 'cxx', 'c', 'h', 'hpp', 'py', 'erl', 'go', 'rs', 'java', 'ts', 'tsx', 'js', 'jsx', 'cu', 'cuh', 'ets']

Test 1: _detect_lang_from_ext('test.py')
  Actual:   'python'
  Expected: 'python'

Test 2: _detect_lang_from_ext('foo.cpp')
  Actual:   'cpp'
  Expected: 'cpp'

Test 3: _detect_lang_from_ext('foo.xyz')
  Actual:   None
  Expected: None

Test 4: _detect_lang_from_ext('foo')
  Actual:   None
  Expected: None

NOT CONFIRMED — function behaves correctly with current EXT_TO_LANG (dotless keys match dot-stripped extension lookup)
```
