"""Probe script for bug dashboard-py--_parse_iso.

Tests whether _parse_iso correctly parses a valid ISO 8601 ordinal date
timestamp. Per the specification, any valid ISO 8601 timestamp string
should be parsed and returned as a datetime object. However,
datetime.fromisoformat (used by the implementation) does not support
ordinal date formats like '2021-001T00:00:00Z'.

This test uses several valid ISO 8601 formats that fromisoformat
may not support, to confirm the specification/implementation gap.
"""
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so that 'from dashboard import ...' works.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# The probe must not use fm_agent/ as its runtime workspace.
# Use a fresh temporary directory for any runtime outputs.
PROBE_TMP = tempfile.mkdtemp(prefix="probe_parse_iso_")

try:
    from dashboard import _parse_iso
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Test case 1 (primary): ordinal date — valid ISO 8601, unsupported by fromisoformat
# Specification says: "any valid ISO 8601 timestamp string" should parse successfully
try:
    result = _parse_iso("2021-001T00:00:00Z")
except Exception as e:
    print(f"ERROR during ordinal date test: {e}")
    sys.exit(1)

if result is None:
    # Bug confirmed: valid ISO 8601 string returned None instead of datetime
    print("CONFIRMED — ordinal date '2021-001T00:00:00Z' returned None (expected a datetime object per spec)")
else:
    # fromisoformat parsed it successfully — spec and implementation match for this input
    print(f"NOT CONFIRMED — ordinal date '2021-001T00:00:00Z' returned {result!r} (datetime parsed OK)")
