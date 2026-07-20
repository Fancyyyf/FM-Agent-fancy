import sys
import os
import io

# Ensure the repo root is on sys.path so `import dashboard` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    from rich.console import Console

    # Create 70 mock status entries (more than 50, fewer than LLM_STATUS_WINDOW=80)
    class MockState:
        pass

    state = MockState()
    state.llm_statuses = [
        {"code": 200, "status": "success", "time": "12:00", "source": "src", "label": f"call_{i}"}
        for i in range(70)
    ]

    result = dashboard.render_llm_status(state)

    # Render the Panel to plain text so we can count strip symbols
    f = io.StringIO()
    console = Console(file=f, no_color=True, force_terminal=False)
    console.print(result)
    output = f.getvalue()

    # Each 200-code entry produces a "■" symbol in the strip
    symbol_count = output.count("\u25a0")
    expected = 70  # spec: strip should show ALL entries in window (capped at LLM_STATUS_WINDOW=80)

    passed = symbol_count != expected
    if passed:
        print(f"CONFIRMED \u2014 strip shows {symbol_count} symbols for {len(state.llm_statuses)} entries, expected {expected}")
    else:
        print(f"NOT CONFIRMED \u2014 strip shows {symbol_count} symbols, matched expected {expected}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
