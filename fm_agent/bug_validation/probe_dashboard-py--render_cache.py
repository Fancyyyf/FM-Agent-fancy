"""Probe script for dashboard-py--render_cache bug.

Bug: The "overall" bar in render_cache() uses aggregated totals
(total_cr, total_cr + total_input) from state.totals and
state.opencode_token_totals instead of summing all entries in
state.cache_window as the specification requires.

When cache_window (maxlen=200) has been truncated, its sums
differ from the accumulated totals, producing a wrong hit rate.
"""

import sys
import os

# Ensure we can import dashboard from the repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import render_cache, _cache_rate
except Exception as e:
    print(f'ERROR: Failed to import dashboard: {e}')
    sys.exit(1)


class MockState:
    """Simulates state where cache_window differs from accumulated totals."""
    def __init__(self):
        # Accumulated totals from ALL events (including those dropped from cache_window)
        self.totals = {
            "cache_read": 500,
            "input": 2000,
            "cache_write": 300,
        }
        self.opencode_token_totals = {
            "cache_read": 400,
            "input": 1800,
            "cache_write": 200,
        }
        # cache_window (maxlen=200) only has recent entries with DIFFERENT sums
        self.cache_window = [(50, 300), (80, 400), (30, 200)]
        self.model_seen = None
        self.cost_native = 0.0
        self.opencode_cost = 0.0


state = MockState()

# ----------------------------------------------------------------
# Test 1: Direct _cache_rate comparison
# ----------------------------------------------------------------
n_cr = state.totals.get("cache_read", 0)
n_in = state.totals.get("input", 0) + state.totals.get("cache_write", 0)
o_cr = state.opencode_token_totals.get("cache_read", 0)
o_in = (state.opencode_token_totals.get("input", 0)
        + state.opencode_token_totals.get("cache_write", 0))
total_cr = n_cr + o_cr          # = 500 + 400 = 900
total_input = n_in + o_in       # = (2000+300) + (1800+200) = 2300 + 2000 = 4300

# What the code does now (buggy):
#   bar_line("overall", [(total_cr, total_cr + total_input)])
code_rows = [(total_cr, total_cr + total_input)]
code_result = _cache_rate(code_rows)
code_rate = code_result[0] if code_result[0] is not None else 0.0

# What the spec says it SHOULD do:
#   bar_line("overall", rows)  where rows = list(state.cache_window)
spec_rows = list(state.cache_window)
spec_result = _cache_rate(spec_rows)
spec_rate = spec_result[0] if spec_result[0] is not None else 0.0

test1_passed = (abs(code_rate - spec_rate) > 0.001)  # rates should differ

# ----------------------------------------------------------------
# Test 2: Extract rendered "overall" bar from render_cache output
# ----------------------------------------------------------------
result = render_cache(state)
# result = Panel(Align.center(text, vertical="middle"), ...)
# result.renderable = Align, result.renderable.renderable = Text
text_obj = result.renderable.renderable
markup = text_obj.markup if hasattr(text_obj, 'markup') else str(text_obj)

# Find the "overall" line in the rendered output
overall_line = None
for line in markup.split('\n'):
    if 'overall' in line.lower():
        overall_line = line
        break

test2_passed = overall_line is not None

# ----------------------------------------------------------------
# Verdict
# ----------------------------------------------------------------
if test1_passed and test2_passed:
    print(f'CONFIRMED — overall bar uses totals-based computation')
    print(f'  code rate: {code_rate*100:.1f}% (totals: cr={total_cr}, in={total_cr+total_input})')
    print(f'  spec rate: {spec_rate*100:.1f}% (cache_window aggregate: cr={spec_result[1]}, tot={spec_result[2]})')
    print(f'  cache_window entries: {spec_rows}')
    print(f'  overall line rendered: {overall_line}')
else:
    if not test1_passed:
        print(f'NOT CONFIRMED — code and spec produce same rate: {code_rate*100:.1f}%')
    elif not test2_passed:
        print('NOT CONFIRMED — could not find overall line in rendered output')
    else:
        print('NOT CONFIRMED')
