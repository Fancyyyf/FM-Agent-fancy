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
