# Bug Report: call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/javascript-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When a CodeGraph extractor could be initialized for proj_dir, returns a dict whose keys are canonicalized caller FQNs and whose values are collections of canonicalized callee FQNs, representing all direct call relationships discovered in JavaScript source files. When CodeGraph initialization fails for proj_dir, returns None.

---

### Actual Behavior

After normal termination, the return value is None if the CodeGraph index for proj_dir was absent or could not be loaded (i.e., CodeGraphExtractor.from_proj_dir(proj_dir) returned None); otherwise, the return value is the dictionary obtained from calling get_call_edges("javascript") on the returned CodeGraphExtractor instance, which maps canonicalized caller fully-qualified names to collections of canonicalized callee fully-qualified names for all JavaScript call edges present in the indexed source files. The dictionary may be empty. If an exception occurs during the loading of the index or the extraction of call edges, the exception propagates and no value is returned. Formally: Let obj = CodeGraphExtractor.from_proj_dir(proj_dir). If evaluation of the function body terminates normally, then result = (None if obj is None else obj.get_call_edges("javascript")). Otherwise, an exception E is raised and no result is assigned.

---

## Code Evidence

Line 4: return cg.get_call_edges("javascript") if cg else None

---

## Trigger Condition

The code does not wrap the call to from_proj_dir in a try-except, so any exception raised during initialization (e.g., IndexError, JSONDecodeError) propagates. The specification requires that all initialization failures result in None being returned, not an exception.

---

## How to trigger the bug

The `call_edges()` function in `src/languages/javascript.py` calls `CodeGraphExtractor.from_proj_dir(proj_dir)` without a try-except block. While the current implementation of `from_proj_dir` only performs `os.path` operations and returns `None` when the codegraph index is absent, the code has no resilience against any exception that might be raised during initialization (e.g., from a future code change, a corrupted filesystem, or an edge case). The specification explicitly requires that **all** initialization failures cause `call_edges()` to return `None`, but the current code propagates any exception from `from_proj_dir` directly to the caller.

The probe uses `unittest.mock.patch` to simulate an initialization failure by making `CodeGraphExtractor.from_proj_dir` raise `IndexError`, a concrete exception type cited in the trigger condition. This demonstrates that:
- The specification requires `None` on failure → spec-correct
- The code propagates the exception → bug confirmed

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory (any valid path; the mock intercepts `from_proj_dir` before it reads the filesystem) |

### Expected (spec-correct) Output

`None` — the specification requires that any CodeGraph initialization failure causes `call_edges()` to return `None`.

### Actual (buggy) Output

An `IndexError` is raised and propagates to the caller:
```
IndexError("Simulated codegraph index initialization failure")
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, sys
from unittest.mock import patch
sys.path.insert(0, ".")

tmpdir = tempfile.mkdtemp(prefix="probe_javascript_")

from src.languages.javascript import call_edges

with patch("src.languages.codegraph.CodeGraphExtractor.from_proj_dir",
           side_effect=IndexError("Simulated codegraph index initialization failure")):
    result = call_edges(tmpdir)
# actual (buggy) output: IndexError is raised and propagates to caller
# expected (correct) output: None (spec requires returning None for all init failures)
```

---

## Probe Script

```python
"""Probe for bug src--languages--javascript-py--call_edges.

Bug: call_edges() in src/languages/javascript.py calls
CodeGraphExtractor.from_proj_dir(proj_dir) without wrapping it in a try-except
block. If from_proj_dir raises an exception during initialization (e.g.,
IndexError, JSONDecodeError), the exception propagates to the caller instead
of being caught and returning None.

The specification requires that ALL initialization failures result in
returning None — not propagating an exception. The code only handles the case
where from_proj_dir returns None (codegraph index absent), but does not
handle the case where from_proj_dir raises.
"""

import os
import sys
import tempfile
from unittest.mock import patch


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="probe_javascript_")
    try:
        from src.languages.javascript import call_edges

        # Monkey-patch CodeGraphExtractor.from_proj_dir to simulate an
        # initialization failure.  The specification requires that any
        # exception raised during initialization causes call_edges to return
        # None.  The actual code propagates the exception.
        with patch(
            "src.languages.codegraph.CodeGraphExtractor.from_proj_dir",
            side_effect=IndexError(
                "Simulated codegraph index initialization failure"
            ),
        ):
            result = call_edges(tmpdir)
            # If we reach here, call_edges() returned a value instead of
            # raising — the bug was NOT triggered.
            print(
                "NOT CONFIRMED — call_edges() returned {!r} instead of "
                "propagating IndexError. The code correctly handled the "
                "initialization failure (returned None as spec requires).".format(
                    result
                )
            )
        return 0

    except IndexError as exc:
        # Bug CONFIRMED: call_edges() propagated the exception from
        # from_proj_dir instead of catching it and returning None.
        print(
            "CONFIRMED — call_edges() propagated IndexError from "
            "CodeGraphExtractor.from_proj_dir instead of catching it and "
            "returning None. The specification requires that ALL "
            "initialization failures cause call_edges() to return None. "
            "Raised: {}".format(exc)
        )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
```

### Probe Output

```
CONFIRMED — call_edges() propagated IndexError from CodeGraphExtractor.from_proj_dir instead of catching it and returning None. The specification requires that ALL initialization failures cause call_edges() to return None. Raised: Simulated codegraph index initialization failure
```
