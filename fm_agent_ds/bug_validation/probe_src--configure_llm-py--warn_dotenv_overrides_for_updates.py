"""Probe script: verify that warn_dotenv_overrides_for_updates raises
an exception for an unreadable .env file, contrary to the spec which
requires it to return False."""
import sys
import os
import stat
import tempfile
from pathlib import Path

# Probe is at: <project>/fm_agent/bug_validation/probe_<id>.py — 3 levels deep
_PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

try:
    import configure_llm as _configure_llm
    warn_dotenv_overrides_for_updates = _configure_llm.warn_dotenv_overrides_for_updates
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

confirmed = False
error_msg = ""

try:
    with tempfile.TemporaryDirectory(prefix="fm_agent_probe_") as tmpdir:
        env_file = Path(tmpdir) / ".env"

        # Create a dotenv-style file
        env_file.write_text("LLM_MODEL=test-model-override\nLLM_EFFORT=high\n")
        # Make it unreadable (removes read permission for owner/group/others)
        os.chmod(env_file, 0o000)

        # Verify the probe process itself cannot read it
        try:
            env_file.read_text()
            print("WARN: chmod 000 did not prevent reads (filesystem may not support Unix perms)")
            print("  This environment cannot reproduce the bug — proceeding with caution.")
        except PermissionError:
            pass  # expected — true unreadable file

        updates: dict[str, str] = {}
        try:
            result = warn_dotenv_overrides_for_updates(env_file, updates)
            # If we reach here without exception, the bug is NOT confirmed
            print(f"NOT CONFIRMED — function returned {result} instead of raising for unreadable .env file")
        except PermissionError:
            confirmed = True
            print("CONFIRMED — PermissionError raised for unreadable .env file; spec requires returning False")
        except OSError as exc:
            confirmed = True
            print(f"CONFIRMED — OSError ({type(exc).__name__}: {exc}) raised for unreadable .env file; spec requires returning False")
        except Exception as exc:
            confirmed = True
            print(f"CONFIRMED — Exception ({type(exc).__name__}: {exc}) raised for unreadable .env file; spec requires returning False")
        finally:
            # Restore permissions so tempdir cleanup doesn't fail
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
