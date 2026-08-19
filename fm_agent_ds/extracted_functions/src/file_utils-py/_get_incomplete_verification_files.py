def _get_incomplete_verification_files(layer_files, input_dir, output_dir, work_dir):
    """Return layer files missing verification or required bug validation output."""
    incomplete = []
    for rel in layer_files:
        result_path = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
        try:
            with open(result_path, "r") as f:
                result = json.load(f)
        except (OSError, json.JSONDecodeError):
            incomplete.append(rel)
            continue

        if result.get("verdict") != "MISMATCH":
            continue

        bug_id = os.path.splitext(rel)[0].replace(os.sep, "--").replace("/", "--")
        validation_path = os.path.join(work_dir, "bug_validation", f"{bug_id}.result.json")
        if not _json_file_is_valid(validation_path):
            incomplete.append(rel)
    return incomplete
