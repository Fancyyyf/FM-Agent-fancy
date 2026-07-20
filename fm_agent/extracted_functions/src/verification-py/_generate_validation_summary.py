# [SPEC]
# Unit: src/verification-py/_generate_validation_summary.py
#
# _generate_validation_summary(proj_dir) -> None
#
# Pre-condition:
#   - proj_dir is a string path to a directory
#
# Post-condition:
#   - If proj_dir/bug_validation/ does not exist or is not a directory,
#     the function returns with no file written
#   - Otherwise, every entry in proj_dir/bug_validation/ whose name ends with
#     ".result.json" and whose contents are valid JSON is included in the
#     summary; entries that cannot be read or parsed produce a warning and are
#     excluded from the summary
#   - Writes proj_dir/bug_validation/summary.json via an atomic rename (temp
#     file then os.replace) containing:
#     - total_reported: the number of successfully parsed .result.json records
#     - total_confirmed: count where confirmation_status == "confirmed"
#     - total_not_confirmed: count where confirmation_status == "not_confirmed"
#     - total_error: count where confirmation_status == "error"
#     - bugs: array of all parsed records, sorted by status group then by id:
#       confirmed (ascending by id), then not_confirmed (ascending), then error
#       (ascending), then any other status (ascending)
#   - Unknown confirmation_status values (neither "confirmed", "not_confirmed",
#     nor "error") are sorted after the three known groups, alphabetically by id
#   - The written JSON uses 2-space indentation and preserves non-ASCII
#     characters (ensure_ascii=False)
# [SPEC]

# [INFO]
# os.path.isdir(path) -> bool
#   Pre-condition: path is a string
#   Post-condition: Returns True when path refers to an existing directory;
#     False otherwise
# [SPLIT]
# os.listdir(path) -> list[str]
#   Pre-condition: path is an existing directory path
#   Post-condition: Returns a list of entry names in the directory; the order
#     is arbitrary and must not be relied upon
# [SPLIT]
# json.load(file) -> Any
#   Pre-condition: file is a readable text-mode file object positioned at the
#     start of valid JSON text
#   Post-condition: Returns the Python object decoded from the JSON text;
#     raises json.JSONDecodeError if the content is not valid JSON
# [SPLIT]
# json.dump(obj, file, indent=2, ensure_ascii=False) -> None
#   Pre-condition: file is a writable text-mode file object; obj is a
#     JSON-serializable Python value
#   Post-condition: Writes the JSON representation of obj to file using the
#     given indent; non-ASCII characters appear as literal Unicode rather
#     than \uXXXX escapes
# [SPLIT]
# os.replace(src, dst) -> None
#   Pre-condition: src and dst are string paths on the same filesystem;
#     src exists
#   Post-condition: On POSIX systems, atomically replaces dst with src;
#     after the call, dst contains what was at src and src no longer exists
# [SPLIT]
# sorted(iterable) -> list
#   Pre-condition: iterable is an iterable of mutually comparable elements
#   Post-condition: Returns a new list containing all elements of iterable in
#     ascending order according to their natural comparison
# [INFO]

def _generate_validation_summary(proj_dir):
    """Scan bug_validation/*.result.json files and write summary.json."""
    validation_dir = os.path.join(proj_dir, "bug_validation")
    if not os.path.isdir(validation_dir):
        logging.info("No bug_validation directory found, skipping summary.")
        return

    bugs = []
    for fname in sorted(os.listdir(validation_dir)):
        if not fname.endswith(".result.json"):
            continue
        fpath = os.path.join(validation_dir, fname)
        try:
            with open(fpath, "r") as f:
                record = json.load(f)
            bugs.append(record)
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning(f"Could not read {fpath}: {exc}")

    confirmed = sum(1 for b in bugs if b.get("confirmation_status") == "confirmed")
    not_confirmed = sum(1 for b in bugs if b.get("confirmation_status") == "not_confirmed")
    errors = sum(1 for b in bugs if b.get("confirmation_status") == "error")

    # Sort: confirmed first, then not_confirmed, then error; alphabetical by id within each group
    status_order = {"confirmed": 0, "not_confirmed": 1, "error": 2}
    bugs.sort(key=lambda b: (status_order.get(b.get("confirmation_status"), 3), b.get("id", "")))

    summary = {
        "total_reported": len(bugs),
        "total_confirmed": confirmed,
        "total_not_confirmed": not_confirmed,
        "total_error": errors,
        "bugs": bugs,
    }

    summary_path = os.path.join(validation_dir, "summary.json")
    tmp_path = summary_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, summary_path)
    logging.info(f"Validation summary written to {summary_path}")
    logging.info(f"  confirmed: {confirmed}, not_confirmed: {not_confirmed}, error: {errors}")
