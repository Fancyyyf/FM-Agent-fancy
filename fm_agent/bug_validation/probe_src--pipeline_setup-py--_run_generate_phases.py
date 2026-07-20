import sys
import os
import tempfile
import json

# The project uses src/ as its package root; import via the public module path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.file_utils import _json_file_is_valid

# The spec requires that phases.json "conforms to the phases.json schema"
# (must contain a "phases" array with structured phase/module entries).
# _json_file_is_valid only checks that the file is valid JSON — it does
# NOT validate schema conformance.  A file containing "{}" is valid JSON
# but is NOT a valid phases.json document.

tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
try:
    # Write an empty JSON object: valid JSON, but NOT a valid phases.json schema.
    json.dump({}, tf)
    tf.close()

    is_valid = _json_file_is_valid(tf.name)

    # Bug: _json_file_is_valid returns True for any valid JSON, regardless
    # of schema.  The spec requires schema conformance, which {} breaks.
    # passed=True → bug reproduced (invalid schema passes validation).
    passed = is_valid

    if passed:
        print(
            "CONFIRMED — _json_file_is_valid returned True for '{}' "
            "(valid JSON but does NOT conform to phases.json schema)"
        )
    else:
        print(f"NOT CONFIRMED — _json_file_is_valid returned {is_valid!r}")
finally:
    os.unlink(tf.name)
