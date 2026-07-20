"""Probe script for bug: dashboard-py--render_header
Bug: render_header() uses `state.model_seen or '?'` which raises AttributeError
when model_seen attribute is absent, violating the spec that requires '?' in that case.
"""
import sys
from pathlib import Path

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from dashboard import render_header

    # Create a mock state that has workdir and elapsed() but NO model_seen
    class MockNoModelSeen:
        workdir = "/fake/project"
        def elapsed(self):
            return 42.0

    state = MockNoModelSeen()

    # Expected: render_header should use '?' when model_seen is absent (per spec)
    # Actual: state.model_seen raises AttributeError before reaching `or '?'`
    result = render_header(state)

    # If we got here without error, check if the output contains '?'
    result_str = str(result)
    has_question_mark = "'?'" in result_str or '?' in result_str
    # Also verify no crash — the panel was returned
    if has_question_mark:
        print("NOT CONFIRMED — function handled absent model_seen gracefully, output contains '?'")
    else:
        print(f"NOT CONFIRMED — function did not crash but did not use '?' for absent model_seen: {result_str[:200]}")

except AttributeError as e:
    # Bug confirmed: state.model_seen access raised AttributeError
    print(f"CONFIRMED — AttributeError when model_seen is absent: {e}")
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
