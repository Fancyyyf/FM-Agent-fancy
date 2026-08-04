# Bug Report: _check_codegraph_version

**Source file:** `src/env_check-py/_check_codegraph_version.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns (True, None) when the configured version, after stripping a leading 'v' prefix and surrounding whitespace, is empty. Returns (True, None) when the configured version is non-empty and the codegraph binary located within the configured bin_dir reports a version string that, after stripping surrounding whitespace, exactly equals the configured version (comparing after stripping any leading 'v' from the configured version). Returns (False, error_message) when the configured version is non-empty and any of the following hold: the codegraph binary cannot be invoked (not found, not executable, or a subprocess-level error occurs), the binary produces empty or whitespace-only output, or the binary's reported version differs from the configured version. The error_message is a non-empty, human-readable string. The function does not modify config, the filesystem, or any external state.

---

### Actual Behavior

The function returns a tuple (ok, msg) where ok is a boolean and msg is either a string or None. Let want = config.settings.codegraph.version.strip(); if want starts with 'v' then want = want[1:]. If want is empty, the function returns (True, None) without further action. Otherwise, let cmd = _codegraph_cmd() and bin = os.path.expanduser(config.settings.codegraph.bin_dir). The function attempts to run subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10). If the call raises OSError or subprocess.SubprocessError, let got = ''; otherwise let got = the stdout of the process stripped. If got is empty, the function returns (False, f'codegraph (pinned v{want}) is not installed at {bin}  run ./install.sh (C/C++ extraction falls back to the regex extractor otherwise).'). Else if got != want, the function returns (False, f'codegraph {got} is installed but v{want} is pinned in fm-agent.toml  re-run ./install.sh to install the pinned build.'). Else (got == want), it returns (True, None). No other side effects occur. If config.settings.codegraph.version is not a string or missing, an unhandled exception may propagate.

---

## Code Evidence

Line 11: cmd = _codegraph_cmd()  does not ensure the command references the binary inside the configured bin_dir. Line 14: [cmd, "--version"]  runs the binary without verifying its location against the bin_dir.

---

## Trigger Condition

The specification requires checking the codegraph binary located within the configured bin_dir. The code does not enforce that the executed binary is from that directory; it relies on whatever command _codegraph_cmd() returns, which may be a binary elsewhere on PATH. This allows a True return even when the binary in bin_dir is missing or broken, violating the condition that True must come from the binary in the specified bin_dir.

---

## How to trigger the bug

`_codegraph_cmd()` at `src/languages/codegraph.py:474` falls back to bare `"codegraph"` (resolved from PATH) when `os.access(bin_dir/codegraph, os.X_OK)` is False — i.e., when the pinned binary in the configured `bin_dir` is missing or not executable. `_check_codegraph_version` then runs `subprocess.run(["codegraph", "--version"], ...)` which picks up whatever codegraph binary exists on PATH, without verifying that it came from the configured `bin_dir`. If a codegraph binary with the matching version happens to be on PATH (e.g., a system-installed one), the function returns `(True, None)` even though the binary in `bin_dir` is absent, violating the specification which requires `True` only when the binary **in the configured bin_dir** reports the pinned version.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.settings.codegraph.version` | `"v0.1.0"` |
| `config.settings.codegraph.bin_dir` | `/tmp/bugprobe_.../empty_bin` (empty — no codegraph binary inside) |
| PATH (environment) | Includes a directory with a fake `codegraph` that outputs `"0.1.0"` |

### Expected (spec-correct) Output

`(False, error_message)` — because the codegraph binary in the configured `bin_dir` does not exist / cannot be invoked.

### Actual (buggy) Output

`(True, None)` — because `_codegraph_cmd()` falls back to bare `"codegraph"`, which resolves to the matching-version binary on PATH.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile

# Create an empty directory for bin_dir
tmp = tempfile.mkdtemp()
empty_bin = os.path.join(tmp, "empty_bin")
os.makedirs(empty_bin)

# Create a fake codegraph on PATH that outputs "0.1.0"
fake_bin = os.path.join(tmp, "fake_bin")
os.makedirs(fake_bin)
with open(os.path.join(fake_bin, "codegraph"), "w") as f:
    f.write("#!/bin/sh\necho '0.1.0'\n")
os.chmod(os.path.join(fake_bin, "codegraph"), 0o755)
os.environ["PATH"] = fake_bin + os.pathsep + os.environ["PATH"]

# Force _codegraph_cmd to return bare "codegraph" (simulating fallback)
import src.languages.codegraph as cg
orig = cg._codegraph_cmd
cg._codegraph_cmd = lambda: "codegraph"

class C:
    class settings:
        class codegraph:
            version = "v0.1.0"
            bin_dir = empty_bin

from src.env_check import _check_codegraph_version
print(_check_codegraph_version(C()))
# actual (buggy) output: (True, None)
# expected (correct) output: (False, "...")
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: (True, None) | expected: (False, error_message); bug: True returned despite codegraph missing in bin_dir '/tmp/bugprobe_7p3r4_7c/empty_bin'
```
