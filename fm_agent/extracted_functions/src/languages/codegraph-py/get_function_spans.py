# [SPEC]
# Unit: src/languages/codegraph-py/get_function_spans.py
#
# get_function_spans(self, lang_key: str, abs_filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - self is a valid CodeGraphExtractor instance
#   - lang_key is a string identifying a language
#   - abs_filepath is an absolute filesystem path to a source file
#
# Post-condition:
#   - Returns None when the codegraph backend does not support the language
#     identified by lang_key, or when the file at abs_filepath is not present
#     in the codegraph index, or when the file is indexed but contains no
#     function or method definitions
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per
#     function or method definition that the codegraph backend has indexed in
#     the file
#   - name is a string containing the bare function identifier: namespace and
#     class qualifiers removed, template parameters stripped, canonicalized
#     according to the project's name-normalization rules
#   - start_idx and end_idx are 0-indexed inclusive integers delimiting the
#     source lines occupied by the function body
#   - Tuples in the returned list are ordered by ascending start_idx,
#     corresponding to the definition order of functions in the source file
# [SPEC]

# [INFO]
# (no callees)
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
            SELECT name, start_line, end_line
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
        # codegraph uses 1-indexed lines with an inclusive end_line.
        return [(canonicalize(_bare_function_name(name)), int(start) - 1, int(end) - 1) for name, start, end in rows]
