#!/usr/bin/env python3
r"""Probe for bug src--languages--codegraph-py--_bare_function_name.

Spec claim: decoration stripping — appended signature/parameter text must be
removed from operator-overload names, so 'operator new(int)' must yield
'operator new' (memory-management operator overload, parameter text stripped).

Actual behavior: src/languages/codegraph.py::_bare_function_name uses
re.fullmatch on `rest`, so 'new(int)' does not match r'new(?:\s*\[\s*\])?';
the operator-symbol loop rejects 'n'; execution falls through to
re.match(r'^(\w+)') and returns just 'operator'.

FM-Agent self-validation guard: this probe does NOT start any FM-Agent
workflow. It only instantiates the public CodeGraphExtractor class over a
fresh fixture SQLite database inside a probe-owned temporary directory and
calls its public get_function_spans() method, which routes every node name
through _bare_function_name via _extraction_ident.
"""
import os
import sqlite3
import sys
import tempfile
import traceback

# Repo root = two levels up from fm_agent/bug_validation/<this file>.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def main():
    from src.languages.codegraph import CodeGraphExtractor

    # Fresh probe-owned workspace; nothing touches the active repo.
    tmp = tempfile.mkdtemp(prefix="fm_probe_bare_fn_name_")
    proj = os.path.join(tmp, "proj")
    cg_dir = os.path.join(proj, ".codegraph")
    os.makedirs(cg_dir)

    # Fixture sources: tree-sitter/codegraph occasionally stores the whole
    # signature in the name column for macro-generated C++ declarations, so
    # 'operator new(int)' is a realistic node name.
    sample_free = os.path.join(proj, "sample_free.cpp")
    with open(sample_free, "w") as f:
        f.write("void* operator new(int size) { return nullptr; }\n")
    sample_memb = os.path.join(proj, "sample_memb.cpp")
    with open(sample_memb, "w") as f:
        f.write("struct Vec {\n")
        f.write("  static void* operator new(int size);\n")
        f.write("};\n")

    # Fixture codegraph SQLite DB with the `nodes` table shape codegraph uses.
    db_path = os.path.join(cg_dir, "codegraph.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE nodes ("
            " id INTEGER PRIMARY KEY,"
            " name TEXT,"
            " qualified_name TEXT,"
            " file_path TEXT,"
            " start_line INTEGER,"
            " end_line INTEGER,"
            " kind TEXT,"
            " language TEXT"
            ")"
        )
        rows = [
            # (name, qualified_name, file_path, start, end, kind, language)
            ("operator new(int)", "operator new(int)", "sample_free.cpp",
             1, 1, "function", "cpp"),
            ("operator new(int)", "Vec::operator new(int)", "sample_memb.cpp",
             2, 2, "method", "cpp"),
        ]
        conn.executemany(
            "INSERT INTO nodes (name, qualified_name, file_path, start_line,"
            " end_line, kind, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    # Public API path: from_proj_dir() locates .codegraph/codegraph.db, and
    # get_function_spans() maps each node through _extraction_ident ->
    # canonicalize(_bare_function_name(component)).
    ext = CodeGraphExtractor.from_proj_dir(proj)
    if ext is None:
        print("ERROR: CodeGraphExtractor.from_proj_dir returned None")
        return 1

    spans_free = ext.get_function_spans("cpp", sample_free)
    spans_memb = ext.get_function_spans("cpp", sample_memb)
    if not spans_free or not spans_memb:
        print(f"ERROR: fixture produced no spans: free={spans_free!r}, "
              f"memb={spans_memb!r}")
        return 1

    actual_free = spans_free[0][0]   # bare ident for 'operator new(int)'
    actual_memb = spans_memb[0][0]   # qualified ident 'Vec::<bare>'

    expected_free = "operator new"        # spec: parameter text '(int)' stripped
    expected_memb = "Vec::operator new"   # spec: scope kept, signature stripped

    detail = (f"free: actual={actual_free!r} expected={expected_free!r} | "
              f"qualified: actual={actual_memb!r} expected={expected_memb!r}")

    if actual_free != expected_free or actual_memb != expected_memb:
        print(f"CONFIRMED — {detail}")
        return 0
    print(f"NOT CONFIRMED — actual matched expected — {detail}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        traceback.print_exc()
        print(f"ERROR: {exc}")
        sys.exit(1)
