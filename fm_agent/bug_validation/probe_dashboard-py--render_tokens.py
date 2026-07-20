import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

try:
    from dashboard import render_tokens, _price_for
    from rich.panel import Panel
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Minimal State-like object with model_seen=None to trigger the claimed bug
class FakeState:
    pass

state = FakeState()
state.totals = {"input": 100, "cache_read": 50, "cache_write": 10, "output": 200}
state.opencode_token_totals = {"input": 300, "cache_read": 100, "cache_write": 20, "output": 400}
state.cost_native = 0.05
state.opencode_cost = 0.10
state.opencode_calls = 5
state.model_seen = None  # THE BUG TRIGGER — falsy value → _price_for("") called

try:
    result = render_tokens(state)
    if isinstance(result, Panel):
        print(f'NOT CONFIRMED — render_tokens returned a valid Rich Panel despite model_seen=None')
    else:
        print(f'NOT CONFIRMED — Unexpected return type: {type(result).__name__}')
except Exception as e:
    print(f'CONFIRMED — Exception raised: {e}')
