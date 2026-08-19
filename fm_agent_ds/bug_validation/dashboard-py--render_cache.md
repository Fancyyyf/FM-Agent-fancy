# Bug Report: render_cache

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Rich Panel renderable titled "Cache Coverage" with green border. When the sum of cache_read and input tokens (aggregated across both verification-LLM and OpenCode categories) equals zero, the panel contains centered dimmed text "(no token data yet)". Otherwise the panel contains text with: (a) three cache-coverage bar lines labeled "latest 10", "latest 100", and "overall", each displaying a percentage value color-coded by threshold (green when ≥80%, yellow when ≥50%, red otherwise), a 20-character visual bar where the filled proportion ("█") equals the percentage and the remainder is "░", and a dimmed token-count breakdown showing cache_read tokens over total tokens; (b) a dimmed line stating the coverage formula; and (c) when pricing data for the model is available via state.model_seen and total cache_read tokens exceed zero, a cost-savings line showing the estimated USD amount saved by cache reads and the percentage reduction versus a no-cache baseline. The state argument is not mutated by this call.

---

### Actual Behavior

The state object (`state`) is unchanged: all its attributes (`totals`, `opencode_token_totals`, `cache_window`, `model_seen`, `cost_native`, `opencode_cost`) retain their original values and types. The function either returns an instance of `Panel` (if no exception occurs) or propagates an exception raised by a called function (`_cache_rate`, `_fmt_tokens`, `_price_for`, `Text.from_markup`, `Panel`); in either case the state remains unmodified. Formally: \(state' = state \land (\textit{returns} \Rightarrow \text{type}(\textit{retval}) = \text{Panel}) \land (\textit{raises} \Rightarrow state' = state)\).

---

## Code Evidence

Line 4: `if tot == 0:` Line 5: `return f"[dim]{label:<14}(no data)[/]"` (with calls at Line 24-25 using `rows[-10:]` and `rows[-100:]`)

---

## Trigger Condition

Spec (a) requires each bar line to display a percentage value, colored bar, and token counts. When `cache_window` is empty but total tokens are non-zero, 'latest 10' and 'latest 100' lines show '(no data)' without these elements, violating the specification.

---

## How to trigger the bug

The bug occurs when `state.cache_window` is empty (no recent cache-hit records) but `state.totals` and `state.opencode_token_totals` have non-zero aggregated values. The `bar_line` helper slices an empty list (`rows[-10:]` → `[]`) and passes it to `_cache_rate`, which returns `(None, 0, 0)`. Because `tot == 0`, the early return `"(no data)"` fires instead of the formatted bar line with percentage, color-coded bar, and token counts.

### Inputs

| Parameter | Value |
|-----------|-------|
| `state.totals["cache_read"]` | 100 |
| `state.totals["input"]` | 900 |
| `state.totals["cache_write"]` | 50 |
| `state.opencode_token_totals["cache_read"]` | 50 |
| `state.opencode_token_totals["input"]` | 850 |
| `state.opencode_token_totals["cache_write"]` | 0 |
| `state.cache_window` | `[]` (empty) |
| `state.model_seen` | `None` |
| `state.cost_native` | 0.0 |
| `state.opencode_cost` | 0.0 |

### Expected (spec-correct) Output

All three bar lines ("latest 10", "latest 100", "overall") display a percentage value with color coding, a 20-character visual bar, and dimmed token counts. Even though the window is empty, the lines should show percentages (0% in this case) with bars and "(0 / 0)" or similar token breakdowns.

### Actual (buggy) Output

"latest 10" and "latest 100" lines show `"(no data)"` without percentages, bars, or token counts. Only the "overall" line renders correctly using the aggregate totals.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package public API):

```python
import dashboard

class MockState:
    totals = {"cache_read": 100, "input": 900, "cache_write": 50}
    opencode_token_totals = {"cache_read": 50, "input": 850, "cache_write": 0}
    cache_window = []
    model_seen = None
    cost_native = 0.0
    opencode_cost = 0.0

panel = dashboard.render_cache(MockState())
# Navigate to inner text
text = panel.renderable.renderable
print(text.plain)
# Output includes:
#   latest 10     (no data)
#   latest 100    (no data)
#   overall      7.7%  █░░░░░░░░░░░░░░░░░░░  150 / 1.9K
#   coverage = cache_read / (input + cache_write + cache_read)
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for dashboard-py--render_cache bug."""

import sys
import os

repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, repo_root)

try:
    import dashboard
except ImportError as exc:
    print(f"ERROR: cannot import dashboard: {exc}")
    sys.exit(1)


class MockState:
    totals = {"cache_read": 100, "input": 900, "cache_write": 50}
    opencode_token_totals = {"cache_read": 50, "input": 850, "cache_write": 0}
    cache_window = []
    model_seen = None
    cost_native = 0.0
    opencode_cost = 0.0


try:
    state = MockState()
    panel = dashboard.render_cache(state)

    align = panel.renderable
    text_obj = align.renderable
    rendered = text_obj.plain

    has_no_data = "(no data)" in rendered
    passed = has_no_data

except Exception as exc:
    import traceback
    print(f"ERROR: {exc}")
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        "CONFIRMED — cache_window empty (0 entries) but totals non-zero "
        "(150 cache_read / 1800 input): bar lines show '(no data)' "
        "instead of percentage/count/bars per spec"
    )
else:
    print("NOT CONFIRMED — no '(no data)' found in rendered output")
```

### Probe Output

```
CONFIRMED — cache_window empty (0 entries) but totals non-zero (150 cache_read / 1800 input): bar lines show '(no data)' instead of percentage/count/bars per spec
```
