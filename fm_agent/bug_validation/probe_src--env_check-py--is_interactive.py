import sys
import os

# Ensure repo root is on sys.path so 'src' is importable
# This probe is at fm_agent/bug_validation/probe_<bug_id>.py
# Repo root is 2 levels up
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

try:
    import src.env_check as env_check

    # The bug: is_interactive() depends on 'sys' being in the module's global namespace.
    # The spec says the return value must not depend on any mutable state.
    # By removing 'sys' from the module dict, we test whether the function
    # truly only depends on the file descriptor table (as the spec requires)
    # or depends on mutable global state (the presence of 'sys').
    del env_check.sys

    result = env_check.is_interactive()
    # If we get here, 'sys' was somehow still accessible
    print(f"NOT CONFIRMED — is_interactive() returned {result!r} even after removing sys from module globals")
except NameError as e:
    print(f"CONFIRMED — is_interactive() raised NameError after removing sys from module globals: {e}")
except AttributeError as e:
    print(f"CONFIRMED — is_interactive() raised AttributeError: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
