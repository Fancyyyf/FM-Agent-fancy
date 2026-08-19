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
