"""Probe script for bug: _read_error_body does not catch BaseException subclasses from read()."""
import sys
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.llm_client import _read_error_body


# Custom exception inheriting directly from BaseException (NOT Exception).
# The spec requires _read_error_body to tolerate ANY exception type from read(),
# but the code uses `except Exception:` which misses direct BaseException subclasses.
class FakeBaseException(BaseException):
    pass


class MockWithRead:
    """Mock whose read() raises FakeBaseException, which is NOT an Exception subclass."""
    def read(self):
        raise FakeBaseException("simulated read failure")


try:
    result = _read_error_body(MockWithRead())
    # If we get here, _read_error_body caught the BaseException → spec is satisfied → bug NOT reproduced
    print(f"NOT CONFIRMED — function returned {result!r} (caught BaseException subclass)")
except FakeBaseException as e:
    # Bug confirmed: BaseException propagated instead of being caught and returning ""
    print(f"CONFIRMED — FakeBaseException propagated: {e} | Spec requires: return '' for any exception from read()")
except BaseException as e:
    print(f"ERROR: unexpected BaseException: {type(e).__name__}: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)
