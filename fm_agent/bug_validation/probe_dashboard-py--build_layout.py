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
