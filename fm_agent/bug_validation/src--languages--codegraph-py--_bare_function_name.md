# Bug Report: _bare_function_name

**Source file:** `/tmp/fm_agent_wt_FM-Agent_jx75d3w8/snapshot/src/languages/codegraph-py/_bare_function_name.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the bare declared identifier of the node, with the following guarantees. (1) Scope reduction: no scope separator and no scope prefix occurs in the result; however deeply the component is qualified, the result identifies only the innermost declared entity. (2) Decoration stripping: every parser-specific addition  appended signature or parameter text, template bodies, receiver decorations, pointer declarators  is removed, leaving only the declared identifier, with the exception that for an operator overload the declared identifier is itself an operator name. (3) Operator overloads: when the innermost component declares an operator overload  the keyword 'operator' followed, with any intervening whitespace ignored for recognition, by an operator token  the result is that overload's name formed from the keyword 'operator' together with the operator token, where the token is a bracket pair, a memory-management operator with or without array-form brackets (whitespace variants inside such a token yield the same name), or the maximal leading run of operator punctuation characters. (4) Idempotence on bare input: when name is already an undecorated identifier, the result is that identifier itself, with surrounding whitespace (if any) removed. (5) Emptiness contract: the result is empty if and only if name contains no non-whitespace characters; every component containing a recognizable identifier yields a non-empty result. The function is deterministic for identical inputs, raises no exception for any string input, and does not modify name.

---

### Actual Behavior

The function returns a string `result` representing the bare function/method identifier extracted from the input `name`. Formally, let `s = name.strip()` (the whitespace-stripped input). The following cases exhaustively describe `result`:

1. If `s == ""`, then `result == ""`.
2. Otherwise, let `tail` be defined as: if `"::" in s`, then `tail = s.rsplit("::", 1)[1].lstrip()`; elif `"." in s`, then `tail = s.rsplit(".", 1)[1].lstrip()`; else `tail = s`.
3. If `tail.startswith("operator")`:
   a. Let `rest = tail[len("operator"):].lstrip()`.
   b. If `rest.startswith("[]")`, then `result == "operator[]"`.
   c. Elif `rest.startswith("()")`, then `result == "operator()"`.
   d. Elif `re.fullmatch(r'new(?:\s*\[\s*\])?', rest)`, then `result == "operator new[]"` if `"[" in rest` else `"operator new"`.
   e. Elif `re.fullmatch(r'delete(?:\s*\[\s*\])?', rest)`, then `result == "operator delete[]"` if `"[" in rest` else `"operator delete"`.
   f. Else, collect the maximal prefix of `rest` consisting solely of characters in `"+-*/%&|^~!=<>,"` into `symbol`. If `symbol` is non-empty, `result == "operator" + "".join(symbol)`.
   g. If none of (b)(f) matched, fall through to step 4.
4. If `re.search(r'(?:^|::|\.)(\w+)$', s)` matches, `result` is the captured group (the trailing word-component of `s`).
5. Elif `re.match(r'\(\s*\*\s*(\w+)\s*\)', s)` matches (function-pointer declarator), `result` is the captured identifier.
6. Elif `re.match(r'\*\s*(\w+)', s)` matches (pointer-return prefix), `result` is the captured identifier.
7. Elif `re.match(r'^(\w+)', s)` matches, `result` is the leading word.
8. Else `result == s` (the stripped input returned unchanged).

In all paths, `result` is of type `str`. The result contains no scope-qualification separators (`::` or `.`), no pointer declarators (`*`), no parenthesised parameter lists, and no leading/trailing whitespace. The caller's original `name` binding is unaffected (Python string immutability; the local rebinding on line 17 is local only). No exception is raised assuming the `re` module is importable and `name` is of type `str`; a `TypeError` would propagate if `name` is not a string, and a `NameError` if `re` is not defined in scope.

---

## Code Evidence

```py
Line 31: if re.fullmatch(r'new(?:\s*\[\s*\])?', rest):
Line 32:     return "operator new[]" if "[" in rest else "operator new"
Line 33: if re.fullmatch(r'delete(?:\s*\[\s*\])?', rest):
Line 34:     return "operator delete[]" if "[" in rest else "operator delete"
```

---

## Trigger Condition

The specification (Condition B) requires that appended signature or parameter text is stripped from operator overloads, so 'operator new(int)' should yield 'operator new'. However, the code uses re.fullmatch on lines 31 and 33, which requires the entire `rest` string to match the pattern. For input 'operator new(int)', rest becomes 'new(int)', which does not fullmatch r'new(?:\s*\[\s*\])?' because of the trailing '(int)'. The operator-symbol collection loop also fails because 'n' is not an operator punctuation character. Execution falls through to line 52 where re.match(r'^(\w+)', name) captures only 'operator', returning 'operator' instead of the spec-required 'operator new'. The same issue affects 'operator delete(size_t)' and 'operator new[](size_t)'.

---

## How to trigger the bug

The probe feeds a codegraph-style `nodes` row whose `name` column carries an operator-overload declaration with appended parameter text — a shape the function's own docstring acknowledges ("Tree-sitter sometimes stores a full function signature in the name column"). The row is written into a fixture SQLite database (`.codegraph/codegraph.db`) inside a probe-owned temporary directory, and is then processed through the public extraction API `CodeGraphExtractor.from_proj_dir()` / `CodeGraphExtractor.get_function_spans()`, which routes every node name through `_extraction_ident` → `canonicalize(_bare_function_name(component))`.

Inside `_bare_function_name('operator new(int)')`: `rest` becomes `'new(int)'`; `re.fullmatch(r'new(?:\s*\[\s*\])?', 'new(int)')` fails (the whole string must match, but `'(int)'` trails); the operator-punctuation loop rejects the leading `'n'`; and the generic fallback `re.match(r'^(\w+)')` captures only `'operator'`. The spec instead requires the appended parameter text to be stripped, yielding the declared overload name `'operator new'`. A second row with `qualified_name = 'Vec::operator new(int)'` demonstrates the same loss after scope reduction (`'Vec::operator'` instead of `'Vec::operator new'`).

### Inputs

| Parameter | Value |
|-----------|-------|
| `name` (codegraph node name) | `operator new(int)` |
| `qualified_name` (free-function row) | `operator new(int)` |
| `qualified_name` (member row, secondary check) | `Vec::operator new(int)` |
| `kind` | `function` / `method` |
| `language` | `cpp` |

### Expected (spec-correct) Output

`operator new` (member row: `Vec::operator new`) — appended parameter text `(int)` stripped, memory-management operator overload name preserved.

### Actual (buggy) Output

`operator` (member row: `Vec::operator`) — the overload name is truncated to the `operator` keyword.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import os
import sqlite3
import tempfile

from src.languages.codegraph import CodeGraphExtractor

tmp = tempfile.mkdtemp()
proj = os.path.join(tmp, "proj")
os.makedirs(os.path.join(proj, ".codegraph"))

with open(os.path.join(proj, "a.cpp"), "w") as f:
    f.write("void* operator new(int size) { return nullptr; }\n")

conn = sqlite3.connect(os.path.join(proj, ".codegraph", "codegraph.db"))
conn.execute(
    "CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT,"
    " qualified_name TEXT, file_path TEXT, start_line INTEGER,"
    " end_line INTEGER, kind TEXT, language TEXT)"
)
conn.execute(
    "INSERT INTO nodes (name, qualified_name, file_path, start_line,"
    " end_line, kind, language) VALUES"
    " ('operator new(int)', 'operator new(int)', 'a.cpp', 1, 1,"
    "  'function', 'cpp')"
)
conn.commit()
conn.close()

ext = CodeGraphExtractor.from_proj_dir(proj)
print(ext.get_function_spans("cpp", os.path.join(proj, "a.cpp"))[0][0])
# actual (buggy) output: 'operator'
# expected (correct) output: 'operator new'
```

---

## Probe Script

```py
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
```

### Probe Output

```
CONFIRMED — free: actual='operator' expected='operator new' | qualified: actual='Vec::operator' expected='Vec::operator new'
```
