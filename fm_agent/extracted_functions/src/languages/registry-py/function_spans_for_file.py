# [SPEC]
# Unit: src/languages/registry-py/function_spans_for_file.py
#
# function_spans_for_file(proj_dir, filepath, lang_key) -> [(str, int, int)] | None
#
# Pre-condition:
#   - proj_dir is a string
#   - filepath is a string
#   - lang_key is a string
#
# Post-condition:
#   - When lang_key is not present in REGISTRY, returns None
#   - When lang_key is present in REGISTRY, returns the registered handler's
#     function_spans result for (proj_dir, filepath) without modification
#   - A non-None return value is a list where each element is a tuple (name, start, end):
#       * name is the function name string
#       * start is the 0-based inclusive start-line index of a top-level function body
#       * end is the 0-based inclusive end-line index of a top-level function body
#   - None signals codegraph unavailability; the caller must fall back to regex extraction
# [SPEC]

# [INFO]
# handler.function_spans(proj_dir, filepath) -> [(str, int, int)] | None
#   Pre-condition: handler is a LanguageHandler registered for lang_key in REGISTRY
#   Post-condition: When a codegraph backend indexes filepath under proj_dir, returns
#     a list of (name, start, end) identifying top-level functions with 0-based
#     inclusive line indices; otherwise returns None
# [INFO]

def function_spans_for_file(proj_dir: str, filepath: str, lang_key: str):
    """Return codegraph function spans for one file, or None to fall back.

    Delegates to the registered language handler's function_spans backend.
    Returns [(func_name, start_idx, end_idx)] (0-indexed, inclusive) when
    codegraph indexes the file, or None when the language is unregistered,
    codegraph does not support it, or the file is not in the index — in every
    such case the caller should fall back to the regex extractor.
    """
    handler = REGISTRY.get(lang_key)
    if handler is None:
        return None
    return handler.function_spans(proj_dir, filepath)
