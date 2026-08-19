import sys
import tempfile
import os

# Ensure the repo root is on sys.path so that `src.trace_writer` resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.trace_writer import append_event

    # Create a temporary directory for the probe (following the rule:
    # all test fixtures must live under a fresh temporary directory)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Input with a non-string dict key (tuple), which json.dumps cannot serialize
        # The spec only permits OSError propagation; TypeError violates the spec
        buggy_event = {(1, 2): "value"}

        actual = None
        passed = False

        try:
            actual = append_event(tmpdir, buggy_event)
            # If we reach here, no exception was raised — bug NOT confirmed
            passed = False
        except TypeError:
            # TypeError raised — this confirms the bug
            passed = True
        except OSError:
            # OSError is permitted by the spec — not the bug we're looking for
            passed = False
        except Exception:
            # Some other exception — not the expected bug
            passed = False

    expected = "No TypeError (spec only permits OSError propagation)"
    if passed:
        print(f"CONFIRMED — TypeError raised when json.dumps encounters non-serializable dict key {(1,2)!r}; spec only permits OSError")
    else:
        print(f"NOT CONFIRMED — no TypeError raised; actual returned: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
