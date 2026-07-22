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

# [INFO]
# _extraction_ident(name: str, qualified_name: str) -> str
#   Pre-condition: name and qualified_name are strings (qualified_name may be empty) obtained from the codegraph database for a single function or method node
#   Post-condition: Returns a class-qualified filesystem-safe identifier string. When qualified_name contains a non-empty scope prefix and ends with name, the returned string includes scope components joined with "::" before the bare function name. When qualified_name is empty or its tail does not match name, the returned string is the bare function name with any tree-sitter signature decorations stripped. Every component in the returned string is canonicalized so the identifier can serve as both a function FQN tail and a filesystem path component.
# [INFO]

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
