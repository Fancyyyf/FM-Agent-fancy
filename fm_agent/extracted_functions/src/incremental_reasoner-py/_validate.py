# [SPEC]
# Unit: src/incremental_reasoner-py/_validate.py
#
# _validate(rel) -> str
#
# Pre-condition:
#   - rel is a non-empty relative path string identifying an extracted function file.
#   - output_dir, proj_dir, and work_dir are valid directory paths accessible from the enclosing scope.
#
# Post-condition:
#   - A bug validation is performed for the function identified by rel, producing or overwriting a
#     result JSON file at the path derived by replacing the extension of rel with ".json" and resolving
#     it relative to output_dir.
#   - Returns rel unchanged.
# [SPEC]

# [INFO]
# _validate_single_bug(result_json_rel, proj_dir, work_dir) -> None
#   Pre-condition: result_json_rel is a non-empty relative path to a verification result JSON file;
#     proj_dir and work_dir are valid directory paths.
#   Post-condition: If the result JSON has a MISMATCH verdict, a bug validation report and verdict
#     file are produced under bug_validation/ in proj_dir. For non-MISMATCH verdicts, no bug
#     validation files are produced.
# [INFO]

    def _validate(rel):
        result_json_rel = os.path.join(
            os.path.relpath(output_dir, proj_dir),
            os.path.splitext(rel)[0] + ".json",
        )
        _validate_single_bug(result_json_rel, proj_dir, work_dir)
        return rel