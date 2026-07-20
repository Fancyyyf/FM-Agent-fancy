# [SPEC]
# Unit: src/extract-py/_function_spans.py
#
# _function_spans(filepath, lang_key, proj_dir=None) -> ([(str, int, int)], [str])
#
# Pre-condition:
#   - filepath is a string path to an existing, readable source file
#   - lang_key is a string key present in LANG_CONFIG
#   - proj_dir is either None or a string path to a project directory
#
# Post-condition:
#   - Returns a tuple (spans, raw_lines) where:
#     * raw_lines is a list of strings whose length equals the number of lines in the source file,
#       each element containing the original line text with its trailing newline character preserved
#     * spans is a list of (name, start_idx, end_idx) tuples, one per top-level function found in the source file,
#       ordered by first appearance in the file
#     * start_idx and end_idx are 0-based line indices into raw_lines, satisfying 0 <= start_idx <= end_idx < len(raw_lines)
#     * name is the canonicalized, deduplicated function name: when N > 1 functions share the same canonicalized name,
#       the i-th occurrence is suffixed with _i (e.g., name, name_1, name_2, ...)
#   - When proj_dir is not None and a codegraph backend covers the file at filepath:
#     function boundaries are determined by language semantics from codegraph
#   - When proj_dir is None or no codegraph backend covers the file:
#     function boundaries are determined by language-specific regex extraction
#     (brace matching for brace-delimited languages, indentation detection for indent-delimited languages)
#   - All extraction backends produce results in the same (name, start_idx, end_idx) shape
#   - If the file at filepath cannot be opened or read, the I/O exception propagates to the caller
# [SPEC]

# [INFO]
# function_spans_for_file(proj_dir, filepath, lang_key) -> [(str, int, int)] | None
#   Pre-condition: proj_dir is a project directory path, filepath is a source file path, lang_key is a language identifier
#   Post-condition: Returns a list of (name, start_line, end_line) tuples with 0-based line indices for each
#     top-level function in the file when a codegraph backend indexes the file; returns None otherwise
# _extract_functions_brace(norm_lines: [str], lang_key: str, lang_cfg: dict) -> [(str, int, int)]
#   Pre-condition: norm_lines is a list of newline-stripped source lines for a brace-delimited language,
#     lang_key is the language identifier, lang_cfg is the corresponding LANG_CONFIG entry
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples with 0-based line indices for each
#     top-level function detected via brace-pair matching
# _extract_functions_indent(norm_lines: [str], lang_cfg: dict) -> [(str, int, int)]
#   Pre-condition: norm_lines is a list of newline-stripped source lines for an indent-delimited language,
#     lang_cfg is the corresponding LANG_CONFIG entry
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples with 0-based line indices for each
#     top-level function detected via indentation boundaries
# canonicalize(name: str) -> str
#   Pre-condition: name is a raw function name string extracted from source code
#   Post-condition: Returns a canonical form of the name suitable for deduplication, with syntactic
#     variations (template parameters, operator overload syntax) normalized to a common representation
# [INFO]

def _function_spans(filepath, lang_key, proj_dir=None):
    """Return ``(spans, raw_lines)`` for a source file.

    ``spans`` is a list of ``(deduped_name, start_idx, end_idx)`` line ranges,
    one per function, named exactly as run_extraction names the extracted files
    (duplicate names get ``_1``, ``_2``, ... suffixes). ``raw_lines`` are the
    file's original lines (newline characters preserved) so callers can rewrite
    the file by line index.

    Function boundaries come from codegraph via the language registry when
    ``proj_dir`` is given and codegraph indexes the file; otherwise they fall
    back to the regex extractor (_extract_functions_brace / _indent). Both
    backends yield the same (name, start_idx, end_idx) shape, so the dedup
    naming below is identical regardless of which one is used.
    """
    lang_cfg = LANG_CONFIG[lang_key]
    with open(filepath, "r", errors="replace") as f:
        raw_lines = f.readlines()
    # Extraction operates on newline-stripped lines; indices line up 1:1 with
    # raw_lines (readlines yields one entry per line).
    norm_lines = [l.rstrip("\n").rstrip("\r") for l in raw_lines]

    raw_funcs = None
    if proj_dir is not None:
        raw_funcs = function_spans_for_file(proj_dir, filepath, lang_key)
    if raw_funcs is None:
        if lang_cfg["body"] == "brace":
            raw_funcs = _extract_functions_brace(norm_lines, lang_key, lang_cfg)
        else:
            raw_funcs = _extract_functions_indent(norm_lines, lang_cfg)

    name_counts = {}
    spans = []
    for name, start, end in raw_funcs:
        cname = canonicalize(name)
        count = name_counts.get(cname, 0)
        name_counts[cname] = count + 1
        deduped = cname if count == 0 else f"{cname}_{count}"
        spans.append((deduped, start, end))
    return spans, raw_lines
