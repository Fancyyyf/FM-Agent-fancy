import os
import sys
import tempfile

# Ensure repo root is on sys.path so 'src' package resolves
repo_root = os.path.dirname(os.path.abspath(__file__))
# Walk up to find the repo root (containing src/ and config.py)
for _ in range(5):
    if os.path.isdir(os.path.join(repo_root, "src")) and os.path.isfile(os.path.join(repo_root, "config.py")):
        break
    repo_root = os.path.dirname(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    # Load via the package entry point: src.languages.erlang
    from src.languages.erlang import ElpClient, _timeout_seconds
except Exception as e:
    print(f"ERROR: Failed to import package: {e}")
    sys.exit(1)

# The spec claims self.timeout must be a positive numeric value.
# The bug claim: _timeout_seconds() could return 0, violating the spec.
# The code: _timeout_seconds() returns max(1, settings.erlang.timeout_s),
# which guarantees the result is always >= 1 (positive).

passed = None  # True means bug confirmed; False means not confirmed

try:
    # Test 1: _timeout_seconds() alone
    timeout = _timeout_seconds()
    if timeout <= 0:
        passed = True
    # Test 2: ElpClient.__init__ with a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        client = ElpClient(tmpdir)
        if client.timeout <= 0:
            passed = True
    # If we get here without confirming: bug is NOT confirmed
    if passed is None:
        passed = False
except Exception as e:
    print(f"ERROR: Probe raised exception: {e}")
    sys.exit(1)

if passed:
    print("CONFIRMED — _timeout_seconds() returned non-positive value")
else:
    print("NOT CONFIRMED — _timeout_seconds() returns max(1, settings.erlang.timeout_s), always >= 1")
    print(f"  _timeout_seconds() returned: {timeout}")
    print(f"  client.timeout: {client.timeout}")
