# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_count_mismatches.py
#
# _count_mismatches(results_dir) -> int
#
# Pre-condition:
#   - results_dir is a filesystem path
#
# Post-condition:
#   - Returns an integer ≥ 0; does not raise any exception
#   - When results_dir does not exist or is not a directory, returns 0
#   - When results_dir exists and is a directory, the returned value is the number of JSON
#     files (filenames ending in ".json") located anywhere in the directory tree rooted at
#     results_dir whose parsed JSON object contains the field "verdict" with the string
#     value "MISMATCH"
#   - Files whose filename does not end in ".json", files that cannot be opened for
#     reading, and files containing malformed JSON are excluded from the count
#   - Does not create, delete, rename, or modify any file or directory
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _count_mismatches(results_dir):
    """Count MISMATCH verdicts in a logic_verification_results/ tree.

    Each function's verdict is a JSON file nested under per-module directories;
    a ``"verdict"`` of ``"MISMATCH"`` marks a spec violation (a candidate bug).
    Unreadable or malformed files are skipped.
    """
    count = 0
    for root, _dirs, files in os.walk(results_dir):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(root, fname), "r") as f:
                    if json.load(f).get("verdict") == "MISMATCH":
                        count += 1
            except (OSError, ValueError):
                continue
    return count
