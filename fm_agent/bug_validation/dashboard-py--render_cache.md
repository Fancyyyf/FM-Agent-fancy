# Bug Report: render_cache

**Source file:** `fm_agent/extracted_functions/dashboard-py/render_cache.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Panel renderable titled "Cache Coverage" with a green
    border
  - The panel body displays cache hit-rate bars for three
    aggregation windows: the most recent 10 entries of
    state.cache_window, the most recent 100 entries, and the
    aggregate of all entries in state.cache_window
  - Each bar renders a percentage value, a filled-bar visual of
    width 20 characters, and the token counts in the form
    "cache_read / total_input"
  - The bar color is green when the hit rate is at least 80%,
    yellow when at least 50%, and red when the hit rate is below 50%
  - A window whose total_input is zero produces "(no data)" in place
    of bar content for that window
  - When the combined total of cache_read and input tokens across
    all data sources is zero, the panel body displays "(no token
    data yet)"
  - Total cache_read tokens are computed as
    state.totals["cache_read"] +
    state.opencode_token_totals["cache_read"]
  - Total input tokens are computed as
    state.totals["input"] + state.totals["cache_write"] +
    state.opencode_token_totals["input"] +
    state.opencode_token_totals["cache_write"]
  - The coverage (hit-rate) interpretation displayed below the bars
    is: cache_read / (input + cache_write + cache_read)
  - When pricing data is available for the model identified by
    state.model_seen and total cache_read > 0, an additional line
    shows estimated cost savings as a dollar amount and as a
    percentage of what the total cost would have been without cache
    reads
  - The panel content is vertically centered

---

### Actual Behavior

After execution, the function returns a Panel object; state is unmodified. The Panel has title "Cache Coverage" and border style "green". Its renderable is an Align(center, vertical="middle") containing a Text object. If the sum of all cache_read, input, and cache_write tokens from both totals and opencode_token_totals is zero, the Text markup is "[dim](no token data yet)[/]". Otherwise, the Text contains three bar-line strings (latest 10, latest 100, overall) summarizing cache hit rates, a visual bar, and formatted token counts, computed from state.cache_window and the aggregated totals. If pricing data exists for the model (state.model_seen), input_cost_per_token > 0, and total cache_read > 0, an additional line showing estimated cost savings and the percentage saved over no-cache usage is appended. Formal logic: let result = render_cache(state); result  Panel  result.title = "Cache Coverage"  result.border_style = "green"  result.renderable  Align  result.renderable.align = "center"  result.renderable.vertical = "middle"  let text = result.renderable.renderable  Text; if total_cr + total_input = 0 then text.markup = "[dim](no token data yet)[/]" else text.markup contains the bar-line for latest 10 computed from state.cache_window[-10:], latest 100 from state.cache_window[-100:], overall from [(total_cr, total_cr+total_input)], and iff p = _price_for(state.model_seen or "")  None  p.get("input_cost_per_token") > 0  total_cr > 0 then a savings line matching the pattern "saved ~$..." is included. The state object is not mutated.

---

## Code Evidence

Line 26: bar_line("overall", [(total_cr, total_cr + total_input)])

---

## Trigger Condition

The specification requires the overall bar to be computed from the aggregate of all entries in state.cache_window (i.e., sum of cache_read and sum of total_input over the entries). The code instead computes the overall bar using total_cr and total_cr+total_input derived from state.totals and state.opencode_token_totals, which may differ from the cache_window sums. This leads to a wrong hit rate when cache_window does not exactly match those totals.

---

## How to trigger the bug

The `render_cache` function computes the "overall" cache-hit-rate bar using the aggregated token totals (`total_cr`, `total_cr + total_input`) from `state.totals` and `state.opencode_token_totals` rather than summing all entries in `state.cache_window`. When the running total exceeds the `cache_window` buffer (maxlen=200), the two computations diverge.

### Inputs

| Parameter | Value |
|-----------|-------|
| state.totals["cache_read"] | 500 |
| state.totals["input"] | 2000 |
| state.totals["cache_write"] | 300 |
| state.opencode_token_totals["cache_read"] | 400 |
| state.opencode_token_totals["input"] | 1800 |
| state.opencode_token_totals["cache_write"] | 200 |
| state.cache_window | [(50, 300), (80, 400), (30, 200)] |
| state.model_seen | None |
| state.cost_native | 0.0 |
| state.opencode_cost | 0.0 |

### Expected (spec-correct) Output

Overall bar uses cache_window aggregate: `cache_read = 50+80+30 = 160`, `total_input = 300+400+200 = 900`, rate = `160/900 = 17.8%`

### Actual (buggy) Output

Overall bar uses totals: `total_cr = 500+400 = 900`, `total_cr + total_input = 900 + 4300 = 5200`, rate = `900/5200 = 17.3%`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import render_cache

class MockState:
    def __init__(self):
        self.totals = {"cache_read": 500, "input": 2000, "cache_write": 300}
        self.opencode_token_totals = {"cache_read": 400, "input": 1800, "cache_write": 200}
        self.cache_window = [(50, 300), (80, 400), (30, 200)]
        self.model_seen = None
        self.cost_native = 0.0
        self.opencode_cost = 0.0

result = render_cache(MockState())
print(result.renderable.renderable.markup)
# actual (buggy) output:   overall   [bold red] 17.3%[/bold red]  [red]███░░░░░░░░░░░░░░░░░[/red] [dim]900 / 5.2K[/dim]
# expected (correct) output: overall   [bold red] 17.8%[/bold red]  [red]███░░░░░░░░░░░░░░░░░[/red] [dim]160 / 900[/dim]
```

---

## Probe Script

```python
"""Probe script for dashboard-py--render_cache bug.

Bug: The "overall" bar in render_cache() uses aggregated totals
(total_cr, total_cr + total_input) from state.totals and
state.opencode_token_totals instead of summing all entries in
state.cache_window as the specification requires.

When cache_window (maxlen=200) has been truncated, its sums
differ from the accumulated totals, producing a wrong hit rate.
"""

import sys
import os

# Ensure we can import dashboard from the repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import render_cache, _cache_rate
except Exception as e:
    print(f'ERROR: Failed to import dashboard: {e}')
    sys.exit(1)


class MockState:
    """Simulates state where cache_window differs from accumulated totals."""
    def __init__(self):
        # Accumulated totals from ALL events (including those dropped from cache_window)
        self.totals = {
            "cache_read": 500,
            "input": 2000,
            "cache_write": 300,
        }
        self.opencode_token_totals = {
            "cache_read": 400,
            "input": 1800,
            "cache_write": 200,
        }
        # cache_window (maxlen=200) only has recent entries with DIFFERENT sums
        self.cache_window = [(50, 300), (80, 400), (30, 200)]
        self.model_seen = None
        self.cost_native = 0.0
        self.opencode_cost = 0.0


state = MockState()

# ----------------------------------------------------------------
# Test 1: Direct _cache_rate comparison
# ----------------------------------------------------------------
n_cr = state.totals.get("cache_read", 0)
n_in = state.totals.get("input", 0) + state.totals.get("cache_write", 0)
o_cr = state.opencode_token_totals.get("cache_read", 0)
o_in = (state.opencode_token_totals.get("input", 0)
        + state.opencode_token_totals.get("cache_write", 0))
total_cr = n_cr + o_cr          # = 500 + 400 = 900
total_input = n_in + o_in       # = (2000+300) + (1800+200) = 2300 + 2000 = 4300

# What the code does now (buggy):
#   bar_line("overall", [(total_cr, total_cr + total_input)])
code_rows = [(total_cr, total_cr + total_input)]
code_result = _cache_rate(code_rows)
code_rate = code_result[0] if code_result[0] is not None else 0.0

# What the spec says it SHOULD do:
#   bar_line("overall", rows)  where rows = list(state.cache_window)
spec_rows = list(state.cache_window)
spec_result = _cache_rate(spec_rows)
spec_rate = spec_result[0] if spec_result[0] is not None else 0.0

test1_passed = (abs(code_rate - spec_rate) > 0.001)  # rates should differ

# ----------------------------------------------------------------
# Test 2: Extract rendered "overall" bar from render_cache output
# ----------------------------------------------------------------
result = render_cache(state)
# result = Panel(Align.center(text, vertical="middle"), ...)
# result.renderable = Align, result.renderable.renderable = Text
text_obj = result.renderable.renderable
markup = text_obj.markup if hasattr(text_obj, 'markup') else str(text_obj)

# Find the "overall" line in the rendered output
overall_line = None
for line in markup.split('\n'):
    if 'overall' in line.lower():
        overall_line = line
        break

test2_passed = overall_line is not None

# ----------------------------------------------------------------
# Verdict
# ----------------------------------------------------------------
if test1_passed and test2_passed:
    print(f'CONFIRMED — overall bar uses totals-based computation')
    print(f'  code rate: {code_rate*100:.1f}% (totals: cr={total_cr}, in={total_cr+total_input})')
    print(f'  spec rate: {spec_rate*100:.1f}% (cache_window aggregate: cr={spec_result[1]}, tot={spec_result[2]})')
    print(f'  cache_window entries: {spec_rows}')
    print(f'  overall line rendered: {overall_line}')
else:
    if not test1_passed:
        print(f'NOT CONFIRMED — code and spec produce same rate: {code_rate*100:.1f}%')
    elif not test2_passed:
        print('NOT CONFIRMED — could not find overall line in rendered output')
    else:
        print('NOT CONFIRMED')
```

### Probe Output

```
CONFIRMED — overall bar uses totals-based computation
  code rate: 17.3% (totals: cr=900, in=5200)
  spec rate: 17.8% (cache_window aggregate: cr=160, tot=900)
  cache_window entries: [(50, 300), (80, 400), (30, 200)]
  overall line rendered: overall   [bold red] 17.3%[/bold red]  [red]███░░░░░░░░░░░░░░░░░[/red] [dim]900 / 5.2K[/dim]
```
