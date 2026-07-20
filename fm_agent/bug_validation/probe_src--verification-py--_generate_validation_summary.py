import sys
import os
import json
import tempfile
import logging

# Suppress logging noise from the function under test
logging.basicConfig(level=logging.CRITICAL)

try:
    from src.verification import _generate_validation_summary

    with tempfile.TemporaryDirectory() as tmpdir:
        validation_dir = os.path.join(tmpdir, "bug_validation")
        os.makedirs(validation_dir)

        # Records with mixed id types in the SAME status group
        # This causes TypeError when comparing int vs str during sort
        records = [
            {"id": "abc", "confirmation_status": "confirmed"},
            {"id": 123, "confirmation_status": "confirmed"},
            {"id": "zzz", "confirmation_status": "confirmed"},
            {"confirmation_status": "confirmed"},  # missing id → b.get("id", "") = ""
        ]

        for i, record in enumerate(records):
            fpath = os.path.join(validation_dir, f"bug_{i}.result.json")
            with open(fpath, "w") as f:
                json.dump(record, f)

        try:
            _generate_validation_summary(tmpdir)
            print("NOT CONFIRMED — no TypeError raised during sort")
        except TypeError as e:
            print(f"CONFIRMED — TypeError raised: {e}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
