# Bug Report: _normalize_endpoint_label

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_normalize_endpoint_label.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When label contains at least one '::' and the substring before the last '::' consists of POSIX-path-like components, returns a canonical FQN where: (1) any leading './' prefix in the path portion is removed; (2) the last '.' in the path's final filename component is replaced by '-'; (3) all parent-directory path components excluding '.' and the empty string are joined with '::' to form the FQN prefix; and (4) the function name is appended as the final '::'-separated segment. When label does not match this pattern, returns label unchanged after cleaning.

---

### Actual Behavior

The function returns a new string with no side effects. Let cl = _clean_label(label) (the label with leading and trailing whitespace removed). If _is_path_function_label(cl) returns True, let (path_str, func) = cl.rsplit('::', 1); let stripped_path = path_str.lstrip('./') (removing any leading occurrences of '.' and '/'); let pp = PurePosixPath(stripped_path); let base = pp.name; let last_dot = base.rfind('.'); let func_dir = (base[:last_dot] + '-' + base[last_dot+1:]) if last_dot > 0 else base; let parts = [p for p in pp.parent.parts if p not in {'', '.'}]; then the return value is '::'.join(parts + [func_dir, func]). Otherwise, the return value is cl. Formally: 
result = ( (lambda cl: (lambda path_str, func: (lambda stripped_path: (lambda pp: (lambda base: (lambda last_dot: (lambda func_dir: (lambda parts: '::'.join(parts + [func_dir, func]))([p for p in pp.parent.parts if p not in {'', '.'}]))((base[:last_dot] + '-' + base[last_dot+1:]) if last_dot > 0 else base))(base.rfind('.')))(pp.name))(PurePosixPath(stripped_path)))(path_str.lstrip('./')))(*cl.rsplit('::', 1)) if _is_path_function_label(cl) else cl )(_clean_label(label))

---

## Code Evidence

Line 5: path = path.lstrip("./")

---

## Trigger Condition

The specification requires removing only a leading './' prefix, but lstrip('./') removes all leading '.' and '/' characters, so '../foo::func' incorrectly becomes 'foo::func' instead of '..::foo::func'.

---

## How to trigger the bug

The bug is triggered by passing a label containing a `../` path prefix. The function uses `str.lstrip("./")` which removes ALL leading `.` and `/` characters, rather than removing only the exact prefix `./`. This causes parent-directory path components like `..` to be silently stripped, producing an incorrect FQN that omits the parent directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| label | `../foo.c::func` |

### Expected (spec-correct) Output

`..::foo-c::func`

### Actual (buggy) Output

`foo-c::func`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.call_graph_edges import normalize_fqn_label

label = "../foo.c::func"
result = normalize_fqn_label(label)
# actual (buggy) output: 'foo-c::func'
# expected (correct) output: '..::foo-c::func'
```

---

## Probe Script

```py
import sys
import os

# Ensure the repo root is on the import path (public entry-point rule)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.call_graph_edges import normalize_fqn_label

    # Input that triggers the bug: path with parent dir ".." prefix
    # lstrip("./") in _normalize_endpoint_label removes ALL leading '.' and '/'
    # characters, so "../foo.c::func" loses the ".." parent component.
    label = "../foo.c::func"

    actual = normalize_fqn_label(label)
    # Spec-correct: only leading "./" prefix stripped, so ".." parent is preserved
    expected = "..::foo-c::func"

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'foo-c::func' | expected: '..::foo-c::func'
```
