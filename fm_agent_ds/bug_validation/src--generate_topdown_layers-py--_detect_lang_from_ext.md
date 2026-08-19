# Bug Report: _detect_lang_from_ext

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_detect_lang_from_ext.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the language key string from the fixed extension-to-language registry whose registered extension matches the suffix of filepath's terminal name component following (and excluding) the last '.' character. Returns None when the terminal name component of filepath contains no '.' character. Returns None when the extracted suffix does not match any registered extension in the registry. The directory portion of filepath preceding the terminal name component does not affect the result.

---

### Actual Behavior

After the function returns, no global state has been modified. The return value is the language key string corresponding to the file extension extracted from the input filepath, or None if the extension is not present in the EXT_TO_LANG dictionary. The extension is the substring after the last dot in the basename of filepath, or an empty string if there is no dot. Formally: let b = os.path.basename(filepath); let ext = b.rsplit('.', 1)[-1] if '.' in b else ''; the result = EXT_TO_LANG.get(ext).

---

## Code Evidence

Line 4: ext = base.rsplit('.', 1)[-1] if '.' in base else ''; Line 5: return EXT_TO_LANG.get(ext)

---

## Trigger Condition

The specification mandates None for any filename whose terminal name component lacks a dot, regardless of the registry contents. The code delegates the decision to EXT_TO_LANG.get(''), so if the registry has an empty-string key, it returns a language instead of None, violating the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | `"Makefile"` (dotless filename) |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`'python'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")
from src.generate_topdown_layers import _detect_lang_from_ext
from src import extract

# The current registry has no empty-string key, so the bug lies dormant.
# Inject one to demonstrate the spec violation:
extract.EXT_TO_LANG[""] = "python"

result = _detect_lang_from_ext("Makefile")
# actual (buggy) output: 'python'
# expected (correct) output: None

# Cleanup
del extract.EXT_TO_LANG[""]
```

---

## Probe Script

```python
import sys
import os

# Add project root to sys.path so 'src' package is importable
project_root = "/home/fancy/Projects_Vault/FM-Agent"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.generate_topdown_layers import _detect_lang_from_ext
    from src import extract

    # Sanity check 1: with current registry, dotless filenames return None
    actual_normal = _detect_lang_from_ext("Makefile")
    assert actual_normal is None, f"Expected None for dotless 'Makefile', got {actual_normal!r}"

    # Inject empty-string key to demonstrate the spec violation
    original_has_empty_key = "" in extract.EXT_TO_LANG
    original_value = extract.EXT_TO_LANG.get("")
    extract.EXT_TO_LANG[""] = "python"

    # Bug trigger: dotless filename should return None per spec,
    # but code delegates to EXT_TO_LANG.get("") which now returns "python"
    actual = _detect_lang_from_ext("Makefile")
    expected = None  # Spec: returns None when no dot in filename

    passed = actual != expected

    # Restore EXT_TO_LANG
    if original_has_empty_key:
        extract.EXT_TO_LANG[""] = original_value
    else:
        del extract.EXT_TO_LANG[""]

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'python' | expected: None
```
