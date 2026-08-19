"""Probe script for bug: src--verification-py--_spec_task_done

The spec claims _spec_task_done returns False when handle is None,
but the code returns True (line 7: return True as the fallback).
"""
import sys
import os

# When run from repo root, the 'src' package should be importable.
# Add repo root to path so the probe works regardless of how it's invoked.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.verification import _spec_task_done

    # The trigger condition: handle is None.
    # Spec says: return False when handle is None.
    # Buggy code: returns True (the fallback on line 7).
    actual = _spec_task_done(None)
    expected = False  # what the spec requires

    passed = actual != expected  # True means the bug is reproduced

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')

        # Additional sanity: verify correct cases still work (Popen / Future)
        import concurrent.futures
        import subprocess
        import threading

        # Popen: running process should be "not done"
        proc = subprocess.Popen(['sleep', '0.1'])
        assert _spec_task_done(proc) is False, "running Popen should be not done"
        proc.wait()
        assert _spec_task_done(proc) is True, "completed Popen should be done"

        # Future: a not-yet-done future should be "not done"
        with concurrent.futures.ThreadPoolExecutor() as ex:
            barrier = threading.Barrier(2, timeout=5)
            def slow_task():
                barrier.wait()
                return 42
            fut = ex.submit(slow_task)
            assert _spec_task_done(fut) is False, "not-yet-completed future should be not done"
            barrier.wait()
            fut.result()
            assert _spec_task_done(fut) is True, "completed future should be done"

        print("CONFIRMED — additional sanity checks passed")
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
