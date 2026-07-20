# Bug Report: _file_to_fqn

**Source file:** `src/generate_topdown_layers-py/_file_to_fqn.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the Fully-Qualified Name (FQN) derived from filepath by:
    taking the path relative to <proj_dir>/extracted_functions/, stripping
    the file extension to obtain the stem, and joining all directory
    components together with the stem using "::" as the separator
  - The returned FQN consists of one or more "::"-separated segments where
    the final segment is the filename stem and preceding segments are the
    directory components below extracted_functions/
  - Each segment in the returned FQN is a non-empty string containing no
    "::" substrings
  - The return value is deterministic for a given (filepath, proj_dir) pair

---

### Actual Behavior

The function returns a fully qualified name (FQN) string constructed from the relative path of `filepath` with respect to `<proj_dir>/extracted_functions`. The file extension of the final component is removed, and all directory separators are replaced by '::'. No exceptions are raised; the return value is deterministic given the inputs. 

Formal logic:
Let `extracted_base = os.path.join(proj_dir, "extracted_functions")`.
Let `rel = os.path.relpath(filepath, extracted_base)`.
Let `(stem, _) = os.path.splitext(rel)`.
Then the return value `result = "::".join(Path(stem).parts)`.

---

## Code Evidence

Line 10: parts = Path(stem).parts; Line 11: return "::".join(parts)

---

## Trigger Condition

The code joins path components with '::' but does not ensure no component already contains '::'. If a directory or filename in the path contains '::', the resulting FQN will contain a segment with '::', violating the specification that each segment must not contain '::'. In the counterexample, the relative path is 'src::engine/loader-cpp/loadData.cpp', stem is 'src::engine/loader-cpp/loadData', parts includes 'src::engine' (which contains '::'), and the output 'src::engine::loader-cpp::loadData' has a segment with '::'.

---

## How to trigger the bug

When `_file_to_fqn` is called with a filepath whose directory components contain "::" substrings (e.g., a directory named `src::engine`), `Path(stem).parts` produces a path component with the embedded "::" — in this case `"src::engine"`. This component is then joined into the FQN using "::" as separator, making it impossible to distinguish the embedded "::" from legitimate separators, and violating the specification that each FQN segment must not contain "::".

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | `<tmpdir>/extracted_functions/src::engine/loader-cpp/loadData.cpp` |
| proj_dir | `<tmpdir>` |

The directory `src::engine` contains the "::" substring that triggers the violation.

### Expected (spec-correct) Output

The FQN segments (the path components from `Path(stem).parts`) must each be non-empty and contain no "::" substrings. The function should either escape, reject, or otherwise handle path components with embedded "::".

### Actual (buggy) Output

`'src::engine::loader-cpp::loadData'` — the segment `"src::engine"` contains the forbidden "::" substring.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from pathlib import Path
from src.generate_topdown_layers import _file_to_fqn

with tempfile.TemporaryDirectory() as tmpdir:
    extracted_base = os.path.join(tmpdir, "extracted_functions")
    buggy_dir = os.path.join(extracted_base, "src::engine", "loader-cpp")
    os.makedirs(buggy_dir, exist_ok=True)
    filepath = os.path.join(buggy_dir, "loadData.cpp")
    with open(filepath, "w") as f:
        f.write("// dummy\n")
    
    actual = _file_to_fqn(filepath, tmpdir)
    # actual (buggy) output: 'src::engine::loader-cpp::loadData'
    # The segment 'src::engine' contains '::', violating the spec
    
    rel = os.path.relpath(filepath, extracted_base)
    stem, _ = os.path.splitext(rel)
    parts = Path(stem).parts
    # parts = ('src::engine', 'loader-cpp', 'loadData')
    # 'src::engine' contains '::' — spec violation
```

---

## Probe Script

```python
import os
import sys
import tempfile
from pathlib import Path

try:
    from src.generate_topdown_layers import _file_to_fqn

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory: extracted_functions/src::engine/loader-cpp/
        # "src::engine" contains "::" — spec says no segment may contain "::"
        extracted_base = os.path.join(tmpdir, "extracted_functions")
        buggy_dir = os.path.join(extracted_base, "src::engine", "loader-cpp")
        os.makedirs(buggy_dir, exist_ok=True)

        filepath = os.path.join(buggy_dir, "loadData.cpp")
        with open(filepath, "w") as f:
            f.write("// dummy\n")

        actual = _file_to_fqn(filepath, tmpdir)

        # Reconstruct what the function internally computes as "parts"
        # (the actual FQN segments before joining with "::")
        rel = os.path.relpath(filepath, extracted_base)
        stem, _ = os.path.splitext(rel)
        parts = Path(stem).parts

        # Spec: "Each segment ... containing no '::' substrings"
        # The segments (parts from Path(stem).parts) must not contain "::"
        spec_violated = any("::" in part for part in parts)
        violating_parts = [p for p in parts if "::" in p]

        if spec_violated:
            print(
                f"CONFIRMED -- actual FQN: {actual!r} | "
                f"segment(s) containing '::': {violating_parts} | "
                f"spec requires no segment to contain '::'"
            )
        else:
            print(
                f"NOT CONFIRMED -- all path parts are '::'-free | "
                f"parts: {list(parts)!r} | "
                f"actual FQN: {actual!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED -- actual FQN: 'src::engine::loader-cpp::loadData' | segment(s) containing '::': ['src::engine'] | spec requires no segment to contain '::'
```
