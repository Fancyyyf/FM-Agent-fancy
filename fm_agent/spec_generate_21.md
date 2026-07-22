# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::CodeGraphExtractor::get_functions_by_file` (language: `python`).
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
def get_functions_by_file(self, lang_key: str, proj_dir: str = None) -> dict:
        """Return {abs_filepath: [(func_name, body_text), ...]} for all files.

        body_text is the raw source lines for that function, matching the format
        that extract_functions_from_file returns.

        proj_dir must be supplied so that the relative file paths stored by
        codegraph can be resolved to absolute paths for opening and for dict
        key lookup in run_extraction.
        """
        cg_langs = _CG_LANG.get(lang_key)
        if not cg_langs:
            return {}

        conn = sqlite3.connect(self._db)
        cur = conn.cursor()
        placeholders = ",".join("?" * len(cg_langs))
        cur.execute(
            f"""
            SELECT name, qualified_name, file_path, start_line, end_line
            FROM nodes
            WHERE kind IN ('function', 'method') AND language IN ({placeholders})
            ORDER BY file_path, start_line
            """,
            cg_langs,
        )
        rows = cur.fetchall()
        conn.close()

        by_file = defaultdict(list)
        for name, qualified_name, file_path, start_line, end_line in rows:
            ident = _extraction_ident(name, qualified_name)
            by_file[file_path].append((ident, int(start_line), int(end_line)))

        result = {}
        for file_path, funcs in by_file.items():
            abs_path = os.path.join(proj_dir, file_path) if proj_dir else file_path
            try:
                with open(abs_path, "r", errors="replace") as f:
                    all_lines = f.readlines()
            except OSError:
                continue

            ident_counts = {}
            file_funcs = []
            for ident, start_line, end_line in funcs:
                # ``ident`` is the class-qualified identifier ("LocalStorage::Flush",
                # or the bare name for a free function). Member functions in
                # different classes are already distinct here, so the class name —
                # not an opaque line-order suffix — is what tells them apart.
                # A suffix is still appended only when two functions share the exact
                # same qualified identifier (e.g. overloads: same class + same name,
                # different parameters), which would otherwise overwrite each other
                # ("LocalStorage::Flush", "LocalStorage::Flush_1"). funcs are
                # line-ordered (SQL ORDER BY start_line), so the suffix is
                # deterministic. run_extraction keeps the "::" in the flat filename.
                count = ident_counts.get(ident, 0)
                ident_counts[ident] = count + 1
                deduped = ident if count == 0 else f"{ident}_{count}"
                # codegraph uses 1-indexed lines, end_line is inclusive
                body_lines = all_lines[start_line - 1 : end_line]
                body = "".join(body_lines)
                if not body.endswith("\n"):
                    body += "\n"
                file_funcs.append((deduped, body))

            result[abs_path] = file_funcs

        return result
```

## Specs of this function's callers

### src::languages::c-py::batch_extract

# [SPEC]
# Unit: src/languages/c-py/batch_extract.py
#
# batch_extract(proj_dir) -> dict
#
# Pre-condition:
#   - proj_dir is a path to an existing directory containing C source files
#
# Post-condition:
#   - Returns a dictionary mapping absolute file paths to lists of
#     (function_name, function_body) tuples for every C function extracted
#     from the project using codegraph analysis
#   - Returns an empty dictionary {} when codegraph initialization fails
# [SPEC]

### src::languages::cpp-py::batch_extract

# [SPEC]
# Unit: src/languages/cpp-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a directory path that
#     contains C++ source files (.cpp, .cc, .cxx) and may have a codegraph
#     index (.codegraph/codegraph.db).
#
# Post-condition:
#   - Returns a dictionary where each key is an absolute file path (str) and
#     each value is a list of (function_name: str, body: str) tuples.
#   - Every key corresponds to a C++ source file under proj_dir for which
#     codegraph extracted at least one top-level function.
#   - Each function_name is the canonical name of a function defined in the
#     corresponding source file.
#   - Each body is the full source text of that function as returned by
#     codegraph.
#   - If codegraph is not available for proj_dir (CodeGraphExtractor.from_proj_dir
#     returns a falsy value), the returned dictionary is empty.
#   - The returned dictionary does not include entries for non-C++ files or for
#     files from which codegraph extracted zero functions.
# [SPEC]

### src::languages::go-py::batch_extract

# [SPEC]
# Unit: src/languages/go-py/batch_extract.py
#
# batch_extract(proj_dir) -> Dict[str, List[Tuple[str, str]]]
#
# Pre-condition:
#   - proj_dir is a non-empty string path to a project root containing Go source files
#
# Post-condition:
#   - Returns a dict whose keys are absolute file paths (strings) of Go source files
#     and whose values are lists of (func_name, body) tuples for all function
#     definitions extracted from each file
#   - func_name is a string containing the canonicalized function identifier; body is
#     a string containing the full source text of the function definition
#   - Returns an empty dict {} when no codegraph backend is available for Go
#   - Only .go source files within proj_dir are processed
# [SPEC]

### src::languages::java-py::batch_extract

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

### src::languages::javascript-py::batch_extract

# [SPEC]
# Unit: src/languages/javascript-py/batch_extract.py
#
# batch_extract(proj_dir)
#
# Pre-condition:
#   - proj_dir is a string path to a valid project root directory containing JavaScript
#     source files (.js, .jsx).
#
# Post-condition:
#   - If the codegraph backend is available, returns a dictionary mapping each absolute
#     file path (string) to a list of (func_name, func_body) tuples, where func_name is
#     a string and func_body is the source text of the function, for every JavaScript
#     function definition found across all project files.
#   - If the codegraph backend is unavailable, returns an empty dictionary.
#   - Each key in the returned dictionary is an absolute filesystem path; each value is
#     a non-empty list of tuples.
# [SPEC]

### src::languages::python-py::batch_extract

# [SPEC]
# Unit: src/languages/python-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a string path to a project root directory.
#
# Post-condition:
#   - Returns a dict where each key is an absolute file path (str) and each value is a list of (function_name: str, function_body: str) tuples.
#   - The returned keys correspond to Python source files (.py) discovered under the project directory.
#   - When the CodeGraph backend cannot index the project directory, returns an empty dict (no entries).
#   - Each tuple's function_name identifies a top-level function or method definition in the corresponding source file.
#   - Each tuple's function_body contains the full source text of the function, including its signature and body.
# [SPEC]

### src::languages::rust-py::batch_extract

# [SPEC]
# Unit: src/languages/rust-py/batch_extract.py
#
# batch_extract(proj_dir) -> dict
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a project directory
#
# Post-condition:
#   - Returns a dictionary where each key is an absolute filesystem path (str) to a Rust source
#     file located within or under the project directory
#   - Each value is a non-empty list of (str, str) tuples: the first element is a function name
#     declared in that file, and the second element is the complete source text of the function body
#   - A source file containing N detected functions produces N entries in its value list
#   - Returns an empty dictionary when no Rust codegraph backend is available for the given project
# [SPEC]

### src::languages::typescript-py::batch_extract

# [SPEC]
# Unit: src/languages/typescript.py
#
# batch_extract(proj_dir: str) -> dict[str, list[tuple[str, str]]]
#
# Pre-condition:
#   - proj_dir is a filesystem path to a project directory
#
# Post-condition:
#   - If codegraph is available: returns a dict whose keys are absolute file
#     paths to TypeScript source files within proj_dir, and whose values are
#     lists of (function_name, function_body) tuples for every top-level
#     function declared in the corresponding file.
#   - Each function_name is the identifier of the function declaration.
#   - Each function_body is the full source text of the function definition.
#   - If proj_dir contains no TypeScript files with top-level functions:
#     returns an empty dict.
#   - If codegraph is unavailable: returns an empty dict {}.
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::c-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(language_key, proj_dir) -> dict
#   Pre-condition: language_key is a valid language identifier; proj_dir is the
#     project root directory
#   Post-condition: Returns a dict mapping absolute file paths to lists of
#     (func_name, func_body) tuples for all functions in files of the given
#     language within the project

### According to src::languages::cpp-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(lang_key: str, proj_dir: str) -> dict[str, list[tuple[str, str]]]
#   Pre-condition: lang_key is a language identifier string recognized by the
#     extractor (e.g., "cpp"); proj_dir is the project root used during
#     initialization.
#   Post-condition: Returns a dictionary mapping absolute file paths (str) to
#     lists of (function_name: str, body: str) tuples, covering all top-level
#     functions in files matching lang_key under proj_dir. Returns an empty
#     dictionary if no matching functions are found.

### According to src::languages::go-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(lang_key, proj_dir) -> Dict[str, List[Tuple[str, str]]]
#   Pre-condition: lang_key is a language identifier string; proj_dir is the project root
#   Post-condition: Returns a dict mapping absolute file paths to lists of (func_name, body)
#     tuples for all function definitions in files of the given language

### According to src::languages::java-py::batch_extract

# cg.get_functions_by_file("java", proj_dir) -> dict
#   Pre-condition: cg is a valid CodeGraphExtractor instance; proj_dir is a valid
#     project directory path
#   Post-condition: Returns a dict mapping each absolute file path (str) to a list of
#     (function_name: str, function_body: str) tuples for all Java functions in the project

### According to src::languages::javascript-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(language, proj_dir) -> dict of str to list of (str, str)
#   Pre-condition: language is a valid language key string; proj_dir is a valid project
#     directory path.
#   Post-condition: Returns a dictionary mapping absolute file paths to lists of
#     (func_name, func_body) tuples for all function definitions found in source files
#     of the given language within the project directory.

### According to src::languages::python-py::batch_extract

# cg.get_functions_by_file(language: str, proj_dir: str) -> dict
#   Pre-condition: language is a valid language key string (e.g., "python").
#   Post-condition: Returns a dict mapping absolute file paths to lists of (function_name, function_body) tuples for all source files of the given language under proj_dir.

### According to src::languages::rust-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(lang, proj_dir) -> dict
#   Pre-condition: lang is a recognized language key string and proj_dir is the project root path
#   Post-condition: Returns a dictionary mapping each absolute source-file path (str) to a list of
#     (function_name, function_body) tuples for all source files of the given language

### According to src::languages::typescript-py::batch_extract

# CodeGraphExtractor.get_functions_by_file(language: str, proj_dir: str) -> dict[str, list[tuple[str, str]]]
#   Pre-condition: language is a supported language key; proj_dir is the indexed
#     project root
#   Post-condition: Returns a dict mapping absolute file paths to lists of
#     (function_name, function_body) tuples for all source files of the given
#     language found under proj_dir

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_21.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
