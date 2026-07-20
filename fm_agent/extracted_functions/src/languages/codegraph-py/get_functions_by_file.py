# [SPEC]
# Unit: src/languages/codegraph-py/get_functions_by_file.py
#
# get_functions_by_file(self, lang_key: str, proj_dir: str = None) -> dict
#
# Pre-condition:
#   - self is a valid CodeGraphExtractor instance
#   - lang_key is a string identifying a language
#   - proj_dir, when provided, is a filesystem path to a project root directory
#
# Post-condition:
#   - Returns an empty dict {} when the codegraph backend does not support the
#     language identified by lang_key
#   - Otherwise returns a dict mapping absolute file paths (str) to lists of
#     (func_name: str, body: str) tuples for every function and method
#     definition indexed across all source files of the given language in the
#     project
#   - func_name is the canonicalized bare function identifier: namespace and
#     class qualifiers removed, template parameters stripped, with a
#     deterministic numeric suffix (_1, _2, ...) appended when multiple
#     functions in the same source file share the same canonicalized bare name;
#     the first occurrence receives no suffix
#   - body is the full source text of the function definition as read from the
#     original source file, including the signature and body, with a trailing
#     newline appended when the original source does not end with one
#   - Within each file's value list, tuples are ordered by ascending start line
#     (definition order in the source file)
#   - Source files that are indexed but cannot be read from the filesystem are
#     silently excluded from the returned dict
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
            SELECT name, file_path, start_line, end_line
            FROM nodes
            WHERE kind IN ('function', 'method') AND language IN ({placeholders})
            ORDER BY file_path, start_line
            """,
            cg_langs,
        )
        rows = cur.fetchall()
        conn.close()

        by_file = defaultdict(list)
        for name, file_path, start_line, end_line in rows:
            by_file[file_path].append((name, int(start_line), int(end_line)))

        result = {}
        for file_path, funcs in by_file.items():
            abs_path = os.path.join(proj_dir, file_path) if proj_dir else file_path
            try:
                with open(abs_path, "r", errors="replace") as f:
                    all_lines = f.readlines()
            except OSError:
                continue

            name_counts = {}
            file_funcs = []
            for name, start_line, end_line in funcs:
                # Disambiguate functions sharing a name within one file
                # (LocalStorage::Flush vs RemoteCache::Flush, overloads, a method
                # and a same-named free function, ...). codegraph stores them all
                # under the same bare name; run_extraction writes each to
                # "<name>.<ext>", so without a suffix the later definition
                # silently overwrites the earlier one — dropping functions from
                # both extraction and the call graph. Mirror the regex path's
                # dedup ("Flush", "Flush_1", ...). funcs are line-ordered (SQL
                # ORDER BY start_line), so suffix assignment is deterministic.
                bare = _bare_function_name(name)
                cname = canonicalize(bare)
                count = name_counts.get(cname, 0)
                name_counts[cname] = count + 1
                deduped = cname if count == 0 else f"{cname}_{count}"
                # codegraph uses 1-indexed lines, end_line is inclusive
                body_lines = all_lines[start_line - 1 : end_line]
                body = "".join(body_lines)
                if not body.endswith("\n"):
                    body += "\n"
                file_funcs.append((deduped, body))

            result[abs_path] = file_funcs

        return result
