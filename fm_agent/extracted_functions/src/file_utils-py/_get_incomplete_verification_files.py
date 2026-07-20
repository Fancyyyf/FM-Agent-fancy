# [SPEC]
# Unit: src/file_utils.py
#
# _get_incomplete_verification_files(layer_files, input_dir, output_dir, work_dir) -> list
#
# Pre-condition:
#   - layer_files is an iterable of relative file paths (strings), each having a file extension.
#   - output_dir is a directory path containing (or expected to contain) verification result
#     JSON files.
#   - work_dir is a directory path; its "bug_validation" subdirectory contains (or is expected
#     to contain) bug validation result JSON files.
#
# Post-condition:
#   - Returns a list that is a subsequence of layer_files, preserving the relative order of
#     paths as they appear in layer_files.
#   - A path is excluded from the result (considered "complete") when EITHER:
#       1. A readable, well-formed JSON file exists at the path formed by
#          <output_dir>/<path_with_last_extension_replaced_by_.json>, and that JSON contains a
#          "verdict" key whose value is any string other than "MISMATCH".
#       OR
#       2. A readable, well-formed JSON file exists at that same output path, its "verdict"
#          value is "MISMATCH", AND a readable, well-formed JSON file exists at
#          <work_dir>/bug_validation/<bug_id>.result.json, where bug_id is derived from the
#          relative path by stripping its file extension and replacing both the final dot and
#          all path separators with "--".
#   - A path is INCLUDED in the result (considered "incomplete") when it fails any of the
#     conditions above — either because no readable verification JSON exists at the expected
#     path, or because a "MISMATCH" verdict is present without a valid corresponding bug
#     validation result.
#   - The function does not create, delete, or modify any filesystem state outside of its
#     own local variables and return value.
#   - The function does not raise exceptions for any combination of inputs (all error
#     conditions are absorbed and reported via the returned list).
# [SPEC]

# [INFO]
# _json_file_is_valid(path) -> bool
#   Pre-condition: path is a string referencing a filesystem location.
#   Post-condition: returns True if the file at path exists, is readable, and contains
#     well-formed JSON; returns False for any OSError or JSON decode failure.
# [INFO]

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
