import sys
import os

# Add the repo root to sys.path so 'src' can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.verification import _spec_task_exit_code

    class FailingDoneHandle:
        """Handle where done() raises an exception.

        Per spec: when done() raises, it does not return True,
        so None should be returned. The bug is that handle.done()
        is called without exception handling on line 55.
        """
        def done(self):
            raise RuntimeError("done() failed unexpectedly")

    handle = FailingDoneHandle()

    # handle has no 'returncode' attribute -> skips first if
    # handle has 'done' attribute -> enters second if
    # handle.done() raises -> spec says return None, code propagates exception
    actual = _spec_task_exit_code(handle)
    # If we reach here, the exception was caught somewhere — bug NOT confirmed
    print(f'NOT CONFIRMED -- _spec_task_exit_code returned {actual!r}')
except Exception as e:
    # Exception propagated — bug CONFIRMED (spec requires None)
    print(f'CONFIRMED -- done() exception propagated as: {type(e).__name__}: {e}')
    print(f'(spec requires returning None when done() raises)')
