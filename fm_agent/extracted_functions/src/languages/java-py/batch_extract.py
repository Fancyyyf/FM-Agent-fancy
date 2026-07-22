# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/java-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a valid project directory
#
# Post-condition:
#   - When a Java code graph backend is available, returns a dict mapping each absolute
#     file path (str) in the project to a list of (function_name: str, function_body: str)
#     tuples, covering all Java functions discovered in the project
#   - When the Java backend is unavailable, returns an empty dict
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid project directory path
#   Post-condition: Returns a CodeGraphExtractor instance initialized for the project,
#     or None when the Java code graph backend cannot be initialized
# [SPLIT]
# cg.get_functions_by_file("java", proj_dir) -> dict
#   Pre-condition: cg is a valid CodeGraphExtractor instance; proj_dir is a valid
#     project directory path
#   Post-condition: Returns a dict mapping each absolute file path (str) to a list of
#     (function_name: str, function_body: str) tuples for Java functions. Each function body
#     ends with a newline; source files that cannot be read are silently omitted.
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all Java files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("java", proj_dir) if cg else {}
