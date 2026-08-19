# Bug Report: normalize_fqn_label

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/normalize_fqn_label.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string in FM-Agent canonical FQN form: every path-segment separator ('/') is replaced by the FQN separator ('::'), and the file-extension dot immediately preceding a '::' function separator is replaced by a hyphen ('-'). The returned string contains no '/' characters and uses '::' as segment delimiters throughout.

---

### Actual Behavior

The return value is a string derived from the input `label` by replacing every occurrence of the character '/' with the substring '::', and then replacing the file-extension dot (the last occurrence of '.' that is immediately followed by '::') with a hyphen '-'. Formally: let t = label.replace('/', '::'). If there exists an index k such that t[k:k+3] == '.::' and for all indices j > k, t[j:j+3] != '.::', then the returned string r = t[0:k] + '-' + t[k+1:]; otherwise r = t. The returned string is never empty.

---

## Code Evidence

Line 3: return _normalize_endpoint_label(label)

---

## Trigger Condition

The code only replaces a dot immediately followed by '::' (substring '.::'). For an input like 'path/to/file.c::func', after '/' replacement, the string becomes 'path::to::file.c::func' which does not contain '.::', so the file-extension dot is not replaced. The specification requires that the file-extension dot (e.g., before 'c') be replaced by a hyphen, producing 'path::to::file-c::func'. The output 'path::to::file.c::func' contains a dot, violating the spec.

---

## How to trigger the bug

The bug report's description of the actual behavior is incorrect. The actual implementation of `_normalize_endpoint_label` (the helper called by `normalize_fqn_label`) does NOT perform simple `label.replace('/', '::')` followed by replacing `.::`. Instead, it uses `PurePosixPath` to properly parse the path component, extracts the file base name, finds the last dot in the base name, and replaces it with a hyphen. This correctly handles the input `"path/to/file.c::func"` and produces the spec-compliant output `"path::to::file-c::func"`.

The verification LLM appears to have analyzed only the wrapper `normalize_fqn_label` (3 lines) and incorrectly inferred how the helper `_normalize_endpoint_label` operates, assuming a naive string-replacement approach. The actual `_normalize_endpoint_label` (lines 203-214 of `src/call_graph_edges.py`) is more sophisticated and correctly handles this case.

### Inputs

| Parameter | Value |
|-----------|-------|
| label | `"path/to/file.c::func"` |

### Expected (spec-correct) Output

`"path::to::file-c::func"`

### Actual (buggy) Output

N/A — the code does not produce the buggy output. The actual code returns `"path::to::file-c::func"`, which matches the specification exactly.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.call_graph_edges import normalize_fqn_label

result = normalize_fqn_label("path/to/file.c::func")
print(repr(result))
# actual output: 'path::to::file-c::func'
# expected (spec-correct) output: 'path::to::file-c::func'
# buggy output (claimed): 'path::to::file.c::func'
```

---

## Probe Script

```python
"""Probe script for bug src--call_graph_edges-py--normalize_fqn_label.

Verifies whether normalize_fqn_label() produces incorrect output for
"path/to/file.c::func" as claimed in the bug report.
"""

import sys
import os
import tempfile

TMP = tempfile.mkdtemp(prefix="probe_normalize_fqn_")
os.chdir(TMP)

if len(sys.argv) > 1:
    REPO_ROOT = sys.argv[1]
else:
    REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

sys.path.insert(0, REPO_ROOT)

try:
    from src.call_graph_edges import normalize_fqn_label
except Exception as e:
    print(f"ERROR: Failed to import normalize_fqn_label: {e}")
    sys.exit(1)

input_label = "path/to/file.c::func"
expected = "path::to::file-c::func"
buggy_output = "path::to::file.c::func"

try:
    actual = normalize_fqn_label(input_label)
except Exception as e:
    print(f"ERROR: normalize_fqn_label raised: {e}")
    sys.exit(1)

spec_match = actual == expected
bug_confirmed = actual == buggy_output

if bug_confirmed:
    print(f"CONFIRMED — actual: {actual!r} | expected (spec): {expected!r}")
elif spec_match:
    print(f"NOT CONFIRMED — actual matches specification: {actual!r}")
else:
    print(f"NOT CONFIRMED — actual: {actual!r} matches neither expected ({expected!r}) nor buggy ({buggy_output!r})")
```

### Probe Output

```
NOT CONFIRMED — actual matches specification: 'path::to::file-c::func'
```
