"""Probe attempt 3: test _validate_spec_update info_updated validation depth."""
import sys
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _validate_spec_update
except ImportError as e:
    print(f"ERROR: Could not import _validate_spec_update: {e}")
    sys.exit(1)

# Test 3a: info_updated=true, new_info has extra top-level keys beyond "callees"
test_3a = {
    "spec_updated": False,
    "new_spec": None,
    "info_updated": True,
    "new_info": {"callees": [], "extra_field": "should be rejected"},
    "updated_callees": [],
}

caught_3a = False
try:
    _validate_spec_update(test_3a)
except ValueError:
    caught_3a = True

# Test 3b: info_updated=true, callee entry has extra keys
test_3b = {
    "spec_updated": False,
    "new_spec": None,
    "info_updated": True,
    "new_info": {"callees": [{"name": "foo", "signature": "s", "pre_condition": "p", "post_condition": "q", "extra": "x"}]},
    "updated_callees": [],
}

caught_3b = False
try:
    _validate_spec_update(test_3b)
except ValueError:
    caught_3b = True

# Test 3c: info_updated=true but new_info missing required callee fields
test_3c = {
    "spec_updated": False,
    "new_spec": None,
    "info_updated": True,
    "new_info": {"callees": [{"name": "foo"}]},  # missing signature, pre_condition, post_condition
    "updated_callees": [],
}

caught_3c = False
try:
    _validate_spec_update(test_3c)
except ValueError:
    caught_3c = True

results = []
if caught_3a:
    results.append("3a: REJECTED extra top-level keys ✓")
else:
    results.append("3a: ACCEPTED extra top-level keys ✗ (potential minor gap)")

if caught_3b:
    results.append("3b: REJECTED extra callee keys ✓")
else:
    results.append("3b: ACCEPTED extra callee keys ✗ (potential minor gap)")

if caught_3c:
    results.append("3c: REJECTED missing callee fields ✓")
else:
    results.append("3c: ACCEPTED missing callee fields ✗ (potential minor gap)")

# Determine overall
all_caught = caught_3a and caught_3b and caught_3c
if all_caught:
    print("NOT CONFIRMED — validator correctly validates info structure depth.")
else:
    print("CONFIRMED — validator has info validation gaps.")
for r in results:
    print(f"  {r}")
