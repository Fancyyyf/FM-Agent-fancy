"""Probe for _elp_argv bug: settings.erlang.command.strip() fails when command is None."""
import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from config import settings
    from src.languages import erlang as erlang_module

    # Save original value
    orig = settings.erlang.command

    # Bypass pydantic validation to set command to None
    object.__setattr__(settings.erlang, 'command', None)

    try:
        result = erlang_module._elp_argv()
        # If we reach here, no AttributeError was raised
        print(f'NOT CONFIRMED — _elp_argv() returned {result!r} without error')
    except AttributeError as e:
        print(f'CONFIRMED — AttributeError raised when command is None: {e}')
    except Exception as e:
        print(f'ERROR — unexpected exception: {type(e).__name__}: {e}')
    finally:
        # Restore original value
        object.__setattr__(settings.erlang, 'command', orig)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
