# Bug Report: render_header

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/render_header.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Panel renderable with a cyan border containing a
    single line of metadata as its body
  - The body line contains four items separated by bullet
    characters, in order: the literal text "FM-Agent Dashboard", the
    working directory from state.workdir, the model identifier from
    state.model_seen (or "?" when model_seen is falsy or absent),
    and the formatted elapsed duration derived from state.elapsed()
  - All items after the dashboard title are styled dimmed relative
    to the title

---

### Actual Behavior

The function returns a rich Panel object representing a header with the state's workdir, model_seen (or '?' if None), and formatted elapsed time. The state object is unchanged. Formal logic: result = Panel(Text.from_markup('    '.join([...])))   attr  {workdir, model_seen, elapsed}: state.attr = old(state.attr).

---

## Code Evidence

Line 5: f"[dim]model:[/] {state.model_seen or '?'}"

---

## Trigger Condition

The specification requires that when model_seen is absent, the output should use '?'. The code directly accesses state.model_seen, causing an AttributeError for an absent attribute, thus not returning any Panel.

---

## How to trigger the bug

The bug occurs when `render_header()` is called with a state object that lacks the `model_seen` attribute (as opposed to having it set to `None`). The expression `state.model_seen or '?'` evaluates `state.model_seen` first — if the attribute does not exist, Python raises `AttributeError` before ever reaching the `or '?'` fallback.

### Inputs

| Parameter | Value |
|-----------|-------|
| state.workdir | `/fake/project` |
| state.model_seen | *(absent — attribute does not exist)* |
| state.elapsed() | `42.0` |

### Expected (spec-correct) Output

`Panel(Text.from_markup("FM-Agent Dashboard  •  workdir: /fake/project  •  model: ?  •  elapsed: 42s"), border_style="cyan")`

### Actual (buggy) Output

`AttributeError: 'MockNoModelSeen' object has no attribute 'model_seen'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import render_header

class MockNoModelSeen:
    workdir = "/fake/project"
    def elapsed(self):
        return 42.0

state = MockNoModelSeen()
result = render_header(state)  # raises AttributeError
# AttributeError: 'MockNoModelSeen' object has no attribute 'model_seen'
```

---

## Probe Script

```python
"""Probe script for bug: dashboard-py--render_header
Bug: render_header() uses `state.model_seen or '?'` which raises AttributeError
when model_seen attribute is absent, violating the spec that requires '?' in that case.
"""
import sys
from pathlib import Path

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from dashboard import render_header

    # Create a mock state that has workdir and elapsed() but NO model_seen
    class MockNoModelSeen:
        workdir = "/fake/project"
        def elapsed(self):
            return 42.0

    state = MockNoModelSeen()

    # Expected: render_header should use '?' when model_seen is absent (per spec)
    # Actual: state.model_seen raises AttributeError before reaching `or '?'`
    result = render_header(state)

    # If we got here without error, check if the output contains '?'
    result_str = str(result)
    has_question_mark = "'?'" in result_str or '?' in result_str
    # Also verify no crash — the panel was returned
    if has_question_mark:
        print("NOT CONFIRMED — function handled absent model_seen gracefully, output contains '?'")
    else:
        print(f"NOT CONFIRMED — function did not crash but did not use '?' for absent model_seen: {result_str[:200]}")

except AttributeError as e:
    # Bug confirmed: state.model_seen access raised AttributeError
    print(f"CONFIRMED — AttributeError when model_seen is absent: {e}")
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError when model_seen is absent: 'MockNoModelSeen' object has no attribute 'model_seen'
```
