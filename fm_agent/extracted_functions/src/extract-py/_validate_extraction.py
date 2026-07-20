# [SPEC]
# Unit: src/extract.py
#
# _validate_extraction(extracted_dir, registry_langs=None) -> [(filepath, function_count)]
#
# Pre-condition:
#   - extracted_dir is a path to an existing directory whose files are expected to each
#     contain exactly one extracted function body
#   - registry_langs, if not None, is an iterable of language key strings identifying
#     languages whose extracted files were produced by codegraph backends and are
#     guaranteed to contain exactly one function body by construction
#
# Post-condition:
#   - Returns a list of (filepath, function_count) tuples — one entry per file under
#     extracted_dir (at any depth) that fails the single-function-body invariant
#   - A file is eligible for validation only when its extension maps to a recognized
#     language key AND, when registry_langs is not None, that language key is absent
#     from registry_langs; all other files are silently excluded from the result
#   - For each eligible file, the regex-based function extractor is applied; the file
#     is included in the result with its function count when that count is not exactly 1
#   - Returns an empty list when every eligible file contains exactly one extracted
#     function body
# [SPEC]

# [INFO]
# extract_functions_from_file(filepath, lang_key) -> [(function_name, source_text)]
#   Pre-condition: filepath is a valid path to a source file; lang_key is a recognized
#     language key with a configured regex-based extraction strategy
#   Post-condition: Returns a list of (function_name, source_text) pairs for every
#     function body detected in the file via regex-based extraction; returns an empty
#     list when no function bodies are found
# [INFO]

def _validate_extraction(extracted_dir, registry_langs=None):
    """Re-parse every extracted file and verify each contains exactly one function.

    Files for languages that returned data from their REGISTRY backend are skipped:
    those backends write exactly one function body per file by construction, so
    regex re-parsing adds no safety and produces false negatives for forms the
    regex cannot recognise (async def, class methods, arrow functions).

    Returns a list of (file_path, function_count) for files that fail validation.
    """
    failures = []
    for root, _, files in os.walk(extracted_dir):
        for fname in files:
            ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
            lang_key = EXT_TO_LANG.get(ext)
            if not lang_key:
                continue
            if registry_langs and lang_key in registry_langs:
                continue
            fpath = os.path.join(root, fname)
            funcs = extract_functions_from_file(fpath, lang_key)
            if len(funcs) != 1:
                failures.append((fpath, len(funcs)))
    return failures
