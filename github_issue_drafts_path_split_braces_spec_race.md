# Validated GitHub Issue Drafts

Validation was performed against the current implementation, not only against
the generated FM-Agent specifications.

| Mismatch | Validation result | Confidence / scope |
| --- | --- | --- |
| 009 | Reproduced | Real path-resolution correctness bug. Whether symlink-plus-`..` inputs must be supported is a product-policy question, but the function currently selects an existing candidate and then turns it into a non-existent path. |
| 050 | Reproduced | Real missing-containment behavior. Practical reachability depends on a stale, malformed, or compromised CodeGraph database; it is weaker as a standalone security report than mismatch 066. |
| 066 | Reproduced end to end | High-confidence project-boundary violation: an accepted `phases.json` entry can cause reads and generated-file writes outside the project/work directory. Symlink escapes are also accepted. |
| 045 | Reproduced with an incorrect source slice | Real LSP-coordinate mapping bug for rare raw control characters such as VT/FF. `keepends=True` is not the cause; `str.splitlines()` uses a broader set of line boundaries than LSP. |
| 071 | Reproduced with a valid C block comment | High-confidence brace-depth bug independent of the generated specification. |
| 073 | Reproduced with a real concurrent producer write | Real race: a file can become ready after the scan and before the producer-completion check, then be skipped by the current invocation. |

---

## Issue 1

### Title

Harden path resolution against absolute paths, `..`, and symlink escapes

### Description

#### Summary

Several path consumers use lexical joining/normalization without enforcing the
intended filesystem boundary. Together, these behaviors can:

1. accept project source paths that resolve outside `proj_dir`;
2. read source files referenced by a malformed CodeGraph database from outside
   the project;
3. write extracted-function files outside
   `fm_agent/extracted_functions`; and
4. reject a valid domain-knowledge path when it combines a symlink with `..`.

The strongest issue is the `phases.json` path because that file is generated or
updated by an LLM and therefore must not be treated as a trusted filesystem
capability.

#### Affected locations

- `src/pipeline_setup.py:731-751`
  (`_phases_cover_current_sources`)
- `src/extract.py:715-776` (`run_extraction`)
- `src/languages/codegraph.py:263-331`
  (`CodeGraphExtractor.get_functions_by_file`)
- `src/languages/go.py:4-7` (`batch_extract`; the shared CodeGraph behavior
  affects the other CodeGraph-backed languages as well)
- `src/domain_knowledge.py:35-75`
  (`resolve_domain_knowledge_paths`)

#### Problem 1: `phases.json` paths are not confined to the project

`_phases_cover_current_sources` currently checks:

```python
os.path.exists(os.path.join(proj_dir, source_file))
```

This does not enforce containment:

- an absolute `source_file` discards `proj_dir`;
- `../` can traverse above `proj_dir`; and
- a relative path can traverse a symlink whose target is outside `proj_dir`.

For example:

```json
{
  "phases": [
    {
      "phase": 1,
      "name": "phase",
      "modules": [
        {
          "name": "module",
          "source_files": ["/tmp/outside/evil.py"]
        }
      ]
    }
  ]
}
```

If the plan also contains all current project sources (or the project contains
none), `_phases_cover_current_sources(...)` returns `True`.

`run_extraction` then repeats the unsafe operation:

```python
src_path = os.path.join(proj_dir, src_rel)
src_dir = os.path.dirname(src_rel)
out_dir = os.path.join(output_base, src_dir, dir_name)
```

When `src_rel` and therefore `src_dir` are absolute, the absolute component
discards `output_base` as well. An end-to-end test produced:

```text
coverage accepted = True
outside source read = True
outside output written = True
outside output = /tmp/.../outside/evil-py/escaped.py
```

A symlink-only escape is also accepted:

```text
project/link -> /tmp/outside
source_files = ["link/linked.py"]
```

The coverage check returned `True`, and extraction read the file whose real path
was `/tmp/outside/linked.py`.

#### Problem 2: CodeGraph database paths are trusted without containment

`CodeGraphExtractor.get_functions_by_file` reads `file_path` values from SQLite
and uses:

```python
abs_path = os.path.join(proj_dir, file_path)
with open(abs_path, "r", errors="replace") as f:
    ...
```

A database row containing:

```text
../outside/evil.go
```

causes `batch_extract(proj_dir)` to read and return a key outside the project:

```text
/tmp/.../project/../outside/evil.go
```

Fresh normal runs usually rebuild `.codegraph/codegraph.db`, which reduces
exposure to a pre-existing malformed database. However, `--resume` deliberately
reuses an existing database, and `batch_extract` is also callable independently.
The extractor should validate database paths rather than assuming that all
producers are permanently trustworthy and bug-free.

#### Problem 3: lexical `abspath()` breaks an existing symlink path

`resolve_domain_knowledge_paths` first selects an existing candidate, then calls
`os.path.abspath()` before validating it again:

```python
path = next(candidate for candidate in candidates if os.path.exists(candidate))
path = os.path.abspath(path)
if not os.path.exists(path):
    raise ValueError(...)
```

Consider:

```text
tmp/
├── doc.md
├── real/
└── base/
    └── link -> ../real/
```

with:

```python
resolve_domain_knowledge_paths(
    ["link/../doc.md"],
    base_dir="tmp/base",
)
```

The kernel resolves the original candidate component by component:

```text
tmp/base/link/../doc.md
-> tmp/real/../doc.md
-> tmp/doc.md
```

That file exists. `os.path.abspath`, however, performs lexical normalization:

```text
tmp/base/link/../doc.md
-> tmp/base/doc.md
```

The function therefore raises:

```text
ValueError: domain knowledge file does not exist: link/../doc.md
```

This part is primarily a correctness issue rather than a project escape:
domain-knowledge CLI paths may intentionally refer to files outside the project.

#### Expected behavior

- Every source path from `phases.json` or CodeGraph must resolve to a regular
  supported source file whose real path is inside the intended project root.
- Every generated output path must independently resolve inside the intended
  output root.
- Domain-knowledge paths should either be explicitly rejected by policy or
  resolved according to real filesystem semantics; an existing candidate should
  not become non-existent because of lexical normalization.

#### Impact

- Reads of files outside the analyzed project.
- Generated function files can be created or overwritten outside
  `fm_agent/extracted_functions`.
- Analysis can include source code that is not part of the requested project.
- Valid domain-knowledge files can be rejected unexpectedly.

This is security-relevant whenever `phases.json`, an existing CodeGraph
database, or the analyzed project is not fully trusted.

#### Suggested fix

1. Introduce a single containment helper for project-owned paths:

   ```python
   def resolve_under(root, raw):
       if not raw or os.path.isabs(raw):
           raise ValueError(...)
       root_real = os.path.realpath(root)
       candidate_real = os.path.realpath(os.path.join(root_real, raw))
       try:
           contained = os.path.commonpath([root_real, candidate_real]) == root_real
       except ValueError:
           contained = False
       if not contained:
           raise ValueError(...)
       return candidate_real
   ```

2. Use it when validating `phases.json` and again immediately before reading a
   source file. Do not rely on a single upstream validation point.
3. Validate CodeGraph `file_path` rows using the same project-root rule.
4. Independently validate `out_dir`/`out_file` against the real output root
   before creating directories or opening files.
5. For domain knowledge, where external files may be allowed, canonicalize the
   selected existing candidate with `realpath()`/`Path.resolve(strict=True)`
   rather than applying lexical `abspath()` first.

#### Regression tests

Please cover:

- absolute POSIX paths;
- `../` traversal;
- symlinks inside the project that target files/directories outside it;
- malformed CodeGraph rows with absolute and parent-relative paths;
- output-path containment;
- symlink-plus-`..` domain-knowledge paths; and
- cross-drive `commonpath` failures on platforms where relevant.

---

## Issue 2

### Title

Use LSP end-of-line rules when converting Erlang positions to source offsets

### Description

#### Summary

`_SourceIndex.build` uses Python's broad `str.splitlines()` semantics to build
the line table used for ELP/LSP positions:

```python
lines = source.splitlines(keepends=True)
```

Python treats vertical tab (`\v`/`\x0b`), form feed (`\f`/`\x0c`), NEL, and
several Unicode separator characters as line boundaries. LSP defines document
end-of-line sequences as `\n`, `\r\n`, and `\r`.

As a result, a raw control character can create a line in `_SourceIndex` that
does not exist in the ELP/LSP coordinate system. Every subsequent LSP line can
then map to the wrong source offset.

`keepends=True` is not the cause of the over-splitting. It only retains the
recognized separators so offsets can be accumulated. Changing it to
`keepends=False` would still split on the same characters and would also make
offset calculation incorrect. The splitting algorithm must change.

References:

- Python `str.splitlines()`:
  https://docs.python.org/3/library/stdtypes.html#str.splitlines
- LSP text-document positions and EOL sequences:
  https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/#text-documents

#### Affected locations

- `src/languages/erlang.py:325-355` (`_SourceIndex`)
- `src/languages/erlang.py:505-529` (ELP symbol-range consumer)

#### Trigger

The source must contain a raw control character, not the two literal characters
backslash and `v`.

For example:

```python
source = (
    "-module(m).\n"
    "f() -> \"left\x0bright\".\n"
    "g() -> ok.\n"
)
```

ELP/LSP sees three lines:

```text
0: -module(m).
1: f() -> "left<VT>right".
2: g() -> ok.
```

`str.splitlines(keepends=True)` creates four:

```text
0: '-module(m).\n'
1: 'f() -> "left\x0b'
2: 'right".\n'
3: 'g() -> ok.\n'
```

The resulting offsets are:

```text
[0, 12, 25, 33]
```

If ELP reports `g/0` with a range from `(line=2, character=0)` to
`(line=3, character=0)`, `source_for_range` currently returns:

```text
'right".\n'
```

instead of:

```text
'g() -> ok.\n'
```

#### Impact

The function identifier from ELP can be paired with source text from another
function or with a truncated fragment. That incorrect body then flows into
extracted functions, specification generation, and verification, causing false
positives or missed defects.

The trigger is uncommon in hand-written Erlang, so this is likely a lower
priority than the project path issue. It is still a deterministic protocol
mapping error and can occur in generated files, comments, or strings containing
raw formatting control characters.

#### Suggested fix

Build the line table with exactly the LSP end-of-line sequences:

```text
\n
\r\n
\r
```

Preserve those terminators when calculating offsets, and continue converting
the LSP character component according to the negotiated/default UTF-16
encoding.

#### Regression tests

- `\n`, `\r\n`, and `\r` produce the expected line starts.
- Raw `\v`, `\f`, `\x85`, `\u2028`, and `\u2029` do not increment the LSP line
  number.
- A symbol after each control character maps to the exact original source
  slice.
- Non-BMP characters still consume two UTF-16 code units.

---

## Issue 3

### Title

Track block-comment state across lines when computing brace depth

### Description

#### Summary

`_compute_brace_depth_per_line` scans each line independently. It skips a block
comment only until the end of the current line and does not preserve an
`in_block_comment` state for the following line.

The implementation comment says:

```python
# If block comment spans lines, we ignore braces inside it (simplified)
```

but braces on subsequent comment lines are processed as real syntax.

#### Affected locations

- `src/reasoner.py:25-79` (`_compute_brace_depth_per_line`)
- `src/reasoner.py:82-147` (`_split_into_blocks_braced`, which consumes the
  incorrect depths)

#### Reproduction

This valid C/C++ input contains a closing brace inside a block comment:

```c
int f() {
    /* comment starts
       }
    */
    return 0;
}
```

Equivalent test:

```python
lines = [
    "int f() {",
    "    /* comment starts",
    "       }",
    "    */",
    "    return 0;",
    "}",
]

assert _compute_brace_depth_per_line(lines) == [1, 1, 1, 1, 1, 0]
```

Current result:

```text
[1, 1, 0, 0, 0, -1]
```

The brace in the comment closes the function early, and the real final brace
then drives the depth negative.

#### Impact

`_split_into_blocks_braced` treats the computed depth as a safe syntactic
boundary:

```python
if depths[j] == entry_depth:
    split_point = j
```

Incorrect depths can therefore split a function at a comment or nested-block
boundary. The reasoner then chains postconditions across blocks that do not
represent valid syntactic units, increasing both false-positive and
false-negative verification results.

The issue affects languages routed through this shared brace scanner, including
C, C++, Java, JavaScript/TypeScript, Rust, and similar brace-delimited
languages.

#### Suggested fix

At minimum, preserve lexical state across lines:

```text
in_block_comment
in_string / string kind where the language permits continuation
escape state where applicable
```

Only count braces while outside comments and literals. A language-aware lexer or
tree-sitter tokens would be safer than continuing to extend one simplified
scanner for several languages with different literal/comment rules.

#### Regression tests

- Multi-line block comments containing `{` and `}`.
- A block comment that starts and ends on the same line.
- Comment terminators followed by real braces on the same line.
- Escaped quotes and language-supported continued/multiline strings.
- Final depth is zero for balanced functions, and all chosen split points are
  outside comments and literals.

---

## Issue 4

### Title

Rescan ready files after spec producers exit to avoid skipping verification

### Description

#### Summary

`streaming_reasoner` scans extracted-function files for completed
`[SPEC]`/`[INFO]` headers and only afterward checks whether all spec-generation
producers have exited.

If a producer finishes a file after that file's readiness check returned
`False`, but before the producer-completion check, the watcher can exit without
performing one final scan. The file is complete on disk but is never submitted
to `_verify_single_file` during the current invocation.

#### Affected locations

- `src/verification.py:108-132` (readiness scan and submission)
- `src/verification.py:205-226` (producer-completion early exit)
- `main.py:422-444` (caller and outer completion behavior)

#### Race timeline

```text
Watcher                         Spec producer
-------                         -------------
is_file_ready(file) -> False
                                writes final [SPEC]/[INFO] marker
                                exits successfully
all spec_procs are done -> True
unready = expected - processed
no reasoning/validation futures
break
```

`unready` is actually the set of unprocessed files. The code does not call
`is_file_ready()` for that set before reporting it as missing specs and exiting.

#### Reproduction result

A deterministic concurrency test used a real producer future and a real file:

1. the file initially contained an incomplete SPEC header;
2. the watcher read it and observed `False`;
3. the producer then wrote a complete `[SPEC]/[INFO]` header and returned `0`;
4. the watcher observed the completed future and exited.

Observed result:

```text
file ready after producer exit = True
producer done = True
verify calls = []
processed = set()
```

The warning was also misleading:

```text
Spec generation process(es) exited (codes [0])
but no files received [SPEC]/[INFO] markers.
```

The file did have all required markers by the time that warning was emitted.

#### Impact

- No logic-verification result is written for the missed function.
- A real mismatch in that function cannot reach bug validation.
- Progress and summary counts can under-report verification coverage.
- The log can claim that specs are missing even though they are complete.
- If the outer loop sees that all spec batches are complete, it may finish the
  layer without invoking the reasoner again. A later `--resume` can recover the
  missing result, but the current run is incomplete.

The race window is narrow, but it is reachable during normal concurrent spec
generation and does not require invalid arguments or corrupted state.

#### Suggested fix

After observing that all producers are done:

1. perform a final scan of every expected file that is neither processed nor
   submitted;
2. submit all files that are now ready;
3. wait for the resulting reasoning/validation futures; and
4. only report pending files after a post-producer scan confirms that they are
   still not ready.

For example:

```python
if all_producers_done:
    remaining = expected_files - processed - submitted
    ready_now = {path for path in remaining if is_file_ready(path)}
    if ready_now:
        submit_all(ready_now)
        continue

    if remaining and not reasoning_futures and not validation_futures:
        report_pending(remaining)
        break
```

If producers modify files in place rather than using an atomic temporary-file
replacement, consider requiring stable size/mtime across scans or changing the
producer to write and `os.replace()` a completed file.

#### Regression test

Use a producer future synchronized to finish immediately after the watcher's
first `is_file_ready()` call. Assert that:

- the producer is done;
- the file is ready;
- `_verify_single_file` is called exactly once; and
- the returned `processed` set includes the file.
