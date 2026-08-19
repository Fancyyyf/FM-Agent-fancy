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
