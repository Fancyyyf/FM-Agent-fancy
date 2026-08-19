import sys
import os
import tempfile
import shutil
from pathlib import Path

# The probe runs from the repo root; ensure the repo root is on the path
# so that 'import dashboard' finds dashboard.py.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    import dashboard
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

tmpdir = Path(tempfile.mkdtemp(prefix="probe_locate_workdir_"))
proj_dir = tmpdir / "myproject"
proj_dir.mkdir()

# Create the real fm_agent target directory
fm_agent_real = tmpdir / "fm_agent_real"
fm_agent_real.mkdir()

# Create a symlink: myproject/fm_agent -> ../fm_agent_real
# When _locate_workdir runs without trace/, it returns proj_dir_resolved / "fm_agent"
# which will be the symlink — NOT resolved to the real target.
os.symlink("../fm_agent_real", str(proj_dir / "fm_agent"))

# NO trace/ subdir — triggers the else branch (line 188 in dashboard.py)
assert not (proj_dir / "trace").exists(), "trace/ should not exist — buggy path"

actual = dashboard._locate_workdir(str(proj_dir))
expected = actual.resolve()  # proper spec-compliant output follows the symlink

passed = str(actual) != str(expected)

# Cleanup
shutil.rmtree(str(tmpdir), ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual (unresolved symlink): {actual!r} | expected (resolved): {expected!r}')
else:
    print(f'NOT CONFIRMED — actual already resolved: {actual!r}')
