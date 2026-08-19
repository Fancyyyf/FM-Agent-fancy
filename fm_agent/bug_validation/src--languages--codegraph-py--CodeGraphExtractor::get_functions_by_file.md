# Bug Report: get_functions_by_file

**Source file:** `src/languages/codegraph-py/CodeGraphExtractor::get_functions_by_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Always returns a dict and never None. The dict is empty exactly when the language family of lang_key is unsupported by the index or when the index records no function or method nodes for that family. Otherwise the dict contains one entry for every indexed source file that the index attributes at least one function of the requested family to; files with no indexed functions of that family are absent from the result. Each key is the file's path resolved to absolute form, and each value is the complete list of (identifier, body_text) pairs for that file with one pair per indexed function, ordered by ascending source position, with no omissions and no duplicates. Each identifier is the function's canonical extraction identity: parser decorations stripped, scope/class qualification preserved as recorded by the index, canonicalized ('/' replaced by '_'), and deduplicated within the file by the deterministic rule shared with function extraction (the first occurrence of an identifier keeps the plain name, later occurrences in ascending start-line order receive _1, _2, ... suffixes), so identifiers coincide exactly with extracted function file names and call-graph node identities. Each body_text is the function's exact source text: the slice of the file's lines covering exactly the function's indexed span (the index stores 1-indexed inclusive bounds; the body covers precisely those lines, verbatim, in file order). The query covers every index language value associated with lang_key. The function never modifies any source file or the index.

---

### Actual Behavior

The method returns a dict `result` satisfying the following:

1. **Three-valued contract**: If `lang_key` does not map to a non-empty language list in `_CG_LANG`, the method returns `{}` (the empty dict), signalling 'handled, nothing found' to the caller, who must NOT fall back to regex extraction.

2. **Normal return structure**: Otherwise, `result` is a `dict[str, list[tuple[str, str]]]` mapping file-path keys to lists of `(deduped_identifier, body_text)` pairs.

3. **Key resolution**: For every key `k` in `result`: if `proj_dir` is not None, `k == os.path.join(proj_dir, file_path)` where `file_path` is the project-relative path stored in the codegraph index (i.e., keys are absolute paths); if `proj_dir` is None, `k == file_path` (the raw relative path from the index).

4. **Value content**: Each `(deduped_identifier, body_text)` pair corresponds to exactly one row from the `nodes` table where `kind IN ('function','method')` and `language` is in the set `_CG_LANG[lang_key]`. The `deduped_identifier` is produced by `_extraction_ident(name, qualified_name)` with a deterministic dedup suffix `_N` (N  1) appended only when two or more functions in the same file share the same canonical identifier; the first occurrence keeps the bare identifier, the second gets `_1`, etc., in ascending `start_line` order. `body_text` is the concatenation of source lines `all_lines[start_line-1 : end_line]` (1-indexed, inclusive end) from the file at the resolved path, guaranteed to end with `'\n'`.

5. **Ordering within each file's list**: Tuples appear in non-decreasing `start_line` order (inherited from the SQL `ORDER BY file_path, start_line`).

6. **Unreadable files silently skipped**: If opening a resolved file path raises `OSError`, that file is omitted from `result` entirely; no exception propagates to the caller for I/O failures on individual source files.

7. **Completeness**: Every file path in the query result that is successfully opened appears as a key in `result`, even if its function list would be empty (though in practice the SQL filter guarantees at least one row per grouped file).

8. **Resource cleanup**: The SQLite connection opened at `self._db` is closed before the method returns on the normal path (line 25). If an unhandled exception occurs between `connect` and `close` (e.g., a malformed SQL or unexpected DB error), the connection may leak; no `finally` guard is present.

9. **No mutation of receiver state**: `self` is not modified beyond the transient DB read.

Formally:  k  result: (proj_dir  None  k = os.path.join(proj_dir, rel_k))  (proj_dir = None  k = rel_k)  result[k] = [(id_i, body_i)] where each body_i ends with '\n' and id_i is unique within result[k]. If _CG_LANG.get(lang_key) is falsy  result = {}.

---

## Code Evidence

```py
Line 57: if not body.endswith("\n"):
Line 58:     body += "\n"
```

---

## Trigger Condition

The specification (Condition B) states that each body_text must be 'the function's exact source text' covering 'precisely those lines, verbatim, in file order.' When a source file lacks a trailing newline and the indexed function span reaches the final line, readlines() returns the last line without a '\n' terminator. The code unconditionally appends '\n' (lines 57-58), producing a body that contains a character not present in the original file. This violates the 'verbatim' and 'exact source text' requirement of the specification. A concrete input: a file ending without a newline where the function's end_line equals the file's last line.

---

## How to trigger the bug

The probe builds a fresh temporary directory containing a fixture project with a mocked codegraph index (`proj/.codegraph/codegraph.db`), so nothing in the active repository is used as the probe workspace. The fixture source file `fixture.py` ends **without** a trailing newline, and the single indexed function `foo` spans lines 1–2, i.e. its `end_line` (2) equals the file's last line. `CodeGraphExtractor.get_functions_by_file("python", proj_dir=...)` reads the file with `readlines()` (the last line therefore lacks `'\n'`), joins the span's lines, and then executes `if not body.endswith("\n"): body += "\n"`, which appends a newline character that does not exist in the original file. The specification requires the body to be the verbatim slice of exactly those indexed lines, so the returned body deviates from the source file by one extra character.

Note (FM-Agent self-validation guard): the probe does not start or call FM-Agent (`run_pipeline()`, `main.py`, CLI, OpenCode are never invoked); it loads only the smallest relevant unit, `CodeGraphExtractor`, via its public `from_proj_dir` factory, and feeds it a mocked SQLite index plus fixture files confined to the probe's temporary directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `lang_key` | `"python"` |
| `proj_dir` | `<tmpdir>/proj` (fresh temporary directory owned by the probe) |
| Fixture source file | `<tmpdir>/proj/fixture.py` with content `def foo():\n    return 1` (no trailing newline, 2 lines) |
| Mocked index node | `name="foo"`, `qualified_name="foo"`, `file_path="fixture.py"`, `start_line=1`, `end_line=2`, `kind="function"`, `language="python"` in `<tmpdir>/proj/.codegraph/codegraph.db` |

### Expected (spec-correct) Output

`'def foo():\n    return 1'` — the verbatim slice of lines 1–2; since the file itself has no trailing newline, no newline may be appended.

### Actual (buggy) Output

`'def foo():\n    return 1\n'` — a `'\n'` that does not exist in the source file is appended to the body.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package's public `CodeGraphExtractor` factory):

```python
import os, sqlite3, tempfile
from src.languages.codegraph import CodeGraphExtractor

tmp = tempfile.mkdtemp(prefix="cg_repro_")
src_dir = os.path.join(tmp, "proj")
os.makedirs(os.path.join(src_dir, ".codegraph"))
with open(os.path.join(src_dir, "fixture.py"), "w") as f:
    f.write("def foo():\n    return 1")  # no trailing newline

conn = sqlite3.connect(os.path.join(src_dir, ".codegraph", "codegraph.db"))
conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT, qualified_name TEXT,"
             " file_path TEXT, start_line INTEGER, end_line INTEGER, kind TEXT, language TEXT)")
conn.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
             (1, "foo", "foo", "fixture.py", 1, 2, "function", "python"))
conn.commit()
conn.close()

body = CodeGraphExtractor.from_proj_dir(src_dir).get_functions_by_file(
    "python", proj_dir=src_dir)[os.path.join(src_dir, "fixture.py")][0][1]
print(repr(body))
# actual (buggy) output: 'def foo():\n    return 1\n'
# expected (correct) output: 'def foo():\n    return 1'
```

---

## Probe Script

```py
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
```

### Probe Output

```
CONFIRMED — bug reproduced: body_text contains a trailing newline not present in the source file
  identifier: 'foo'
  actual   body_text: 'def foo():\n    return 1\n'
  expected body_text: 'def foo():\n    return 1'
  actual ends with newline: True | expected ends with newline: False
```
