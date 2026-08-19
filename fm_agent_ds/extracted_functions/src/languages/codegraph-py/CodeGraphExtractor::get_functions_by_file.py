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
