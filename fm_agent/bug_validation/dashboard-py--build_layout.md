# Bug Report: build_layout

**Source file:** `dashboard-py/build_layout.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Rich Layout renderable that, when rendered to a terminal,
    produces a full-screen dashboard partitioned into vertically stacked
    regions: header, top, mid, and footer
  - The header region contains run identification information derived
    from state
  - The top region is horizontally split into a pipeline stage progress
    panel (ratio 3) and a right column containing a prompt-cache panel
    (ratio 2) stacked above a bug-validation summary panel (ratio 1)
  - The mid region is horizontally split into a token-usage statistics
    panel (ratio 3) and an LLM call status panel (ratio 2)
  - The footer region displays the most recent trace events in
    chronological order
  - Every panel's rendered content reflects the data in state at the
    moment of the call
  - Region heights are computed from the number of data rows each panel
    is expected to render, not from fixed absolute sizes

---

### Actual Behavior

Natural language: The function returns a Rich `Layout` object that represents a dashboard with a specific vertical and horizontal split structure. The root layout is split into four vertical panes: 'header' (fixed height 3, containing the dashboard title and project identification rendered from `state`), 'top' (height equal to the number of pipeline stages plus 6), 'mid' (height 9), and 'footer' (fills remaining space, containing a recent event log). The 'top' pane is split horizontally into 'stages' (ratio 3, rendering stage status tallies) and 'top_right' (ratio 2), which is itself split vertically into 'cache' (ratio 2, rendering prompt-cache statistics) and 'bugs' (ratio 1, rendering bug validation counts). The 'mid' pane is split horizontally into 'tokens' (ratio 3, rendering token consumption breakdown) and 'llm' (ratio 2, rendering recent LLM statuses). All renderables are derived from `state` via the corresponding `render_*` helper functions; `state` is not modified. The layout sizes and ratios are constants determined at build time except for the 'top' height which depends on the global `STAGES` list. 

Formal logic:  state: State satisfying Pre, the function terminates normally and returns a `Layout` object `layout` such that:
  is_layout(layout) 
  layout.children = [header, top, mid, footer] 
  header.name = 'header'  header.size = 3  header.renderable = render_header(state) 
  top.name = 'top'  top.size = len(STAGES) + 6 
    top.children = [stages, top_right] 
    stages.name = 'stages'  stages.ratio = 3  stages.renderable = render_stages(state) 
    top_right.name = 'top_right'  top_right.ratio = 2 
      top_right.children = [cache, bugs] 
      cache.name = 'cache'  cache.ratio = 2  cache.renderable = render_cache(state) 
      bugs.name = 'bugs'  bugs.ratio = 1  bugs.renderable = render_bugs(state) 
  mid.name = 'mid'  mid.size = 9 
    mid.children = [tokens, llm] 
    tokens.name = 'tokens'  tokens.ratio = 3...

---

## Code Evidence

Line 11: Layout(render_header(state), name="header", size=3)

---

## Trigger Condition

The specification requires that region heights are computed from the number of data rows each panel is expected to render, not from fixed absolute sizes. The header height is hardcoded to 3, so if render_header produces more than 3 rows, the header will be clipped, violating the specification.

---

## How to trigger the bug

The header size in `build_layout` is hardcoded to `3` rather than being computed dynamically from the content that `render_header(state)` produces. If `render_header` ever returns a renderable taller than 3 lines (e.g., a Panel with 10 lines of text → 12 total lines with borders), the content will be clipped because the Layout's fixed `size=3` does not accommodate it.

### Inputs

| Parameter | Value |
|-----------|-------|
| state | A dummy object (the render functions are monkey-patched to isolate the test) |

### Expected (spec-correct) Output

`layout["header"].size` = 12 (computed from the 10 text lines + 2 Panel borders)

### Actual (buggy) Output

`layout["header"].size` = 3 (hardcoded constant, ignoring content height)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, ".")

import dashboard
from rich.panel import Panel
from rich.text import Text

orig = dashboard.render_header
# Make render_header return 10 lines of text in a Panel → 12 lines total
tall_text = Text("\n".join(f"Line {i}" for i in range(10)))
dashboard.render_header = lambda state: Panel(tall_text, border_style="cyan")

layout = dashboard.build_layout(object())
print(f"header size: {layout['header'].size}")  # actual (buggy) output: 3
# expected (correct) output: 12

dashboard.render_header = orig
```

---

## Probe Script

```python
"""Probe script for dashboard-py--build_layout: verify header size is hardcoded, not computed from content."""
import sys
import os

# Add repo root to path so `import dashboard` resolves (project is not a package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    from rich.panel import Panel
    from rich.text import Text

    # Save originals for restoration
    _orig_header = dashboard.render_header
    _orig_stages = dashboard.render_stages
    _orig_cache = dashboard.render_cache
    _orig_bugs = dashboard.render_bugs
    _orig_tokens = dashboard.render_tokens
    _orig_llm = dashboard.render_llm_status
    _orig_recent = dashboard.render_recent

    # Patch render_header to return a tall renderable (10 text lines in a Panel = 12 total lines)
    tall_text = Text("\n".join(f"Line {i}" for i in range(10)))
    dashboard.render_header = lambda state: Panel(tall_text, border_style="cyan")

    # Patch other render_* functions to return simple dummy content
    dashboard.render_stages = lambda state: Panel("stages", border_style="cyan")
    dashboard.render_cache = lambda state: Panel("cache", border_style="green")
    dashboard.render_bugs = lambda state: Panel("bugs", border_style="yellow")
    dashboard.render_tokens = lambda state: Panel("tokens", border_style="green")
    dashboard.render_llm_status = lambda state: Panel("llm", border_style="cyan")
    dashboard.render_recent = lambda state: Panel("recent", border_style="cyan")

    state = object()  # dummy state — build_layout only passes it to render_* functions
    layout = dashboard.build_layout(state)

    header_size = layout["header"].size

    # Spec-expected: heights computed from data rows. 10 text lines + 2 Panel borders = 12.
    expected = 12
    actual = header_size

    # Bug reproduced if actual != expected (fixed at 3 instead of computed)
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — header size is hardcoded to {actual}, spec requires computed from content (expected {expected})")
    else:
        print(f"NOT CONFIRMED — header size matches expected: {actual}")

    # Restore originals
    dashboard.render_header = _orig_header
    dashboard.render_stages = _orig_stages
    dashboard.render_cache = _orig_cache
    dashboard.render_bugs = _orig_bugs
    dashboard.render_tokens = _orig_tokens
    dashboard.render_llm_status = _orig_llm
    dashboard.render_recent = _orig_recent

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — header size is hardcoded to 3, spec requires computed from content (expected 12)
```
