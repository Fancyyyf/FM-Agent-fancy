# [SPEC]
# Unit: src/languages/registry-py/batch_extract_all.py
#
# batch_extract_all(proj_dir: str) -> tuple
#
# Pre-condition:
#   - proj_dir is a string representing a path to an existing directory.
#   - REGISTRY is a non-empty dict mapping language key strings to LanguageHandler
#     objects, each exposing a batch_extract callable that accepts a single
#     directory-path argument.
#
# Post-condition:
#   - Returns a tuple (funcs, langs) where:
#       funcs is a dict mapping normalized absolute file paths (str) to lists
#         of (func_name: str, func_body: str) tuples.
#       langs is a set of language key strings.
#   - Every registered handler's batch_extract is invoked exactly once with
#     proj_dir as its sole argument.
#   - For each handler whose batch_extract returns a truthy dict result: every
#     key-value pair in that dict is included in funcs (with later handlers
#     overwriting earlier entries for duplicate keys), and the handler's language
#     key is included in langs.
#   - A handler whose batch_extract returns a falsy result contributes nothing to
#     funcs or langs.
#   - If no handler returns a truthy result: funcs is an empty dict and langs is
#     an empty set.
#   - If any handler's batch_extract raises an exception, that exception
#     propagates uncaught to the caller; funcs and langs are not returned.
# [SPEC]

# [INFO]
# handler.batch_extract(proj_dir: str) -> dict | None
#   Pre-condition: proj_dir is a valid project directory containing source files
#     for the handler's language.
#   Post-condition: Returns a dict mapping absolute file paths to lists of
#     (func_name, func_body) tuples extracted from source files in the project,
#     or a falsy value when the handler's backend is unavailable or no functions
#     are found.
# [INFO]

def batch_extract_all(proj_dir: str) -> tuple:
    """Call batch_extract for every registered language and merge results.

    Returns (funcs, langs) where funcs is {abs_filepath: [(func_name, body)]}
    and langs is the set of language keys that returned data.
    """
    funcs = {}
    langs = set()
    for lang, handler in REGISTRY.items():
        result = handler.batch_extract(proj_dir)
        if result:
            funcs.update(result)
            langs.add(lang)
    return funcs, langs
