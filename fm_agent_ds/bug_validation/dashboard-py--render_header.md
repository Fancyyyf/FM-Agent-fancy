# Bug Report: render_header

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Rich Panel renderable with cyan border containing a single line of text. The line joins four parts separated by "  " (space, bullet, space): (a) the dashboard title "FM-Agent Dashboard" in bold cyan; (b) the workdir path from state.workdir labeled "workdir:"; (c) the model identifier from state.model_seen (or "?" if the value is empty) labeled "model:"; and (d) the elapsed time from state.elapsed() formatted as a human-readable duration string labeled "elapsed:". The state argument is not mutated by this call.

---

### Actual Behavior

The function returns a new Panel instance. Its renderable is a Text object whose markup string equals: '[bold cyan]FM-Agent Dashboard[/]' + '    ' + '[dim]workdir:[/] ' + str(state.workdir) + '    ' + '[dim]model:[/] ' + str(state.model_seen or '?') + '    ' + '[dim]elapsed:[/] ' + _fmt_duration(state.elapsed()). The panel's border_style is 'cyan'. The state argument is not modified. Formally: return.type == Panel  return.renderable.type == Text  return.renderable.markup == '[bold cyan]FM-Agent Dashboard[/]    [dim]workdir:[/] ' + str(state.workdir) + '    [dim]model:[/] ' + str(state.model_seen or '?') + '    [dim]elapsed:[/] ' + _fmt_duration(state.elapsed())  return.border_style == 'cyan'  state == old(state).

---

## Code Evidence

Line 8: return Panel(Text.from_markup("    ".join(parts)), border_style="cyan")

---

## Trigger Condition

The specification requires the four parts to be separated by the string '  ' (space, bullet, space). Condition A shows that the code uses the separator '    ' (two spaces before and after the bullet). This difference holds for any valid input, causing the rendered markup to differ from the specification.

---

## How to trigger the bug

The `render_header` function in `dashboard.py` (line 521) joins header parts using `"  •  "` (two spaces before and after the Unicode bullet character) instead of `" • "` (one space before and after the bullet) as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| state.workdir | `/test/workdir` |
| state.model_seen | `"test-model"` |
| state.elapsed() | `42.0` (returns `"42s"`) |

### Expected (spec-correct) Output

`[bold cyan]FM-Agent Dashboard[/] • [dim]workdir:[/] /test/workdir • [dim]model:[/] test-model • [dim]elapsed:[/] 42s`

### Actual (buggy) Output

`[bold cyan]FM-Agent Dashboard[/]  •  [dim]workdir:[/] /test/workdir  •  [dim]model:[/] test-model  •  [dim]elapsed:[/] 42s`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import render_header, _fmt_duration

class MockState:
    workdir = "/test/workdir"
    model_seen = "test-model"
    first_event_time = None
    last_event_time = None
    def elapsed(self):
        return 42.0

state = MockState()
panel = render_header(state)
print(panel.renderable.markup)
# actual (buggy) output: [bold cyan]FM-Agent Dashboard[/]  •  [dim]workdir:[/] /test/workdir  •  [dim]model:[/] test-model  •  [dim]elapsed:[/] 42s
# expected (correct) output: [bold cyan]FM-Agent Dashboard[/] • [dim]workdir:[/] /test/workdir • [dim]model:[/] test-model • [dim]elapsed:[/] 42s
```

---

## Probe Script

```python
import sys
import os

# Add repo root to path so we can import dashboard.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import render_header, _fmt_duration

    class MockState:
        workdir = "/test/workdir"
        model_seen = "test-model"
        first_event_time = None
        last_event_time = None

        def elapsed(self):
            return 42.0

    state = MockState()
    panel = render_header(state)
    actual_markup = panel.renderable.markup

    # Build the spec-correct expected markup using spec separator " * " (space-bullet-space)
    parts = [
        "[bold cyan]FM-Agent Dashboard[/]",
        "[dim]workdir:[/] /test/workdir",
        "[dim]model:[/] test-model",
        f"[dim]elapsed:[/] {_fmt_duration(state.elapsed())}",
    ]
    spec_separator = " \u2022 "  # space, bullet, space per spec
    expected_markup = spec_separator.join(parts)

    passed = actual_markup != expected_markup

    if passed:
        print(f"CONFIRMED")
        print(f"actual markup:   {actual_markup!r}")
        print(f"expected markup: {expected_markup!r}")
    else:
        print(f"NOT CONFIRMED")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED
actual markup:   '[bold cyan]FM-Agent Dashboard[/bold cyan]  •  [dim]workdir:[/dim] /test/workdir  •  [dim]model:[/dim] test-model  •  [dim]elapsed:[/dim] 42s'
expected markup: '[bold cyan]FM-Agent Dashboard[/] • [dim]workdir:[/] /test/workdir • [dim]model:[/] test-model • [dim]elapsed:[/] 42s'
```
