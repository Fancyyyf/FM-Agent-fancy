import sys
import os
import json
import tempfile

# Add repo root to sys.path so we can import the package
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.opencode_trace import record_opencode_call

    # Bug: `summary or f"OpenCode {stage}"` treats any falsy value (like empty
    # string "") the same as None. The spec says only None should trigger the
    # default; an explicitly provided empty string should be used as-is.
    with tempfile.TemporaryDirectory() as work_dir:
        record_opencode_call(
            work_dir=work_dir,
            event_id="test_bug_001",
            stage="setup",
            status="success",
            started="2025-01-01T00:00:00Z",
            ended="2025-01-01T00:01:00Z",
            command=["echo", "hello"],
            summary="",  # non-None but falsy — spec says use it, code substitutes default
        )

        events_path = os.path.join(work_dir, "trace", "events.jsonl")
        with open(events_path, encoding="utf-8") as f:
            event = json.loads(f.readline().strip())

        actual = event["summary"]
        expected = ""  # spec: use provided value when non-None

        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
