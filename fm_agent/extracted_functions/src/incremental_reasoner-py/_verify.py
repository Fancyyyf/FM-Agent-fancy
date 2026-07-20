# [SPEC]
# Unit: src/incremental_reasoner-py/_verify.py
#
# _verify(rel) -> (str, str)
#
# Pre-condition:
#   - rel is a string representing a relative path to an extracted function file
#     under the extracted_dir directory
#   - The enclosing scope provides: extracted_dir (directory path), output_dir (directory
#     path), work_dir (directory path or None), and _VERIFY_EXT_TO_LANG (a dict mapping
#     file extensions to language identifier strings)
#
# Post-condition:
#   - Returns a 2-tuple (rel, verdict) where rel is the exact str passed as input
#     and verdict is the verification result produced by the callee
#   - verdict is one of "MATCH", "MISMATCH", "ERROR", or "SKIPPED" — each representing
#     a distinct category of conformance between the function's [SPEC] block and its
#     implementation
#   - The language identifier passed to the callee is resolved from the file extension
#     of the path formed by joining extracted_dir and rel; if the extension is not
#     present in _VERIFY_EXT_TO_LANG, the language defaults to "C"
# [SPEC]

# [INFO]
# _verify_single_file(filepath, extracted_dir, output_dir, language, work_dir=work_dir) -> (_, str)
#   Pre-condition: filepath is an absolute or well-formed path to an extracted function
#     file containing a valid [SPEC] block; language is a string identifier recognized
#     by the verifier; work_dir is a filesystem directory path or None
#   Post-condition: Returns a tuple whose second element is a verdict string
#     ("MATCH", "MISMATCH", "ERROR", or "SKIPPED") describing whether the implementation
#     satisfies its specification
# [INFO]

    def _verify(rel):
        fpath = os.path.join(extracted_dir, rel)
        language = _VERIFY_EXT_TO_LANG.get(os.path.splitext(fpath)[1], "C")
        _, verdict = _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir=work_dir)
        return rel, verdict
