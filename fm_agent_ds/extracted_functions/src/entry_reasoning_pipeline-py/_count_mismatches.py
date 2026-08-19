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
