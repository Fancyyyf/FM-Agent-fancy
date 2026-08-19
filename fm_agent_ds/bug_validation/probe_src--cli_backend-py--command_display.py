import sys
import os

# Ensure the project root is on the Python path so 'src' can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    from src.cli_backend import command_display, AgentCommand

    # An argument containing a literal newline character should cause
    # command_display to return a string with an embedded newline, which
    # violates the spec claim: "The returned string contains no embedded
    # newline characters."

    cmd = AgentCommand(argv=["echo", "line1\nline2"])
    result = command_display(cmd)

    # Bug confirmed if the result has a newline (spec prohibits it)
    has_newline = "\n" in result

    if has_newline:
        print(f"CONFIRMED — result contains embedded newline: {result!r}")
    else:
        print(f"NOT CONFIRMED — no embedded newline in result: {result!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
