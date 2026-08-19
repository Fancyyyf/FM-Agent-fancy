import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock

# The probe runs from the repo root; ensure src/ is importable.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# All fixtures and temp data live under a fresh temporary directory owned by the probe.
PROBE_TMP = tempfile.mkdtemp(prefix="fm_agent_probe_")
proj_dir = os.path.join(PROBE_TMP, "project")
os.makedirs(proj_dir, exist_ok=True)

# Create an intent file that exists but is unreadable (mode 0000)
intent_file = os.path.join(PROBE_TMP, "unreadable_intent.txt")
with open(intent_file, "w") as f:
    f.write("test developer intent content")
os.chmod(intent_file, 0o000)

old_commit_id = "HEAD"

actual = None

try:
    # Mock the 'main' module before it gets imported by the function body.
    # This prevents any FM-Agent workflow from starting.
    mock_main = MagicMock()
    mock_main.run_pipeline = MagicMock(return_value=None)
    mock_main._run_setup_extract = MagicMock(return_value=None)
    mock_main.main = MagicMock(return_value=None)
    sys.modules['main'] = mock_main

    from src.incremental_reasoner import run_incremental_pipeline
    import src.incremental_reasoner as incr_mod

    # Mock check_last_run_existence to return True so we reach the
    # intent-file-reading code path (Stage 2) without falling back to
    # a full pipeline run (which would start FM-Agent).
    original_check = incr_mod.check_last_run_existence
    incr_mod.check_last_run_existence = lambda *a, **kw: True

    # Mock _setup_incremental_logging so it doesn't set up real file handlers
    original_setup_logging = incr_mod._setup_incremental_logging
    incr_mod._setup_incremental_logging = lambda wd: os.path.join(wd, "incremental_dummy.log")

    # Also mock stage_domain_knowledge_files to avoid side effects
    if hasattr(incr_mod, 'stage_domain_knowledge_files'):
        original_stage = incr_mod.stage_domain_knowledge_files
        incr_mod.stage_domain_knowledge_files = lambda *a, **kw: []

    result = run_incremental_pipeline(
        proj_dir,
        intent_file,
        old_commit_id,
    )
    # If we get here, no exception was raised — the bug was NOT triggered.
    actual = result
    print(f"NOT CONFIRMED — function returned {result!r} without raising an exception")

except PermissionError as e:
    actual = f"PermissionError: {e}"
    print(f"CONFIRMED — PermissionError raised: {e}")
except OSError as e:
    actual = f"OSError: {e}"
    print(f"CONFIRMED — OSError raised: {e}")
except ImportError as e:
    actual = f"ImportError: {e}"
    print(f"ERROR: ImportError — {e}")
    sys.exit(1)
except Exception as e:
    actual = f"{type(e).__name__}: {e}"
    print(f"CONFIRMED — unexpected exception {type(e).__name__}: {e}")
finally:
    # Cleanup: restore mocked modules and functions
    if 'incr_mod' in dir():
        if 'original_check' in dir():
            incr_mod.check_last_run_existence = original_check
        if 'original_setup_logging' in dir():
            incr_mod._setup_incremental_logging = original_setup_logging
        if 'original_stage' in dir():
            incr_mod.stage_domain_knowledge_files = original_stage

    # Restore the real main module
    sys.modules.pop('main', None)

    # Clean up temp files and directories
    try:
        if os.path.exists(intent_file):
            os.chmod(intent_file, 0o644)
    except Exception:
        pass
    if os.path.isdir(PROBE_TMP):
        shutil.rmtree(PROBE_TMP, ignore_errors=True)
