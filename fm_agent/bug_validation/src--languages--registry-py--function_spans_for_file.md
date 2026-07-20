# Bug Report: function_spans_for_file

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/registry-py/function_spans_for_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When lang_key is not present in REGISTRY, returns None
  - When lang_key is present in REGISTRY, returns the registered handler's
    function_spans result for (proj_dir, filepath) without modification
  - A non-None return value is a list where each element is a tuple (name, start, end):
      * name is the function name string
      * start is the 0-based inclusive start-line index of a top-level function body
      * end is the 0-based inclusive end-line index of a top-level function body
  - None signals codegraph unavailability; the caller must fall back to regex extraction

---

### Actual Behavior

Natural language: If `lang_key` is not present in `REGISTRY` (i.e., `REGISTRY.get(lang_key)` returns `None`), the function returns `None` immediately. Otherwise, it delegates to `handler.function_spans(proj_dir, filepath)` and returns whatever that call returns. The return value is therefore either `None` (when the handler does not support the file, the file is not in the codegraph index, or the language is unregistered) or a list of tuples `(func_name, start_idx, end_idx)` where `start_idx` and `end_idx` are 0based inclusive line numbers; `handler.function_spans` never returns anything else according to its specification. If the call to `handler.function_spans` raises an exception, that exception is not caught and propagates to the caller; in that case no normal return occurs.

Formal logic: Let \( H = \text{REGISTRY.get}(\text{lang_key}) \). 
If \( H = \text{None} \), then the function terminates normally and \( \text{returned\_value} = \text{None} \). 
If \( H \neq \text{None} \), then exactly one of the following holds:
- The call \( H.\text{function\_spans}(\text{proj\_dir}, \text{filepath}) \) evaluates normally to \( R \), and \( R = \text{None} \) or \( R \) is a finite list of triples \((s_i, e_i, n_i)\) where each \( s_i, e_i \in \mathbb{Z} \), \( 0 \le s_i \le e_i \), and `str` type for names; the function then returns \( R\).
- The call raises an exception \( E \), and the function terminates abruptly with the same exception \( E \).
The postcondition does not constrain the values of `proj_dir`, `filepath`, or `lang_key` (they are immutable strings and remain unchanged).

---

## Code Evidence

Line 12: return handler.function_spans(proj_dir, filepath)

---

## Trigger Condition

The specification requires that when codegraph cannot provide spans, the function returns None to signal unavailability and let the caller fall back. However, if handler.function_spans raises an exception (e.g., due to a missing file or internal error), the code does not catch it, so the exception propagates. This violates the contract that the function must always return either a list or None; the caller never receives the fallback signal.

---

## How to trigger the bug

The buggy function `function_spans_for_file` (in `src/languages/registry.py`, line 68-80) delegates to the registered language handler's `function_spans` method. When the handler raises an exception instead of returning a value, the exception propagates through `function_spans_for_file` uncaught, violating the specification that says the function must always return either a list or None.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot` |
| `filepath` | `src/languages/registry.py` |
| `lang_key` | `"python"` (registered in REGISTRY, handler monkey-patched to raise) |

### Expected (spec-correct) Output

`None` — the specification requires that when codegraph is unavailable or fails, the function returns None so the caller can fall back to regex extraction.

### Actual (buggy) Output

`RuntimeError: Simulated codegraph internal failure` — the exception propagates to the caller instead of being caught and converted to None.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.languages.registry import function_spans_for_file, REGISTRY

class BrokenHandler:
    def batch_extract(self, proj_dir): return {}
    def call_edges(self, proj_dir): return {}
    def function_spans(self, proj_dir, filepath):
        raise RuntimeError("Simulated codegraph internal failure")

original = REGISTRY.get("python")
REGISTRY["python"] = BrokenHandler()
try:
    function_spans_for_file("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot", "src/languages/registry.py", "python")
    # actual (buggy) output: raises RuntimeError
    # expected (correct) output: None
finally:
    if original:
        REGISTRY["python"] = original
```

---

## Probe Script

```py
import sys
try:
    from src.languages.registry import function_spans_for_file, REGISTRY

    # Monkey-patch the python handler to simulate an internal codegraph failure
    # that raises instead of returning None — triggering the exception-propagation bug.
    class _BrokenHandler:
        def batch_extract(self, proj_dir):
            return {}
        def call_edges(self, proj_dir):
            return {}
        def function_spans(self, proj_dir, filepath):
            raise RuntimeError("Simulated codegraph internal failure")

    original = REGISTRY.get("python")
    REGISTRY["python"] = _BrokenHandler()

    exception_raised = False
    actual = None
    try:
        result = function_spans_for_file(
            "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot",
            "src/languages/registry.py",
            "python",
        )
        actual = result
    except RuntimeError as e:
        exception_raised = True
        actual = f"{type(e).__name__}: {e}"
    except Exception as e:
        exception_raised = True
        actual = f"{type(e).__name__}: {e}"
    finally:
        if original is not None:
            REGISTRY["python"] = original
        else:
            del REGISTRY["python"]

    expected = None  # spec: "None signals codegraph unavailability; the caller must fall back"

    if exception_raised:
        print(f"CONFIRMED — exception propagated instead of returning None: {actual}")
    elif actual != expected:
        print(f"NOT CONFIRMED — returned {actual!r} instead of {expected!r}")
    else:
        print(f"NOT CONFIRMED — returned None (spec-correct behavior)")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — exception propagated instead of returning None: RuntimeError: Simulated codegraph internal failure
```
