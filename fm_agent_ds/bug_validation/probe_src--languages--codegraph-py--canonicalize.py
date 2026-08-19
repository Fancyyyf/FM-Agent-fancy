import sys
import tempfile
import os
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Create a fresh temporary directory for the probe workspace
# (as required by FM-Agent self-validation guard)
_probe_workspace = tempfile.mkdtemp(prefix="canonicalize_probe_")

try:
    from src.languages.codegraph import canonicalize
except ImportError as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: Cannot import canonicalize: {e}')
    sys.exit(1)

test_inputs = [
    ("operator/", "operator_"),
    ("ns::operator/", "ns::operator_"),
    ("normal_function", "normal_function"),
    ("", ""),
    ("a/b/c", "a_b_c"),
]

all_passed = True
details = []

for input_val, expected in test_inputs:
    actual = canonicalize(input_val)
    if actual == expected:
        details.append(f"OK: {input_val!r} -> {actual!r}")
    else:
        details.append(f"FAIL: {input_val!r} -> {actual!r} (expected {expected!r})")
        all_passed = False

# The bug claim: '/' might not be in _UNSAFE, so inputs with '/' would not be sanitized.
# We test directly: if canonicalize("operator/") returns "operator_", the bug is NOT CONFIRMED.
passed = canonicalize("operator/") != "operator_"

if passed:
    print(f'CONFIRMED — canonicalize("operator/") returned {canonicalize("operator/")!r}, not "operator_"')
else:
    print(f'NOT CONFIRMED — canonicalize("operator/") returned {canonicalize("operator/")!r}')
    for d in details:
        print(f'  {d}')

# Cleanup probe workspace
try:
    os.rmdir(_probe_workspace)
except OSError:
    pass
