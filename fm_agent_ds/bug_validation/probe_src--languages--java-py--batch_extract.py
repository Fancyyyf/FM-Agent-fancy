"""Probe for bug: batch_extract() propagates exception instead of returning {} when from_proj_dir fails.

Spec claim: Returns an empty dict if the CodeGraph backend cannot be initialized for the project.
Actual: if from_proj_dir raises an exception (e.g. TypeError for None input), the function crashes.
Trigger: call batch_extract with an input that causes from_proj_dir to raise.
"""

import sys
import traceback

# FM-Agent self-validation guard: do NOT invoke run_pipeline, main.py, or any FM-Agent workflow.
# Test only the smallest relevant unit.

try:
    from src.languages.java import batch_extract
except Exception as e:
    print(f"ERROR: Failed to import batch_extract: {e}")
    sys.exit(1)

# The spec claims: "Returns an empty dict if the CodeGraph backend cannot be initialized"
# If from_proj_dir raises, the code does not catch it — the exception propagates.
# Test with None: os.path.abspath(None) raises TypeError.

all_passed = True
results = []

# Test case 1: proj_dir = None (causes TypeError in os.path.abspath)
try:
    actual = batch_extract(None)  # type: ignore — testing runtime behavior
    # If we got here, the function handled it (returned something)
    spec_expected = {}
    if actual == spec_expected:
        results.append(f"PASS: batch_extract(None) returned {{}} as spec requires")
    else:
        results.append(f"NOT CONFIRMED: batch_extract(None) returned {actual!r} instead of {{}}")
        all_passed = False
except TypeError as e:
    # Bug confirmed: exception propagated instead of returning {}
    results.append(f"CONFIRMED: batch_extract(None) raised TypeError: {e}")
    results.append("Spec requires returning {}; got exception instead")
    all_passed = False
except Exception as e:
    results.append(f"CONFIRMED: batch_extract(None) raised {type(e).__name__}: {e}")
    all_passed = False

# Test case 2: proj_dir with null byte (causes ValueError in os.path.abspath)
try:
    actual = batch_extract("/tmp/\x00test")  # type: ignore
    spec_expected = {}
    if actual == spec_expected:
        results.append(f"PASS: batch_extract('/tmp/\\x00test') returned {{}} as spec requires")
    else:
        results.append(f"NOT CONFIRMED: batch_extract('/tmp/\\x00test') returned {actual!r} instead of {{}}")
        all_passed = False
except ValueError as e:
    results.append(f"CONFIRMED: batch_extract('/tmp/\\x00test') raised ValueError: {e}")
    results.append("Spec requires returning {}; got exception instead")
    all_passed = False
except Exception as e:
    results.append(f"CONFIRMED: batch_extract('/tmp/\\x00test') raised {type(e).__name__}: {e}")
    all_passed = False

# Final verdict
for line in results:
    print(line)

if all_passed:
    print("NOT CONFIRMED — batch_extract correctly returns {} on all edge cases tested")
else:
    print("CONFIRMED — batch_extract propagates exception(s) instead of returning {}")
