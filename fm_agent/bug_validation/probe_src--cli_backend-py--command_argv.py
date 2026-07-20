"""Probe script for bug: src--cli_backend-py--command_argv"""

import sys
import os

# Ensure the repo root is on sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.cli_backend import command_argv

    # An object that has an `argv` attribute (list of strings) but is NOT an AgentCommand.
    # The spec says it should return the same argv list object.
    # The code will fall through to `list(command)`, which raises TypeError since
    # FakeCommand instances are not iterable.
    class FakeCommand:
        argv = ['arg1', 'arg2']

    cmd = FakeCommand()
    result = command_argv(cmd)

    # If we reach here (no exception), the code DID iterate (possibly returning wrong results)
    expected = FakeCommand.argv
    passed = result is not expected  # Bug: should be same reference, but isn't
    if passed:
        print(f'CONFIRMED — actual: {result!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result!r}')
except TypeError as e:
    # The bug triggers TypeError, which the spec says should never happen
    print(f'CONFIRMED — TypeError raised: {e}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
