import sys
import os

# Ensure the repo root is on the path so that 'src' is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class CustomBaseException(BaseException):
    """Exception that inherits from BaseException, not Exception."""

try:
    from src.verification import _spec_task_exit_code

    class BuggyHandle:
        def done(self):
            return True

        def result(self):
            raise CustomBaseException("test probe exception")

    handle = BuggyHandle()
    try:
        actual = _spec_task_exit_code(handle)
        expected = 1
        passed = actual != expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except CustomBaseException:
        # Bug confirmed: the exception propagated because except Exception
        # on line 59/34 only catches Exception subclasses, not BaseException.
        print(
            "CONFIRMED — CustomBaseException propagated (not caught "
            "by except Exception), expected return 1"
        )
    except BaseException as e:
        print(f"ERROR: unexpected: {type(e).__name__}: {e}")
        sys.exit(1)

except BaseException as e:
    print(f"ERROR: import/setup failed: {type(e).__name__}: {e}")
    sys.exit(1)
