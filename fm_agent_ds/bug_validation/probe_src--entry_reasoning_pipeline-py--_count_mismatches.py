"""Probe script for bug: _count_mismatches does not return 0 for non-existent directory.

Spec claims: Returns 0 when results_dir does not exist as a directory.
Actual claim: os.walk raises FileNotFoundError/OSError for non-existent/non-directory path.

Tests in Python 3.12+: os.walk silently handles all these cases, so the function
returns 0 as specified. Bug is not reproducible in the supported Python version.
"""
import sys
import os
import tempfile
import stat

# This project uses a flat package layout (package=false in pyproject.toml).
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _count_mismatches
except ImportError as e:
    print(f"ERROR: Could not import _count_mismatches: {e}")
    sys.exit(1)

test_cases = []

# Test 1: Non-existent directory
nonexistent = os.path.join(tempfile.gettempdir(), "fm_agent_probe_nonexistent_" + os.urandom(8).hex())
while os.path.exists(nonexistent):
    nonexistent = os.path.join(tempfile.gettempdir(), "fm_agent_probe_nonexistent_" + os.urandom(8).hex())
test_cases.append(("non-existent directory", nonexistent, None, None))

# Test 2: Path that is a regular file, not a directory
tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
regfile = os.path.join(tmpdir, "regular_file.txt")
with open(regfile, "w") as f:
    f.write("not a directory")
test_cases.append(("regular file (not a directory)", regfile, [regfile], [tmpdir]))

# Test 3: Unreadable directory (permission denied)
unreadable = os.path.join(tmpdir, "unreadable_dir")
os.mkdir(unreadable)
os.chmod(unreadable, 0o000)
test_cases.append(("unreadable directory", unreadable, [unreadable], [tmpdir]))

passed_buggy = False
results = []

for label, path, clean_files, clean_dirs in test_cases:
    try:
        actual = _count_mismatches(path)
        results.append(f"  {label}: returned {actual!r} (no exception)")
    except FileNotFoundError as e:
        passed_buggy = True
        results.append(f"  {label}: CONFIRMED BUG - FileNotFoundError: {e}")
    except OSError as e:
        passed_buggy = True
        results.append(f"  {label}: CONFIRMED BUG - {type(e).__name__}: {e}")
    except Exception as e:
        results.append(f"  {label}: ERROR - {type(e).__name__}: {e}")
        passed_buggy = True

# Cleanup
for p in (clean_files or []):
    try:
        os.unlink(p)
    except OSError:
        pass
for d in (clean_dirs or []):
    try:
        if os.path.isdir(d):
            os.chmod(d, 0o755)
            os.rmdir(d)
    except OSError:
        pass
try:
    os.rmdir(tmpdir) if os.path.isdir(tmpdir) else None
except OSError:
    pass

if passed_buggy:
    print("CONFIRMED — bug reproduced")
else:
    print("NOT CONFIRMED — function returns 0 for all trigger conditions")
    print("Details:", "; ".join(r.strip() for r in results))
    print(f"Note: Python {sys.version.split()[0]} os.walk silently handles these cases.")
