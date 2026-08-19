# Bug Report: append_event

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/trace_writer-py/append_event.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Thread-safely appends the event dict as a single, self-contained JSON line (terminated by a newline character) to the events.jsonl file located within trace_dir. The written JSON preserves every top-level key from the provided event dict. The function does not modify the event dict argument. If the trace_dir directory hierarchy does not exist, it is created before the write. On filesystem write failure (e.g., disk full, permission denied), an OSError propagates to the caller.

---

### Actual Behavior

Normal execution: The function returns None. The lock `_LOCK` is acquired and released. The file `os.path.join(trace_dir, 'events.jsonl')` has a new line appended containing `json.dumps(event, ensure_ascii=False) + '\\n'`. The directory `trace_dir` exists (created if necessary by `_ensure_trace_dirs`).

Exceptional paths:
- `_ensure_trace_dirs` raises `OSError`: The function exits with `OSError`. No lock is acquired. No file write occurs. No side effects on the event file.
- `json.dumps` raises `TypeError`: The function exits with `TypeError`. The trace directory may have been created (if `_ensure_trace_dirs` succeeded), but no lock is acquired and no file write occurs.
- File operations (`open` or `write`) raise `OSError` while the lock is held: The lock is released (guaranteed by the `with` statement). The trace directory exists (created if needed). The file may be partially written or unchanged; no atomicity guarantee. The `OSError` propagates.

Formal:
post  
  (returns None  
   directory_exists(trace_dir)  
   appended_line(file_path, json.dumps(event, ensure_ascii=False) + '\\n')  
   lock_released(_LOCK))
   raises OSError from _ensure_trace_dirs (no file modifications)
   raises TypeError from json.dumps (directory may exist, no file modifications)
   raises OSError from file I/O (directory exists, lock released, file state undefined)

---

## Code Evidence

Line 4: line = json.dumps(event, ensure_ascii=False)

---

## Trigger Condition

The code calls json.dumps(event) on the input dict unconditionally. If the event dict contains a top-level key that is not a valid JSON key (e.g., a tuple), json.dumps raises TypeError. The specification (B) only allows for OSError propagation on filesystem write failure and does not account for TypeError. The input event={(1,2): 'value'} is a valid dict, yet the codes behavior (TypeError) violates the specified post-condition, which does not include this exceptional outcome.

---

## How to trigger the bug

The bug is triggered by passing an event dict that contains a non-string key (e.g., a tuple `(1, 2)`). Python's `json.dumps` raises `TypeError` because JSON requires all keys to be strings. The specification only accounts for `OSError` propagation on filesystem write failure and does not document `TypeError` as a possible exceptional path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `trace_dir` | any writable directory path |
| `event` | `{(1, 2): "value"}` |

### Expected (spec-correct) Output

The function should either:
- Reject the invalid input and raise a documented exception, or
- Convert non-string keys to strings before serialization.

The specification does not account for TypeError propagation, so the behavior (raising TypeError from `json.dumps`) is undocumented and violates the spec.

### Actual (buggy) Output

`TypeError: keys must be str, int, float, bool or None, not tuple`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from src.trace_writer import append_event

with tempfile.TemporaryDirectory() as tmpdir:
    append_event(tmpdir, {(1, 2): "value"})
# actual (buggy) output: TypeError: keys must be str, int, float, bool or None, not tuple
# expected (correct) output: function either handles non-string keys gracefully or raises a documented exception
```

---

## Probe Script

```python
import sys
import tempfile
import os

# Ensure the repo root is on sys.path so that `src.trace_writer` resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.trace_writer import append_event

    # Create a temporary directory for the probe (following the rule:
    # all test fixtures must live under a fresh temporary directory)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Input with a non-string dict key (tuple), which json.dumps cannot serialize
        # The spec only permits OSError propagation; TypeError violates the spec
        buggy_event = {(1, 2): "value"}

        actual = None
        passed = False

        try:
            actual = append_event(tmpdir, buggy_event)
            # If we reach here, no exception was raised — bug NOT confirmed
            passed = False
        except TypeError:
            # TypeError raised — this confirms the bug
            passed = True
        except OSError:
            # OSError is permitted by the spec — not the bug we're looking for
            passed = False
        except Exception:
            # Some other exception — not the expected bug
            passed = False

    expected = "No TypeError (spec only permits OSError propagation)"
    if passed:
        print(f"CONFIRMED — TypeError raised when json.dumps encounters non-serializable dict key {(1,2)!r}; spec only permits OSError")
    else:
        print(f"NOT CONFIRMED — no TypeError raised; actual returned: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — TypeError raised when json.dumps encounters non-serializable dict key (1, 2); spec only permits OSError
```
