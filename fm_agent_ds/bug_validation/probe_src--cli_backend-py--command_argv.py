import sys
import traceback

try:
    from src.cli_backend import command_argv
except Exception as e:
    print(f'ERROR importing module: {e}')
    sys.exit(1)


# Create a custom class that has an 'argv' attribute but is NOT iterable
# and is NOT an AgentCommand — mirrors the trigger condition
class CustomCommand:
    def __init__(self):
        self.argv = ["custom-arg1", "custom-arg2"]


# Spec claim: the function should return a list of strings for any command.
# Actual code: line 129 calls list(command), which raises TypeError for
# non-iterable, non-AgentCommand inputs.
# We assert that TypeError IS raised → bug is CONFIRMED.

actual = None
error_raised = None

try:
    actual = command_argv(CustomCommand())
    error_raised = False
except TypeError as e:
    actual = e
    error_raised = True
except Exception as e:
    actual = e
    error_raised = True

if error_raised:
    # Bug confirmed: TypeError raised on a non-iterable, non-AgentCommand
    # input, violating the spec that claims it should work with any command.
    print(f'CONFIRMED — TypeError raised for non-AgentCommand, non-iterable input '
          f'(spec requires returning list of strings): {actual!r}')
else:
    print(f'NOT CONFIRMED — no error raised, actual output: {actual!r}')
