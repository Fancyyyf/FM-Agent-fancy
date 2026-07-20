# Bug Report: render_stages

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/render_stages.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Rich Panel renderable whose title is "Stages" and whose
    border is styled cyan
  - The panel contains a table with one row for each stage name in
    STAGES, in iteration order, and no other rows
  - For each stage, the row displays four non-negative integer counts
    derived from state.stage_counts: the number of successful
    verifications (key "success"), mismatches (key "mismatch"), errors
    (key "error"), and format errors (key "format_error")
  - When a stage name is absent from state.stage_counts, every verdict
    count for that stage is rendered as zero

---

### Actual Behavior

The function returns a rich Panel object r with title 'Stages' and border_style 'cyan'. The renderable of r is a Table t with header row ['Stage', '', ' mismatch', ' error', 'fmt']. For each stage string st in the iterable STAGES, t contains a row consisting of the elements: st, str(c_s), str(c_m), str(c_e), str(c_f), where counts = state.stage_counts.get(st, {}) and c_s = counts.get('success', 0), c_m = counts.get('mismatch', 0), c_e = counts.get('error', 0), c_f = counts.get('format_error', 0). The stage_counts attribute of state is not modified.

---

## Code Evidence

Line 12: str(counts.get("success", 0))
Line 13: str(counts.get("mismatch", 0))
Line 14: str(counts.get("error", 0))
Line 15: str(counts.get("format_error", 0))

---

## Trigger Condition

The specification requires that each row displays non-negative integer counts. The code directly converts the values from state.stage_counts to strings without ensuring they are integers. Thus, if state.stage_counts contains non-integer values (e.g., strings), the output will not be an integer representation, violating the spec.

---

## How to trigger the bug

The bug is triggered by setting a non-integer float value in `state.stage_counts`. The code calls `str()` on the raw value without converting to `int()` first, so the float representation leaks into the rendered table output.

### Inputs

| Parameter | Value |
|-----------|-------|
| `state.stage_counts["init"]["success"]` | `5.5` (float) |

### Expected (spec-correct) Output

`"5"` — the integer representation of the count, obtained by converting to `int()` before `str()`.

### Actual (buggy) Output

`"5.5"` — the raw float value rendered as-is by `str()`, which is not a non-negative integer representation.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
from pathlib import Path
sys.path.insert(0, '.')
import dashboard
from dashboard import render_stages

state = dashboard.State('.')
state.stage_counts["init"]["success"] = 5.5
panel = render_stages(state)

from rich.console import Console
console = Console(force_terminal=False, width=200, color_system=None)
console.print(panel)
# actual (buggy) output: stage_counts["init"]["success"] renders as "5.5" instead of "5"
# expected (correct) output: "5" (non-negative integer)
```

---

## Probe Script

```python
"""Probe script for bug: dashboard-py--render_stages
Bug: render_stages() does str(counts.get(key, 0)) without enforcing integer type.
If state.stage_counts contains non-integer values (floats, strings), they are
rendered as-is, violating the spec's requirement of non-negative integer counts.
"""
import sys
import io
from pathlib import Path

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from rich.console import Console
    import dashboard
    from dashboard import render_stages

    # Create a State object through the public API
    state = dashboard.State("/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot")

    # Inject a non-integer float into stage_counts
    # This violates the pre-condition, but the spec's post-condition states
    # that counts must be rendered as non-negative integers regardless.
    state.stage_counts["init"]["success"] = 5.5

    # Call the public API
    panel = render_stages(state)

    # Capture rendered output as plain text
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=200, color_system=None)
    console.print(panel)
    rendered = buf.getvalue()

    # Check: if "5.5" appears in output, the bug is confirmed (float leaked through)
    # Expected: should only contain integer representations like "5" or "0"
    if "5.5" in rendered:
        print("CONFIRMED — actual: '5.5' (float) rendered | expected: non-negative integer count")
    else:
        print("NOT CONFIRMED — no non-integer values found in rendered output")
except Exception as e:
    print(f"ERROR: {e.__class__.__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '5.5' (float) rendered | expected: non-negative integer count
```
