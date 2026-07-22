# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::_extraction_ident` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _bare_function_name, _qualified_parts, canonicalize.

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
def _extraction_ident(name: str, qualified_name: str) -> str:
    """Return the class-qualified, filesystem-safe identifier for a function.

    Each component is first stripped of any tree-sitter decoration by
    :func:`_bare_function_name` (codegraph occasionally stores a whole signature
    or template body in the name column — see issue #82, which would otherwise
    blow past the filesystem's filename limit), then passed through
    :func:`canonicalize` (so a class-scoped operator like ``Store::operator/``
    stays path/FQN-safe), then joined with ``::``. This single string is used both
    as a function's FQN tail and — with ``::`` turned into path separators — as its
    extracted-file location, so the call edges (via :func:`_node_fqn_map`) and the
    extracted files (via ``run_extraction`` + ``_file_to_fqn``) always agree.
    Examples: ``main`` -> ``"main"``; ``LocalStorage::Flush`` ->
    ``"LocalStorage::Flush"``.
    """
    return "::".join(
        canonicalize(_bare_function_name(p))
        for p in _qualified_parts(name, qualified_name)
    )
```

## Specs of this function's callers

### src::languages::codegraph-py::CodeGraphExtractor::get_function_spans

# [SPEC]
# Unit: src/languages/codegraph.py
#
# CodeGraphExtractor.get_function_spans(self, lang_key: str, abs_filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - self is a CodeGraphExtractor instance initialized with a valid codegraph SQLite database path
#   - lang_key is a non-empty string identifying a programming language
#   - abs_filepath is an absolute filesystem path to a source file residing within the project root
#
# Post-condition:
#   - Returns None when lang_key does not map to any language identifier recognized by the codegraph backend, signalling the caller to fall back to regex-based function extraction
#   - Returns None when the database contains no rows for the given file — this covers the file not being indexed, the file containing no function or method definitions, and the file path not resolving relative to the project root
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples covering every function and method definition that the codegraph backend detects in the file
#   - name is a class-qualified identifier string suitable for use as both a function FQN tail and a filesystem path component
#   - start_idx and end_idx are 0-indexed inclusive line numbers delimiting each function's source span, converted from the backend's 1-indexed representation
#   - The list is ordered by ascending start_idx, matching the definition order of functions in the source file
# [SPEC]

### src::languages::codegraph-py::CodeGraphExtractor::get_functions_by_file

# [SPEC]
# Unit: src/languages/codegraph.py
#
# CodeGraphExtractor.get_functions_by_file(lang_key: str, proj_dir: str = None) -> dict
#
# Pre-condition:
#   - lang_key is a string
#   - proj_dir is a string path to a directory, or None
#   - The receiver has an initialized codegraph database accessible for reading
#
# Post-condition:
#   - Returns a dict whose keys are absolute filesystem paths (str) and whose
#     values are lists of (str, str) tuples
#   - Each tuple consists of a function identifier and the full source text of
#     the corresponding function body
#   - Each function body ends with a newline character ("\n")
#   - For a given file, tuples are ordered by ascending line number of the
#     function definition within the source file
#   - Function identifiers are class-qualified; when multiple functions in the
#     same file share the same identifier, the first occurrence retains the
#     bare name and every subsequent occurrence appends a numeric suffix
#     starting from 1
#   - When lang_key is not a recognized language identifier, the returned dict
#     is empty
#   - Source files that cannot be opened for reading are omitted from the
#     result; no error is raised
#   - When proj_dir is provided, file paths stored in the database are resolved
#     relative to proj_dir to produce absolute keys
# [SPEC]

### src::languages::codegraph-py::_node_fqn_map

# [SPEC]
# Unit: src/languages/codegraph-py/_node_fqn_map.py
#
# _node_fqn_map(cur, cg_langs) -> dict
#
# Pre-condition:
#   - cur is a database cursor connected to a codegraph database containing a
#     nodes table with columns id, name, file_path, start_line, kind, and
#     language
#   - cg_langs is a non-empty sequence of language key strings
#
# Post-condition:
#   - Returns a dict mapping each node's id to its fully-qualified function
#     name (FQN)
#   - The mapping includes exactly the rows from the nodes table whose kind
#     is either 'function' or 'method' and whose language is one of the given
#     cg_langs values, ordered by (file_path ASC, start_line ASC)
#   - Each FQN is derived from the node's file_path and a canonicalized,
#     deduplicated function name in the canonical convention where path
#     components are joined by "::" and the source file extension in the
#     parent directory component is replaced by a hyphen
#   - Function name canonicalization strips angle-bracket template parameters
#     and normalizes operator-overload names to safe identifier forms
#   - When N > 1 nodes share the same file_path and canonicalized name, the
#     first such node in the result ordering receives the canonicalized name
#     without a suffix, and each subsequent node (k-th, 1-indexed) receives
#     the canonicalized name suffixed with _k
#   - Returns an empty dict when the query matches no rows
#   - The deduplication rule and ordering correspond to those used by
#     get_functions_by_file, ensuring that the FQN assigned to a node here
#     matches the FQN the extracted function file receives for the same node
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::codegraph-py::CodeGraphExtractor::get_function_spans

# _extraction_ident(name: str, qualified_name: str) -> str
#   Pre-condition: name and qualified_name are non-empty strings from a codegraph node representing a function or method definition
#   Post-condition: Returns a class-qualified filesystem-safe identifier string. When qualified_name contains a non-empty scope prefix and ends with name, the returned string includes scope components joined with "::" before the bare function name. When qualified_name is empty or its tail does not match name, the returned string is the bare function name with any tree-sitter signature decorations stripped. Every component in the returned string is canonicalized so the identifier can serve as both a function FQN tail and a filesystem path component.

### According to src::languages::codegraph-py::CodeGraphExtractor::get_functions_by_file

# _extraction_ident(name: str, qualified_name: str) -> str
#   Pre-condition:
#     - name and qualified_name are strings obtained from the codegraph database
#   Post-condition:
#     - Returns a filesystem-safe string composed of the scope components from
#       qualified_name followed by the bare function name, joined with "::"
#     - The result is deterministic for a given (name, qualified_name) pair

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_73.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
