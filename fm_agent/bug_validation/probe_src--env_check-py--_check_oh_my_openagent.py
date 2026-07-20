import sys
import os

# Ensure the repo root (cwd) is on sys.path so 'src' is importable
sys.path.insert(0, os.getcwd())

import subprocess as sp_module

# Save original before patching
_original_run = sp_module.run


class _FakeCompletedProcess:
    """Simulates bunx running but oh-my-openagent not found."""
    def __init__(self):
        self.returncode = 1
        self.stdout = ''
        self.stderr = 'error: package "oh-my-openagent" not found'


def _fake_run(args, **kwargs):
    return _FakeCompletedProcess()


# Monkey-patch so the function-under-test gets a non-zero returncode
# without an exception — exactly what triggers the bug.
sp_module.run = _fake_run

try:
    from src.env_check import _check_oh_my_openagent

    success, msg = _check_oh_my_openagent()

    # Spec claim: Returns (False, str) when command is not available.
    # Bug: returns (True, None) because only exceptions are caught,
    #      not non-zero return codes.
    expected_success = False
    expected_msg_is_str = True

    bug_confirmed = (
        success == True           # should be False — buggy
        and msg is None           # should be a string — buggy
    )

    if bug_confirmed:
        print(f'CONFIRMED — actual: (success={success}, msg={msg!r}) '
              f'| expected: (success=False, msg=<error string>)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: '
              f'(success={success}, msg={msg!r})')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    sp_module.run = _original_run
