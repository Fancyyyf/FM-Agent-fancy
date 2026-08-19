"""Probe script for bug src--configure_llm-py--apply_local_backend_configuration.

The specification requires that apply_local_backend_configuration raises
ConfigWizardError when paths.toml_path does not identify a readable
fm-agent.toml file. When the file exists but lacks read permissions,
_read_text_if_exists raises PermissionError, which is not caught by
the calling code — violating the specification.
"""
import sys
import os
import stat
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))

try:
    from src.configure_llm import (
        apply_local_backend_configuration,
        WizardPaths,
        ConfigWizardError,
    )
except Exception as exc:
    print(f"ERROR: could not import src.configure_llm: {exc}")
    sys.exit(1)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_root = tmp / "project"
        project_root.mkdir()

        # Create fm-agent.toml with valid TOML but remove read permission
        toml_path = project_root / "fm-agent.toml"
        toml_path.write_text("[llm]\nbackend = \"opencode\"\nname = \"test-model\"\n", encoding="utf-8")
        # Make unreadable (even by owner)
        toml_path.chmod(0o000)

        # Create minimal .env file
        env_path = project_root / ".env"
        env_path.write_text("", encoding="utf-8")

        # Arbitrary opencode config path (should not be accessed for local backend)
        opencode_config_path = tmp / "opencode.json"

        paths = WizardPaths(
            project_root=project_root,
            env_path=env_path,
            toml_path=toml_path,
            opencode_config_path=opencode_config_path,
        )

        actual_str = ""
        raises_config_wizard_error = False
        raises_permission_error = False
        exc_type_name = ""

        try:
            result = apply_local_backend_configuration("opencode", paths)
            actual_str = "returned normally (did not raise)"
        except ConfigWizardError as exc:
            raises_config_wizard_error = True
            actual_str = f"ConfigWizardError: {exc}"
        except PermissionError as exc:
            raises_permission_error = True
            exc_type_name = type(exc).__name__
            actual_str = f"PermissionError: {exc}"
        except Exception as exc:
            exc_type_name = type(exc).__name__
            actual_str = f"{type(exc).__name__}: {exc}"
        finally:
            # Restore permissions so the tmpdir cleanup can succeed
            try:
                toml_path.chmod(0o644)
            except Exception:
                pass

        if raises_config_wizard_error:
            print(
                f"NOT CONFIRMED — function raised ConfigWizardError as spec requires: "
                f"{actual_str}"
            )
        elif raises_permission_error:
            print(
                f"CONFIRMED — spec requires ConfigWizardError for an unreadable toml file, "
                f"but code raised PermissionError (uncaught): {actual_str}"
            )
        else:
            print(
                f"CONFIRMED — spec requires ConfigWizardError for an unreadable toml file, "
                f"but actual: {actual_str}"
            )


if __name__ == "__main__":
    main()
