import sys
import tempfile
from pathlib import Path

# Ensure repo root is on the Python path for the entry-point import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import dashboard

    with tempfile.TemporaryDirectory() as tmpdir:
        state = dashboard.State(tmpdir)

        # Create a falsy mock datetime that has strftime() but is falsy
        class FalsyDatetime:
            def strftime(self, fmt):
                return "12:34:56"

            def __bool__(self):
                return False

        fake_ts = FalsyDatetime()

        # Verify preconditions: fake_ts is falsy but not None
        assert fake_ts is not None, "precondition failed: fake_ts is not None"
        assert not fake_ts, "precondition failed: fake_ts is falsy"

        # Call _push_recent with the falsy non-None datetime
        state._push_recent(fake_ts, "test_stage", "success", "test summary")

        when_str, stage, status, summary = state.recent_events[0]

        # Spec says: when_str = ts.strftime("%H:%M:%S") since ts is not None
        # Code does: when_str = "" because `if ts` is False
        expected = "12:34:56"
        actual = when_str
        passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
