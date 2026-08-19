#!/usr/bin/env python3
"""Probe for dashboard-py--render_cache bug.

Bug: render_cache() returns bar lines with "(no data)" for "latest 10" and
"latest 100" when cache_window is empty but total tokens are non-zero.
The spec requires all three bar lines to display percentages, colored bars,
and token counts when total tokens are non-zero.
"""

import sys
import os

# Allow import of dashboard from the repo root
repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, repo_root)

try:
    import dashboard
except ImportError as exc:
    print(f"ERROR: cannot import dashboard: {exc}")
    sys.exit(1)


class MockState:
    """State with non-zero token totals but empty cache_window.

    tokens.total: cache_read=100, new_input=900, cache_write=50 → n_cr=100, n_in=950
    opencode_tokens: cache_read=50, new_input=850, cache_write=0 → o_cr=50, o_in=850
    total_cr=150, total_input=1800 → non-zero → renders bar lines (not "(no token data yet)")
    """
    totals = {"cache_read": 100, "input": 900, "cache_write": 50}
    opencode_token_totals = {"cache_read": 50, "input": 850, "cache_write": 0}
    cache_window = []       # EMPTY — trigger for the bug
    model_seen = None       # no pricing → skip cost-savings line
    cost_native = 0.0
    opencode_cost = 0.0


try:
    state = MockState()
    panel = dashboard.render_cache(state)

    # Panel wraps Align(Text.from_markup(...), ...)
    align = panel.renderable       # Align
    text_obj = align.renderable     # Text
    rendered = text_obj.plain       # plain-text representation

    has_no_data = "(no data)" in rendered

    # Bug: spec says all three bar lines must show percentages, colored bars,
    # and token counts when total tokens are non-zero. "(no data)" violates this.
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
