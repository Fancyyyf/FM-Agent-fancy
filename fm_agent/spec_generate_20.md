# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::CodeGraphExtractor::get_function_spans` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _extraction_ident.

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
def get_function_spans(self, lang_key: str, abs_filepath: str):
        """Return ``[(name, start_idx, end_idx), ...]`` for a single file, or None.

        Line indices are 0-indexed and inclusive, matching the convention the
        regex extractor (_extract_functions_brace / _extract_functions_indent)
        uses, so callers can rewrite the file by line index. Functions are
        ordered by their starting line.

        Returns None when codegraph does not support ``lang_key`` or when the
        file is not present in the index (e.g. it was never indexed) — the
        caller then falls back to the regex extractor. An indexed file that
        genuinely contains no functions also yields None, which is harmless:
        the regex fallback finds none either.
        """
        cg_langs = _CG_LANG.get(lang_key)
        if not cg_langs:
            return None

        # codegraph stores file paths relative to the project root, which is the
        # parent of the .codegraph/ directory holding the database.
        root = os.path.dirname(os.path.dirname(os.path.abspath(self._db)))
        rel = os.path.relpath(os.path.abspath(abs_filepath), root)

        conn = sqlite3.connect(self._db)
        cur = conn.cursor()
        placeholders = ",".join("?" * len(cg_langs))
        cur.execute(
            f"""
            SELECT name, qualified_name, start_line, end_line
            FROM nodes
            WHERE kind IN ('function', 'method') AND language IN ({placeholders})
              AND file_path = ?
            ORDER BY start_line
            """,
            (*cg_langs, rel),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return None
        # codegraph uses 1-indexed lines with an inclusive end_line. Return the
        # class-qualified identifier so the caller's dedup + name matching (trim)
        # stays consistent with the extracted files and the call graph.
        return [
            (_extraction_ident(name, qualified_name), int(start) - 1, int(end) - 1)
            for name, qualified_name, start, end in rows
        ]
```

## Specs of this function's callers

### src::languages::c-py::function_spans

# [SPEC]
# Unit: src/languages/c-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory
#   - filepath is a path to a C source file with a ".c" extension
#
# Post-condition:
#   - Returns None when a codegraph instance cannot be initialized from proj_dir
#   - Otherwise returns a list of (function_name, start_idx, end_idx) tuples for every
#     function defined in the C source file at filepath, where start_idx and end_idx
#     are 0-indexed inclusive line numbers
# [SPEC]

### src::languages::cpp-py::function_spans

# [SPEC]
# Unit: src/languages/cpp-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list | None
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory on the filesystem
#   - filepath is a string identifying a C++ source file within the project
#
# Post-condition:
#   - Returns None when a codegraph backend is unavailable or does not index the file, signaling the caller to fall back to regex-based extraction
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples, each identifying one function in the file by its name and the range of source lines it occupies
#   - In every returned tuple, start_idx and end_idx are 0-indexed inclusive line indices
#   - The returned list covers every function that the codegraph backend detects in the file
# [SPEC]

### src::languages::go-py::function_spans

# [SPEC]
# Unit: src/languages/go-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list | None
#
# Pre-condition:
#   - proj_dir is a non-empty string referencing a project directory.
#   - filepath is a string identifying a Go source file within that project.
#
# Post-condition:
#   - Returns a list of (function_name, start_line, end_line) tuples for every
#     top-level function definition found in the file at filepath.
#   - start_line and end_line are 0-indexed and inclusive.
#   - The returned list is ordered by function occurrence within the file.
#   - Returns None when the codegraph backend is unavailable or does not index
#     the file at filepath.
# [SPEC]

### src::languages::java-py::function_spans

# [SPEC]
# Unit: src/languages/java-py/function_spans.py
#
# function_spans(proj_dir, filepath)
#
# Pre-condition:
#   - proj_dir is a string path to a valid project root directory containing Java source files.
#   - filepath is a string path to a Java source file (.java) located within proj_dir.
#
# Post-condition:
#   - If the codegraph backend is available and indexes the given Java file, returns a list of
#     (name, start_idx, end_idx) tuples, one per function definition found in the file, ordered
#     by appearance in the source. Each tuple contains the function name as a string and
#     0-indexed inclusive line indices delimiting the function body.
#   - If the codegraph backend is unavailable or does not index the file, returns None,
#     signalling that the caller must fall back to regex-based extraction.
# [SPEC]

### src::languages::javascript-py::function_spans

# [SPEC]
# Unit: src/languages/javascript-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple] | None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory.
#   - filepath is a path to a JavaScript source file within the project.
#
# Post-condition:
#   - Returns None when the codegraph backend is unavailable for the project, or when the
#     backend exists but does not index the given file.
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function
#     defined in the file.
#   - start_idx and end_idx are 0-indexed inclusive line numbers.
#   - The list is ordered by appearance (ascending start_idx).
#   - The list is empty when no functions are defined in the file.
# [SPEC]

### src::languages::python-py::function_spans

# [SPEC]
# Unit: src/languages/python-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory
#   - filepath is a relative or absolute path to a Python source file
#
# Post-condition:
#   - If a codegraph backend is available and indexes the project at proj_dir,
#     returns a list of (name, start_idx, end_idx) tuples, one per function
#     defined in the Python source file at filepath, where start_idx and
#     end_idx are 0-indexed inclusive line numbers delimiting each function body.
#   - Returns None when the codegraph backend cannot be initialized for the
#     project or does not index the given filepath, signaling the caller to
#     fall back to regex-based function extraction for this file.
# [SPEC]

### src::languages::rust-py::function_spans

# [SPEC]
# Unit: src/languages/rust.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a filesystem path to a project directory
#   - filepath is a path to a single Rust source file within the project
#
# Post-condition:
#   - If codegraph is available and indexes filepath: returns a list of
#     (function_name, start_line, end_line) tuples, one per top-level function
#     declared in the file. Each start_line and end_line is a 0-indexed
#     inclusive line number bounding the function's source span.
#   - If filepath contains no top-level function declarations: returns an
#     empty list.
#   - If codegraph is unavailable or does not index filepath: returns None.
#     A None return signals the caller to fall back to regex-based extraction.
# [SPEC]

### src::languages::typescript-py::function_spans

# [SPEC]
# Unit: src/languages/typescript-py/function_spans.py
#
# function_spans(proj_dir, filepath) -> list[(name, start_idx, end_idx)] | None
#
# Pre-condition:
#   - proj_dir is a path to a project root directory
#   - filepath is a path to a single TypeScript source file residing under proj_dir
#
# Post-condition:
#   - When a codegraph backend initializes successfully from proj_dir AND the backend
#     indexes the TypeScript file at filepath, returns a non‑empty list of
#     (name, start_idx, end_idx) tuples covering every function defined in the file,
#     where name is the function's declared name as a string, and start_idx and end_idx
#     are 0‑indexed inclusive line positions delimiting the function body
#   - When no codegraph backend is available, or the backend exists but does not index
#     the file at filepath, returns None
#   - The order of tuples in the returned list corresponds to the definition order of
#     functions in the source file
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::cpp-py::function_spans

# cg.get_function_spans(lang_key: str, filepath: str) where lang_key="cpp"
#   Pre-condition: cg is a valid CodeGraphExtractor instance bound to the project
#   Post-condition: Returns a list of (name, start, end) tuples for functions found in the given file, or None if the file is not indexed

### According to src::languages::java-py::function_spans

# CodeGraphExtractor.get_function_spans(language, filepath) -> list of (str, int, int) or None
#   Pre-condition: language is a valid language key string; filepath is a file path string
#     pointing to a source file.
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for each function
#     definition found in the file, where indices are 0-indexed inclusive positions, or None
#     if the file is not indexed by the codegraph backend.

### According to src::languages::javascript-py::function_spans

# cg.get_function_spans(language_key: str, filepath: str) -> list[tuple] | None
#   Pre-condition: cg is a successfully constructed CodeGraphExtractor; language_key is a
#     recognized language identifier; filepath is a source file path within the project.
#   Post-condition: Returns a list of (name, start_line, end_line) tuples for each function
#     in the file with 0-indexed inclusive line numbers, or None when the file is not
#     indexed by the backend.

### According to src::languages::python-py::function_spans

# CodeGraphExtractor.get_function_spans(language: str, filepath: str) -> list[tuple[str, int, int]] | None
#   Pre-condition: language is a recognized language key (e.g., "python")
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for
#     each function defined in the source file, with 0-indexed inclusive line
#     indices; returns None if the file is not indexed by this extractor.

### According to src::languages::rust-py::function_spans

# CodeGraphExtractor.get_function_spans(language: str, filepath: str) -> list[tuple[str, int, int]]
#   Pre-condition: language is a supported language key; filepath is a path to a
#     source file within the indexed project
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for each
#     top-level function in filepath, with 0-indexed inclusive line indices

### According to src::languages::typescript-py::function_spans

# CodeGraphExtractor.get_function_spans(language, filepath) -> list[(name, start_idx, end_idx)] | None
#   Pre-condition: language is a supported language key; filepath is a path to a source
#     file of the given language within the project
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for every
#     function defined in the file with 0‑indexed inclusive line indices; returns None
#     if the backend does not index the given file

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_20.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
