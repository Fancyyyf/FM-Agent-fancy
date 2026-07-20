import sys
import os

# Add repo root to sys.path so 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src import opencode_trace
    trace_dir = "/tmp"
    path = "/tmp/foo"

    # _payload_ref is internal, but we access it through the public module
    actual = opencode_trace._payload_ref(trace_dir, path)
    # spec-correct: relative path from trace_dir to path
    expected = os.path.relpath(path, trace_dir)
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
