# Bug Report: _read_error_body

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the raw HTTP response body decoded as UTF-8 text, with undecodable bytes replaced by the Unicode replacement character (U+FFFD), and leading/trailing whitespace stripped
- When the decoded, stripped text exceeds limit characters, the returned string is truncated to the first limit characters and suffixed with a single "…" (ellipsis) character
- Returns an empty string when: read() raises any exception, read() returns a falsy value, or the decoded text after stripping is empty
- The function tolerates any exception type from read() — callers can invoke it on any exception object without risk of secondary failures

---

### Actual Behavior

If calling exc.read() raises an exception or returns a falsy value (e.g., None or empty bytes), the function returns an empty string. Otherwise, let raw_bytes be the returned bytes. The function decodes raw_bytes using UTF-8 with replacement characters for errors, strips surrounding whitespace, yielding text. It then returns text if its length ≤ limit; otherwise returns the first limit characters of text followed by '…'. Formally: (result : str)(result = '' ∨ ¬RaisedException(exc.read()) ∧ bool(raw_bytes := exc.read()))) ∨ (result = (t[:limit] + '…' if len(t) > limit else t) ∧ ¬RaisedException(exc.read()) ∧ bool(raw_bytes := exc.read()) ∧ t = raw_bytes.decode('utf-8','replace').strip()).

---

## Code Evidence

Line 7:     except Exception:

---

## Trigger Condition

The specification requires that the function returns an empty string when read() raises any exception. The code's except clause only catches exceptions derived from Exception, missing exceptions derived directly from BaseException (e.g., KeyboardInterrupt, SystemExit). This allows such exceptions to propagate, violating the 'any exception' tolerance mandate.

---

## How to trigger the bug

The bug is triggered when `_read_error_body` is called with an object whose `read()` method raises a `BaseException` subclass that is not also an `Exception` subclass (e.g., `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, or a custom `BaseException` subclass). The spec requires returning `""`, but the code's `except Exception:` clause does not catch these exceptions, causing them to propagate.

### Inputs

| Parameter | Value |
|-----------|-------|
| `exc` | Mock object whose `read()` raises `FakeBaseException("simulated read failure")` |
| `limit` | 800 (default) |

### Expected (spec-correct) Output

`""` (empty string)

### Actual (buggy) Output

`FakeBaseException` propagates uncaught

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())

from src.llm_client import _read_error_body

class FakeBaseException(BaseException):
    pass

class Mock:
    def read(self):
        raise FakeBaseException("test")

# actual (buggy) output: FakeBaseException propagates uncaught
# expected (correct) output: ""
result = _read_error_body(Mock())
```

---

## Probe Script

```python
"""Probe script for bug: _read_error_body does not catch BaseException subclasses from read()."""
import sys
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.llm_client import _read_error_body


# Custom exception inheriting directly from BaseException (NOT Exception).
# The spec requires _read_error_body to tolerate ANY exception type from read(),
# but the code uses `except Exception:` which misses direct BaseException subclasses.
class FakeBaseException(BaseException):
    pass


class MockWithRead:
    """Mock whose read() raises FakeBaseException, which is NOT an Exception subclass."""
    def read(self):
        raise FakeBaseException("simulated read failure")


try:
    result = _read_error_body(MockWithRead())
    # If we get here, _read_error_body caught the BaseException → spec is satisfied → bug NOT reproduced
    print(f"NOT CONFIRMED — function returned {result!r} (caught BaseException subclass)")
except FakeBaseException as e:
    # Bug confirmed: BaseException propagated instead of being caught and returning ""
    print(f"CONFIRMED — FakeBaseException propagated: {e} | Spec requires: return '' for any exception from read()")
except BaseException as e:
    print(f"ERROR: unexpected BaseException: {type(e).__name__}: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — FakeBaseException propagated: simulated read failure | Spec requires: return '' for any exception from read()
```
