import sys
from collections import deque
from io import StringIO
from pathlib import Path

# Ensure the repo root is on sys.path so dashboard.py is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from dashboard import render_recent
from rich.console import Console


class MockState:
    pass


state = MockState()
state.recent_events = deque()

# Inject Rich markup into the "time" field.
# The spec requires the time column to be rendered in "dimmed" style,
# but passing unescaped Rich markup like [red]...[/red] should be
# parsed by Rich and override the column-level style.
state.recent_events.append(("[red]14:30:00[/red]", "verification", "success", "test summary"))

try:
    panel = render_recent(state)

    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    console.print(panel)
    output = buf.getvalue()

    # If Rich parsed the [red] markup, the literal "[red]" and "[/]" tags
    # will be stripped from the rendered output (consumed as markup).
    # If they appear literally, the markup was not parsed and column style
    # (dimmed) is preserved — the bug is not reproduced.
    markup_parsed = "[red]" not in output

    if markup_parsed:
        print(
            "CONFIRMED — Rich markup [red] in time field was parsed,"
            " overriding the dim column style"
        )
    else:
        print(
            "NOT CONFIRMED — [red] appeared as literal text,"
            " column style was preserved; render_recent appears spec-compliant"
        )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
