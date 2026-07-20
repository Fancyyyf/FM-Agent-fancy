# Bug Report: bar_line

**Source file:** `fm_agent/extracted_functions/dashboard-py/bar_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When the total input tokens aggregated across rows is zero,
    returns a Rich markup string indicating no data for the given
    label.
  - Otherwise, returns a Rich markup string containing:
      * The label left-aligned to a fixed width.
      * The cache-hit rate expressed as a percentage with one
        decimal place, rendered in bold with a color determined
        by the rate: green when ≥ 80%, yellow when ≥ 50%, and
        red otherwise.
      * A 20-character horizontal bar whose filled portion is
        proportional to the hit rate (rendered with the same color
        as the percentage), followed by the formatted cache-read
        and total-input token counts separated by " / " in dim
        style.

---

### Actual Behavior

The function returns a string and has no side effects on the inputs. Let n be the number of pairs in rows, and for each i=1..n let a_i = cache_read_i ≥ 0, b_i = total_input_i ≥ 0. Define cr = Σ a_i, tot = Σ b_i. If tot = 0 the function returns "[dim]" + label left-justified to width 14 + "(no data)[/]". Otherwise, let rate = cr / tot, pct = 100 * rate, filled = 20 * rate, bar = "█" repeated filled times + "░" repeated (20−filled) times, color = "green" if pct ≥ 80 else ("yellow" if pct ≥ 50 else "red"). The function returns f"{label:<10}[bold {color}]{pct:5.1f}%[/]  [{color}]{bar}[/] [dim]{_fmt_tokens(cr)} / {_fmt_tokens(tot)}[/]" where _fmt_tokens gives a human‑readable abbreviation. Precondition guarantees label is a non‑empty string, so label alignment never fails.

---

## Code Evidence

Line 6:         bar_w = 20
Line 7:         filled = int(bar_w * rate)
Line 8:         bar = "█" * filled + "░" * (bar_w - filled)

---

## Trigger Condition

When total_input > 0 and rate > 1 (cache_read > total_input), filled = int(20*rate) exceeds 20, making the bar longer than 20 characters. The specification requires a 20-character horizontal bar, so the code violates it.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| label | `"latest 10"` |
| rows | `[(10, 5)]` — a single row where cache_read=10, total_input=5 (rate=2.0) |

### Expected (spec-correct) Output

A 20-character horizontal bar. With rate=2.0, the correct bar should be clamped or capped at 20 characters (either by capping `rate` at 1.0 before multiplication, or by clamping `filled` to `bar_w`).

### Actual (buggy) Output

A 40-character horizontal bar (40 `█` characters instead of 20), because `filled = int(20 * 2.0) = 40`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from collections import defaultdict
import dashboard

class FakeState:
    totals = defaultdict(int, {"cache_read": 1})
    opencode_token_totals = defaultdict(int)
    cache_window = [(10, 5)]  # cache_read=10 > total_input=5 → rate=2.0
    cost_native = 0.0
    opencode_cost = 0.0
    model_seen = None

result = dashboard.render_cache(FakeState())
# The rendered output contains "█" * 40 for the "latest 10" and "latest 100" bars
# instead of the specified 20-character limit.
# actual (buggy) output bar width: 40 chars
# expected (correct) output bar width: 20 chars (or ≤ 20)
```

---

## Probe Script

```python
import re
import sys
from pathlib import Path

# Add repo root to sys.path so `import dashboard` works
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    from collections import defaultdict

    import dashboard
    from rich.console import Console

    class FakeState:
        # totals.get("cache_read",0)=1 ensures total_cr+total_input > 0
        # so render_cache takes the bar_line path instead of "(no token data yet)".
        totals = defaultdict(int, {"cache_read": 1})
        opencode_token_totals = defaultdict(int)
        cache_window = [(10, 5)]  # cache_read=10 > total_input=5 → rate=2.0
        cost_native = 0.0
        opencode_cost = 0.0
        model_seen = None

    result = dashboard.render_cache(FakeState())

    # Render the Rich Panel to a string and strip ANSI escapes
    console = Console(width=200, force_terminal=False, color_system=None)
    with console.capture() as capture:
        console.print(result)
    output = capture.get()
    clean = re.sub(r'\x1b\[[0-9;]*m', '', output)

    # Count max consecutive "█" characters in the rendered output.
    # The spec requires a 20-char bar, but with rate > 1 the bar expands.
    max_bar = 0
    count = 0
    for ch in clean:
        if ch == '\u2588':  # full block: "█"
            count += 1
            max_bar = max(max_bar, count)
        else:
            count = 0

    expected_bar_width = 20
    bug_reproduced = max_bar > expected_bar_width

    if bug_reproduced:
        print(f'CONFIRMED — bar width: {max_bar} chars (exceeds spec limit of {expected_bar_width})')
        print(f'Rate: cache_read={10}, total_input={5}, rate={10/5:.1f}, '
              f'filled=int({20}*{10/5:.1f})={int(20*10/5)}, expected filled<=20')
    else:
        print(f'NOT CONFIRMED — max bar width: {max_bar} chars (within spec limit of {expected_bar_width})')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — bar width: 40 chars (exceeds spec limit of 20)
Rate: cache_read=10, total_input=5, rate=2.0, filled=int(20*2.0)=40, expected filled<=20
```
