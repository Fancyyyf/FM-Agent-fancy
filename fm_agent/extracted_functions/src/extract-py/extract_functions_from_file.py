# [SPEC]
# Unit: src/extract.py
#
# extract_functions_from_file(filepath, lang_key) -> [(function_name, source_text)]
#
# Pre-condition:
#   - filepath is a path to an existing file that can be opened for reading
#   - lang_key is a key present in LANG_CONFIG
#
# Post-condition:
#   - Returns a list of (function_name, source_text) tuples
#   - When the language configuration for lang_key specifies body type
#     "brace" or "indent", the list contains one entry per function body
#     whose boundaries are determined by the structural rules of that
#     body type (brace-matching for "brace", indentation depth for
#     "indent")
#   - When the language configuration specifies a body type that is
#     neither "brace" nor "indent", returns an empty list
#   - Each source_text consists of the exact contiguous source lines of
#     the detected function body (from the line where the function
#     definition begins through the line where its body ends), with
#     line endings normalized to '\n' and with a trailing '\n' appended
#   - Each function_name is derived from the raw function name by
#     stripping angle-bracket template parameters and normalizing
#     operator overload names to safe identifier forms
#   - When multiple extracted functions canonicalize to the same name,
#     the first occurrence in the file keeps the canonicalized name
#     without a suffix, and each subsequent occurrence appends _N where
#     N equals the count of previous occurrences of that canonicalized
#     name (1, 2, ...) in order of appearance
#   - Returns an empty list when no function bodies are detected in the
#     file under a brace or indent body type
#   - If opening the file at filepath fails, the corresponding I/O
#     exception propagates to the caller
#   - If lang_key is absent from LANG_CONFIG, raises KeyError
# [SPEC]

# [INFO]
# _extract_functions_brace(lines, lang_key, lang_cfg) -> [(raw_name, start, end)]
#   Pre-condition: lines is a list of source lines with line endings stripped;
#     lang_key is a recognized language key; lang_cfg is the LANG_CONFIG
#     entry for that language with body type "brace"
#   Post-condition: Returns a list of (raw_name, start_line, end_line)
#     tuples for every span of lines between matching open/close brace
#     pairs that begins with a function-definition declarator, using
#     language-specific keyword and syntax rules to identify function
#     definitions; start and end are zero-based line indices into lines
# [SPLIT]
# _extract_functions_indent(lines, lang_cfg) -> [(raw_name, start, end)]
#   Pre-condition: lines is a list of source lines with line endings
#     stripped; lang_cfg is the LANG_CONFIG entry with body type
#     "indent"
#   Post-condition: Returns a list of (raw_name, start_line, end_line)
#     tuples for every top-level indented block whose header line matches
#     the language's function-definition pattern; a block spans from the
#     header line through the last consecutive line whose indentation
#     level is strictly greater than or equal to the block's base
#     indentation; start and end are zero-based line indices into lines
# [SPLIT]
# canonicalize(name) -> str
#   Pre-condition: name is a raw function name string extracted from
#     source code
#   Post-condition: Returns a string where angle-bracket template
#     parameter lists are removed and operator overload names are
#     normalized to safe identifier forms suitable for use as filenames
#     and FQN components
# [INFO]

def extract_functions_from_file(filepath, lang_key):
    """Extract all functions from a single source file.

    Returns a list of (function_name, source_text) tuples.
    """
    lang_cfg = LANG_CONFIG[lang_key]

    with open(filepath, 'r', errors='replace') as f:
        lines = f.readlines()

    # Normalize line endings
    lines = [l.rstrip('\n').rstrip('\r') for l in lines]

    if lang_cfg["body"] == "brace":
        raw_funcs = _extract_functions_brace(lines, lang_key, lang_cfg)
    elif lang_cfg["body"] == "indent":
        raw_funcs = _extract_functions_indent(lines, lang_cfg)
    else:
        # Semantic-only languages (currently Erlang) are extracted by their
        # registered backend and have no reliable file-local fallback.
        return []

    # Deduplicate names (applied after canonicalize so operator overloads
    # produce safe filenames and FQN components).
    name_counts = {}
    results = []
    for name, start, end in raw_funcs:
        cname = canonicalize(name)
        count = name_counts.get(cname, 0)
        name_counts[cname] = count + 1
        if count > 0:
            deduped = f"{cname}_{count}"
        else:
            deduped = cname
        source = '\n'.join(lines[start:end + 1]) + '\n'
        results.append((deduped, source))

    return results
