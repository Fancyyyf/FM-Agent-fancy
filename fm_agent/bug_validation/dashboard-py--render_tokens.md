# Bug Report: render_tokens

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Rich Panel renderable whose title is "Tokens & Cost"
    and whose border is styled green
  - The panel contains a table with exactly three data rows: one for
    verification tokens, one for OpenCode tokens, and one for the
    combined totals across both sources
  - Each data row displays five values: the token count classified as
    new input ("input"), the count of tokens served from the prompt
    cache ("cache_read"), the count of tokens written to the prompt
    cache ("cache_write"), the output token count ("output"), and a
    monetary cost formatted as currency
  - The OpenCode row label includes the value of state.opencode_calls
    to indicate the number of invocations comprising the totals
  - The combined-total row's token values are the element-wise sum of
    the corresponding verification and OpenCode token counts; its cost
    is the sum of the two cost values
  - Token values are formatted with unit suffixes that compactly
    represent large magnitudes; cost values are derived from per-model
    pricing and formatted consistently with the currency unit

---

### Actual Behavior

The state object is unchanged: state.totals, state.opencode_token_totals, state.model_seen, state.cost_native, state.opencode_cost, and state.opencode_calls retain the exact same values and types as before the call. The return value is an instance of rich.panel.Panel with title='Tokens & Cash', border_style='green', and its renderable is a rich.table.Table containing the following rows: a header row [Source, in:new, in:read, in:write, output, cost]; a row labeled 'verification' with token counts from state.totals and cost from state.cost_native; a row labeled 'opencode (<state.opencode_calls>)' with token counts from state.opencode_token_totals and cost from state.opencode_cost; a total row summing both token categories and both costs, displaying a bold label 'TOTAL' with an input subtotal. All numeric values are formatted using _fmt_tokens and _fmt_cost (human-readable format). No exceptions are raised; all execution paths complete normally.

---

## Code Evidence

Line 2: p = _price_for(state.model_seen or "")

---

## Trigger Condition

When state.model_seen is an empty string (or any falsy value), the expression `state.model_seen or ""` evaluates to an empty string. This violates _price_fors documented precondition that model must be a nonempty string, leading to an exception or undefined behavior and preventing the function from returning a Rich Panel as required by the specification.

---

## How to trigger the bug

The claimed bug does not reproduce: `_price_for` handles empty strings gracefully via its `if not model: return None` guard on line 93 of dashboard.py. The resulting `None` value for `p` is never used in `render_tokens`, so the function still returns a valid Rich Panel.

### Inputs

| Parameter | Value |
|-----------|-------|
| state.model_seen | None |
| state.totals | {"input": 100, "cache_read": 50, "cache_write": 10, "output": 200} |
| state.opencode_token_totals | {"input": 300, "cache_read": 100, "cache_write": 20, "output": 400} |
| state.cost_native | 0.05 |
| state.opencode_cost | 0.10 |
| state.opencode_calls | 5 |

### Expected (spec-correct) Output

A valid `rich.panel.Panel` with title "Tokens & Cost" and green border.

### Actual (buggy) Output

A valid `rich.panel.Panel` with title "Tokens & Cost" and green border — identical to the expected output. The function does not crash and returns the correct type.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import render_tokens
from types import SimpleNamespace

state = SimpleNamespace(
    totals={"input": 100, "cache_read": 50, "cache_write": 10, "output": 200},
    opencode_token_totals={"input": 300, "cache_read": 100, "cache_write": 20, "output": 400},
    cost_native=0.05,
    opencode_cost=0.10,
    opencode_calls=5,
    model_seen=None,
)
result = render_tokens(state)
# result is a valid rich.panel.Panel — no exception raised
# actual (buggy) output: rich.panel.Panel instance
# expected (correct) output: rich.panel.Panel instance
```

---

## Probe Script

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

try:
    from dashboard import render_tokens, _price_for
    from rich.panel import Panel
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Minimal State-like object with model_seen=None to trigger the claimed bug
class FakeState:
    pass

state = FakeState()
state.totals = {"input": 100, "cache_read": 50, "cache_write": 10, "output": 200}
state.opencode_token_totals = {"input": 300, "cache_read": 100, "cache_write": 20, "output": 400}
state.cost_native = 0.05
state.opencode_cost = 0.10
state.opencode_calls = 5
state.model_seen = None  # THE BUG TRIGGER — falsy value → _price_for("") called

try:
    result = render_tokens(state)
    if isinstance(result, Panel):
        print(f'NOT CONFIRMED — render_tokens returned a valid Rich Panel despite model_seen=None')
    else:
        print(f'NOT CONFIRMED — Unexpected return type: {type(result).__name__}')
except Exception as e:
    print(f'CONFIRMED — Exception raised: {e}')
```

### Probe Output

```
NOT CONFIRMED — render_tokens returned a valid Rich Panel despite model_seen=None
```
