import sys
import os
import tempfile

# Ensure repo root is on sys.path for package imports
# Script lives in fm_agent/bug_validation/ → walk up 3 levels
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.opencode_trace import _opencode_trace_path, _trace_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = tmpdir
        trace_dir = _trace_dir(work_dir)

        # Benign event_id — should resolve inside trace_dir/opencode/
        benign_path = _opencode_trace_path(work_dir, "test_event")
        benign_resolved = os.path.normpath(benign_path)

        # Malicious event_id with path traversal — should escape opencode/
        malicious_path = _opencode_trace_path(work_dir, "../other")
        malicious_resolved = os.path.normpath(malicious_path)

        # Expected base: trace_dir/opencode/
        opencode_dir = os.path.normpath(os.path.join(trace_dir, "opencode"))

        # Check if the benign path is correctly within opencode/
        benign_within = benign_resolved.startswith(opencode_dir + os.sep) or benign_resolved == opencode_dir

        # Check if the malicious path escapes opencode/
        malicious_escapes = not (
            malicious_resolved.startswith(opencode_dir + os.sep)
            or malicious_resolved == opencode_dir
        )

        if not benign_within:
            print(f"ERROR: benign path escaped opencode/ — unexpected: {benign_resolved}")
            sys.exit(1)

        # Bug: ../other should NOT escape opencode/ per the spec,
        # but the unsanitized os.path.join allows it.
        if malicious_escapes:
            print(
                f"CONFIRMED — path traversal: event_id='../other' "
                f"→ {malicious_resolved} escapes {opencode_dir}"
            )
        else:
            print(
                f"NOT CONFIRMED — malicious path stayed within opencode/: "
                f"{malicious_resolved}"
            )

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
