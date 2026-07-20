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
