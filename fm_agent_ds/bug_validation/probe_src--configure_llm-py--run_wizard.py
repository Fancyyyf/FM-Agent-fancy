"""Probe script for bug src--configure_llm-py--run_wizard.

The specification requires that run_wizard() raises ConfigWizardError when
configuration cannot be completed due to an unrecoverable error such as an
unwritable configuration path. The code instead returns a non-zero value from
run_local_backend_configuration, which does not raise the required exception.

This probe tests the non-opencode backend path: select a local CLI backend,
confirm the operation, and verify that an unwritable fm-agent.toml file
causes ConfigWizardError to be raised.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add repo root to sys.path so the src package is importable.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.configure_llm import run_wizard, ConfigWizardError
except Exception as exc:
    print(f'ERROR: could not import src.configure_llm: {exc}')
    sys.exit(1)

_attempts_remaining = 3
_confirmed = False
_last_stdout = ""

for attempt in range(1, _attempts_remaining + 1):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # Create a minimal valid fm-agent.toml so the read succeeds.
            toml_path = project_root / "fm-agent.toml"
            toml_path.write_text('[llm]\nbackend = "opencode"\n', encoding="utf-8")
            toml_path.chmod(0o644)

            # Make the project root read-only (r-xr-xr-x) so that
            # backup_file cannot create a new file and atomic_write
            # cannot create its temp file in the same directory.
            project_root.chmod(0o555)

            # Mock the interactive prompts:
            #   _prompt_backend  → return "auto"  (non-opencode backend)
            #   _prompt_yes_no   → return True    (confirm the write)
            with patch(
                "src.configure_llm._prompt_backend", return_value="auto"
            ), patch(
                "src.configure_llm._prompt_yes_no", return_value=True
            ):
                # The spec requires ConfigWizardError here, but the code
                # throws PermissionError (or similar) instead.
                result = run_wizard(project_root)
                # If we reach this line, no exception was raised at all.
                _last_stdout = (
                    f"CONFIRMED — run_wizard() returned {result!r} "
                    f"instead of raising ConfigWizardError "
                    f"(unwritable configuration path)"
                )
                print(_last_stdout)
                _confirmed = True
                break

    except ConfigWizardError:
        # The code actually raised ConfigWizardError — the bug is NOT present.
        _last_stdout = (
            "NOT CONFIRMED — ConfigWizardError was raised as expected, "
            "the code matches the specification"
        )
        print(_last_stdout)
        _confirmed = False
        break

    except PermissionError as exc:
        # PermissionError: backup_file or atomic_write could not write to the
        # read-only directory. This is the bug: the code raises the wrong
        # exception type instead of ConfigWizardError.
        _last_stdout = (
            f"CONFIRMED — run_wizard() raised {type(exc).__name__} "
            f"instead of ConfigWizardError for an unwritable path: {exc}"
        )
        print(_last_stdout)
        _confirmed = True
        break

    except Exception as exc:
        # Some other unexpected exception was raised — still a bug because
        # it's not ConfigWizardError.
        _last_stdout = (
            f"CONFIRMED — run_wizard() raised {type(exc).__name__} "
            f"instead of ConfigWizardError: {exc}"
        )
        print(_last_stdout)
        _confirmed = True
        break

    finally:
        # Restore writability so the tempdir cleanup can succeed.
        try:
            project_root.chmod(0o755)
        except Exception:
            pass

if not _confirmed:
    # Last attempt didn't confirm — report final classification.
    if _last_stdout:
        print(_last_stdout)
    else:
        print("NOT CONFIRMED — all attempts exhausted, could not trigger the bug")
