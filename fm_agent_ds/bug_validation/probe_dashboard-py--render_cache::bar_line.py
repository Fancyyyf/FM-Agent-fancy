"""Probe for dashboard-py--render_cache::bar_line
Bug: bar_line uses left-alignment (:<14) for label in no-data case,
     but spec requires right-alignment (:>14).
"""
import sys
import os

# Add repo root to sys.path so 'import dashboard' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from dashboard import render_cache

    class MockState:
        pass

    state = MockState()
    state.totals = {"cache_read": 1}       # non-zero total_cr → enter normal path
    state.opencode_token_totals = {}
    state.cache_window = [(0, 0)]          # zero totals → bar_line no-data path
    state.model_seen = None                 # no price → no cost line appended
    state.cost_native = 0
    state.opencode_cost = 0

    # Call the public API that exercises bar_line
    panel = render_cache(state)

    # Extract plain text: Panel → Align → Text
    align = panel.renderable
    text = align.renderable
    content = text.plain

    # For label "latest 10" (length 10) in a 14-char field:
    #   Left-aligned  (buggy):    "latest 10     "  → 10 chars label + 4 spaces right-pad
    #   Right-aligned (spec):     "    latest 10"    → 4 spaces left-pad + 10 chars label
    #
    # The bar_line returns Rich markup: "[dim]latest 10     (no data)[/]"
    # After Text.from_markup, the content between tags is preserved literally.
    # So .plain should contain "latest 10     (no data)"

    # Find the dim-styled text for "latest 10"
    # We check the plain text for the bug pattern
    bug_pattern = "latest 10     (no data)"       # left-aligned (buggy)
    spec_pattern = "    latest 10(no data)"        # right-aligned (correct)

    if bug_pattern in content:
        print(f"CONFIRMED — bar_line left-aligns label in no-data case")
        print(f"actual:   {bug_pattern!r}")
        print(f"expected: {spec_pattern!r}")
        print(f"full content: {content!r}")
    elif spec_pattern in content:
        print(f"NOT CONFIRMED — bar_line right-aligns label, matching spec")
        print(f"output: {content!r}")
    else:
        print(f"NOT CONFIRMED — neither pattern found in output")
        print(f"output: {content!r}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
