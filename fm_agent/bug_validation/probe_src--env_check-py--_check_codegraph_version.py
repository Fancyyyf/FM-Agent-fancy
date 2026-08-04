"""
Probe for bug: _check_codegraph_version returns True when bin_dir binary is
missing but PATH has a matching codegraph version.

Spec requires True only when the binary IN BIN_DIR reports the right version.
Bug: _codegraph_cmd() falls back to bare "codegraph" (PATH) when bin_dir
binary is missing, and _check_codegraph_version doesn't verify the location.
"""

import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so "src" is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# ── 1. Create a temporary workspace ──────────────────────────────────────────
tmpdir = tempfile.mkdtemp(prefix="bugprobe_")

# ── 2. Create a fake codegraph binary on PATH that outputs "0.1.0" ──────────
fake_bin_dir = os.path.join(tmpdir, "fake_bin")
os.makedirs(fake_bin_dir, exist_ok=True)
fake_cg_path = os.path.join(fake_bin_dir, "codegraph")
with open(fake_cg_path, "w") as f:
    f.write("#!/bin/sh\necho '0.1.0'\n")
os.chmod(fake_cg_path, 0o755)
os.environ["PATH"] = fake_bin_dir + os.pathsep + os.environ.get("PATH", "")

# ── 3. Create an EMPTY bin_dir (where codegraph should be per config) ───────
empty_bin_dir = os.path.join(tmpdir, "empty_bin")
os.makedirs(empty_bin_dir, exist_ok=True)

# ── 4. Build a mock config matching the fake codegraph version ──────────────
class FakeCodegraphSettings:
    version = "v0.1.0"       # pinned version (matching what fake codegraph outputs)
    bin_dir = empty_bin_dir   # THIS dir has NO codegraph binary

class FakeSettings:
    codegraph = FakeCodegraphSettings()

class FakeConfig:
    settings = FakeSettings()
    LLM_API_KEY = "sk-test-dummy-key"  # needed to avoid import-side effects

# ── 5. Monkey-patch _codegraph_cmd to simulate the fallback-to-PATH case ────
# When bin_dir/codegraph is missing, _codegraph_cmd() returns bare "codegraph",
# which resolves from PATH.  We force that behavior.
import src.languages.codegraph as cg_module
_original_cg_cmd = cg_module._codegraph_cmd
cg_module._codegraph_cmd = lambda: "codegraph"

# ── 6. Call the function under test ─────────────────────────────────────────
from src.env_check import _check_codegraph_version

exit_code = 0
try:
    ok, msg = _check_codegraph_version(FakeConfig())

    # Per spec:  binary in bin_dir is missing → must return (False, error_msg)
    # Per code:  PATH has matching version → returns (True, None) ← BUG
    spec_expected_ok = False   # spec says "False when binary not in bin_dir"

    if ok == spec_expected_ok:
        print(
            f"NOT CONFIRMED — actual: ({ok}, {msg!r}) | expected: ({spec_expected_ok}, error_message)"
        )
    else:
        print(
            f"CONFIRMED — actual: ({ok}, {msg!r}) | expected: ({spec_expected_ok}, error_message); "
            f"bug: True returned despite codegraph missing in bin_dir '{empty_bin_dir}'"
        )
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit_code = 1
finally:
    # ── 7. Restore original state ───────────────────────────────────────────
    cg_module._codegraph_cmd = _original_cg_cmd
    shutil.rmtree(tmpdir, ignore_errors=True)

sys.exit(exit_code)
