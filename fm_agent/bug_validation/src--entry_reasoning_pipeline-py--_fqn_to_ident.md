# Bug Report: _fqn_to_ident

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_fqn_to_ident.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the class-qualified identifier portion of fqn: the tail after the source-file component (the component whose rightmost hyphen-separated token is a known language file extension). If no source-file component is found, returns the last '::'-delimited component of fqn.

---

### Actual Behavior

Let parts = fqn.split('::') and n = len(parts). The function returns a string result determined as follows: the code searches from i = n-1 down to 0 to find the first (i.e., rightmost) component where parts[i].rfind('-') returns a position h > 0 and the substring parts[i][h+1:] is a key in the global dictionary EXT_TO_LANG. If such an index i0 is found, the function immediately returns '::'.join(parts[i0+1:]). Otherwise (if no component satisfies the condition), it returns parts[-1] (the last component). If n = 1, the loop over indices is empty and result equals parts[0].

---

## Code Evidence

Line 14: if hyphen > 0 and comp[hyphen + 1:] in EXT_TO_LANG:

---

## Trigger Condition

The code's condition requires hyphen > 0, so it rejects components like '-cpp' that start with a hyphen even though the spec treats the rightmost hyphen-separated token 'cpp' as a valid extension. For input 'src::-cpp::foo::bar', the spec expects 'foo::bar' (tail after the source-file component '-cpp'), but the code returns 'bar' because it does not recognize '-cpp' as a source-file component.

---

## How to trigger the bug

The function `_fqn_to_ident` incorrectly rejects source-file components that start with a hyphen (e.g., `-cpp`). The condition `hyphen > 0` on line 129 of the source file (`src/entry_reasoning_pipeline.py`) requires the hyphen to not be at position 0, which means any source-file directory beginning with `-<ext>` is ignored even though the spec clearly states the component is identified by the rightmost hyphen-separated token being a known language file extension.

### Inputs

| Parameter | Value |
|-----------|-------|
| fqn | `src::-cpp::foo::bar` |

### Expected (spec-correct) Output

`foo::bar`

### Actual (buggy) Output

`bar`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.entry_reasoning_pipeline import _fqn_to_ident

# The fqn 'src::-cpp::foo::bar' contains a source-file component '-cpp'
# where 'cpp' is a known extension in EXT_TO_LANG.
result = _fqn_to_ident("src::-cpp::foo::bar")
# actual (buggy) output: 'bar'
# expected (correct) output: 'foo::bar'
```

---

## Probe Script

```python
"""Probe script for bug src--entry_reasoning_pipeline-py--_fqn_to_ident.

The bug: _fqn_to_ident at line 129 uses `hyphen > 0` which rejects
components like `-cpp` (where rfind("-") returns 0). For input
`src::-cpp::foo::bar`, the spec expects `foo::bar` but the code returns `bar`
because `-cpp` is not recognized as a source-file component.
"""

import sys
import os

# Add repo root to path so the import works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.entry_reasoning_pipeline import _fqn_to_ident

    # Test case: input where the source-file component starts with a hyphen
    actual = _fqn_to_ident("src::-cpp::foo::bar")
    expected = "foo::bar"
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'bar' | expected: 'foo::bar'
```
