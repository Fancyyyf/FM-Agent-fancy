"""Probe for bug: src--languages--codegraph-py--CodeGraphExtractor::get_functions_by_file

Spec claim: each body_text is the function's exact source text — the slice of
the file's lines covering precisely the indexed span, VERBATIM, in file order.

Trigger: a source file WITHOUT a trailing newline where the indexed function's
end_line equals the file's last line. readlines() then yields a final line with
no '\n', and the code unconditionally appends '\n'
(`if not body.endswith("\n"): body += "\n"`), producing a body containing a
character that does not exist in the original file.

FM-Agent self-validation guard: this probe does NOT start any FM-Agent workflow
(no run_pipeline / main.py / CLI / OpenCode). It loads only the smallest
relevant unit (CodeGraphExtractor) and feeds it a mocked codegraph SQLite index
plus fixture files, all confined to a fresh temporary directory.
"""

import os
import shutil
import sqlite3
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.codegraph import CodeGraphExtractor
except Exception as e:
    print(f"ERROR: failed to import src.languages.codegraph: {e}")
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="cg_probe_get_functions_by_file_")

try:
    # ---- Fixture project (owned by the probe, inside the temp dir) ----
    src_dir = os.path.join(tmp, "proj")
    os.makedirs(src_dir)

    # Source file WITHOUT a trailing newline; the function spans lines 1-2,
    # and end_line (2) is the file's last line.
    func_src = "def foo():\n    return 1"  # note: no trailing '\n'
    src_path = os.path.join(src_dir, "fixture.py")
    with open(src_path, "w") as f:
        f.write(func_src)

    # ---- Mocked codegraph index: proj/.codegraph/codegraph.db ----
    cg_dir = os.path.join(src_dir, ".codegraph")
    os.makedirs(cg_dir)
    db_path = os.path.join(cg_dir, "codegraph.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qualified_name TEXT,
            file_path TEXT,
            start_line INTEGER,
            end_line INTEGER,
            kind TEXT,
            language TEXT
        )
        """
    )
    # codegraph stores project-relative file paths; 1-indexed, end_line inclusive.
    conn.execute(
        "INSERT INTO nodes (id, name, qualified_name, file_path, start_line, end_line, kind, language)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "foo", "foo", "fixture.py", 1, 2, "function", "python"),
    )
    conn.commit()
    conn.close()

    # ---- Exercise the unit through its public factory ----
    extractor = CodeGraphExtractor.from_proj_dir(src_dir)
    if extractor is None:
        print("ERROR: CodeGraphExtractor.from_proj_dir returned None (mock db not found)")
        sys.exit(1)

    result = extractor.get_functions_by_file("python", proj_dir=src_dir)

    if src_path not in result or not result[src_path]:
        print("ERROR: expected one extracted function for fixture.py, got: %r" % (result,))
        sys.exit(1)

    ident, body_actual = result[src_path][0]
    # Spec-correct: verbatim slice of lines 1..2 of the file — identical bytes
    # to the file itself, i.e. NO trailing newline.
    body_expected = func_src

    ok_identity = ident == "foo"
    ok_verbatim = body_actual == body_expected

    if ok_identity and not ok_verbatim:
        print(
            "CONFIRMED — bug reproduced: body_text contains a trailing newline not present in the source file"
        )
        print(f"  identifier: {ident!r}")
        print(f"  actual   body_text: {body_actual!r}")
        print(f"  expected body_text: {body_expected!r}")
        print(f"  actual ends with newline: {body_actual.endswith(chr(10))} | expected ends with newline: {body_expected.endswith(chr(10))}")
    elif not ok_identity:
        print(f"ERROR: unexpected identifier: {ident!r} (expected 'foo')")
        sys.exit(1)
    else:
        print(
            "NOT CONFIRMED — body_text matched the verbatim source exactly (no appended newline): "
            f"{body_actual!r}"
        )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
