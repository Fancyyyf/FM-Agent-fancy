# Bug Report: _normalize_endpoint_label

**Source file:** `src/call_graph_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string
  - When the input label represents a function reference qualified by a source-file
    path, the returned FQN has the source-file extension dot in the filename
    replaced with "-", leading "./" stripped, "." and empty parent-directory
    components excluded, and components joined with "::"
  - When the input label does not represent a path-qualified function reference,
    the returned string equals the input
  - The normalization is deterministic: the same input always produces the same
    output

---

### Actual Behavior

The function terminates normally and returns a string r. Let c = _clean_label(label). If _is_path_function_label(c) is False, then r = c. If _is_path_function_label(c) is True, then c can be uniquely decomposed as p + '::' + f where f contains no '::', and r is computed as: let p' = the result of removing all leading occurrences of '.' and '/' from p; let src = PurePosixPath(p'); let b = src.name; let d = b.rfind('.'); let fd = (b[:d] + '-' + b[d+1:]) if d > 0 else b; let dirs = [x for x in src.parent.parts if x not in {'', '.'}]; then r = '::'.join(dirs + [fd, f]).

---

## Code Evidence

Line 5: path = path.lstrip("./")

---

## Trigger Condition

The specification requires stripping only the leading "./" sequence, but the code uses lstrip("./"), which removes all leading occurrences of '.' and '/' individually. For a path starting with "../", this incorrectly removes the parent-directory component "..", leading to a missing ".." in the output, thus violating the specification.

---

## How to trigger the bug

The public API `normalize_fqn_label` delegates to `_normalize_endpoint_label`. Passing a path-qualified label that starts with `"../"` instead of `"./"` triggers the bug: `lstrip("./")` greedily strips all leading `.` and `/` chars including the `..`, destroying the parent-directory component.

### Inputs

| Parameter | Value |
|-----------|-------|
| label | `"../src/test.c::func"` |

### Expected (spec-correct) Output

`"..::src::test-c::func"`

### Actual (buggy) Output

`"src::test-c::func"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.call_graph_edges import normalize_fqn_label

label = "../src/test.c::func"
actual = normalize_fqn_label(label)
expected = "..::src::test-c::func"
print(f"actual:   {actual!r}")
print(f"expected: {expected!r}")
# actual (buggy) output:   'src::test-c::func'
# expected (correct) output: '..::src::test-c::func'
```

---

## Probe Script

```py
import sys
sys.path.insert(0, '.')

try:
    from src.call_graph_edges import normalize_fqn_label
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The spec says: strip only the leading "./" sequence, then exclude "." and
# empty parent-directory components.  ".." is a valid parent-directory ref and
# should be PRESERVED.
# The code uses lstrip("./") which strips ALL leading '.' and '/' chars
# individually, destroying "../" prefixes.
test_cases = [
    # (input, expected per spec)
    ("../src/test.c::func",       "..::src::test-c::func"),
    ("./src/test.c::func",        "src::test-c::func"),
    ("src/test.c::func",          "src::test-c::func"),
    ("../../lib/util.h::do_work", "..::..::lib::util-h::do_work"),
]

confirmed = False
for label, expected in test_cases:
    try:
        actual = normalize_fqn_label(label)
    except Exception as e:
        print(f'ERROR on input {label!r}: {e}')
        sys.exit(1)

    if actual != expected:
        print(f'CONFIRMED — input: {label!r} | actual: {actual!r} | expected: {expected!r}')
        confirmed = True
        break

if not confirmed:
    print('NOT CONFIRMED — all outputs matched expected')
```

### Probe Output

```
CONFIRMED — input: '../src/test.c::func' | actual: 'src::test-c::func' | expected: '..::src::test-c::func'
```
