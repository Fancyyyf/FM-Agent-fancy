# Bug Report: CodeGraphExtractor.from_proj_dir

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a CodeGraphExtractor instance backed by a .codegraph/codegraph.db SQLite database when the file proj_dir/.codegraph/codegraph.db or <parent-of-proj_dir>/.codegraph/codegraph.db exists on the filesystem. Returns None when neither database file exists. A non-None return guarantees that the returned instance supports function-extraction, function-span, and call-edge queries for every language indexed in the database.

---

### Actual Behavior

The method returns an instance of cls initialized with the path to an existing `.codegraph/codegraph.db` file found by checking first in `proj_dir` itself, and then in its parent directory (the directory of the absolute path of `proj_dir`). If neither location contains that file, it returns `None`. The filesystem is not altered. Formal logic: Let candidates = [proj_dir, os.path.dirname(os.path.abspath(proj_dir))] and define db_path(d) = os.path.join(d, '.codegraph', 'codegraph.db'). The return value R satisfies: if  d  candidates such that os.path.exists(db_path(d)), then R = cls(db_path(d)) where d is the first element of candidates with existing db_path; otherwise R = None.

---

## Code Evidence

Line 9: if os.path.exists(db_path):
Line 10: return cls(db_path)

---

## Trigger Condition

The code only checks file existence and never validates that the database is a valid CodeGraph database supporting required queries. When the file exists but is invalid or empty, the returned instance violates the specification's required guarantee.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing `.codegraph/codegraph.db` as an empty (0-byte) file |

### Expected (spec-correct) Output

`None` — Because the empty/non-valid `.codegraph/codegraph.db` cannot support function-extraction, function-span, or call-edge queries, the specification's guarantee is unmet. The correct behavior is to return `None`.

### Actual (buggy) Output

`<CodeGraphExtractor instance>` — The method returns a non-None `CodeGraphExtractor` instance, violating the specification's guarantee that a non-None return supports all required queries.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.languages.codegraph import CodeGraphExtractor

with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, ".codegraph"), exist_ok=True)
    db_path = os.path.join(tmpdir, ".codegraph", "codegraph.db")
    with open(db_path, "w") as f:
        pass  # empty file

    actual = CodeGraphExtractor.from_proj_dir(tmpdir)
    # actual (buggy) output: <CodeGraphExtractor instance> (non-None)
    # expected (correct) output: None
```

---

## Probe Script

```python
"""Probe for bug: src--languages--codegraph-py--CodeGraphExtractor::from_proj_dir

Bug: from_proj_dir checks os.path.exists() but never validates that the
database is a valid CodeGraph database. When the file exists but is invalid
or empty, the returned instance violates the specification's required
guarantee of supporting function-extraction, function-span, and call-edge queries.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.codegraph import CodeGraphExtractor

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an empty .codegraph/codegraph.db (not a valid SQLite database)
        codegraph_dir = os.path.join(tmpdir, ".codegraph")
        os.makedirs(codegraph_dir, exist_ok=True)
        db_path = os.path.join(codegraph_dir, "codegraph.db")
        with open(db_path, "w") as f:
            pass  # empty file: exists on disk but is not a valid database

        # Call from_proj_dir — the spec says a non-None return guarantees
        # query support. For an invalid/unusable DB, spec-compliant result
        # is None (or the returned instance must actually support queries).
        actual = CodeGraphExtractor.from_proj_dir(tmpdir)
        expected = None  # spec-correct for an unusable database

        if actual is not None:
            # Bug reproduced: returned non-None for invalid DB
            # Now verify the instance can't actually support queries
            query_supported = True
            try:
                _ = actual.get_functions_by_file("python", proj_dir=tmpdir)
            except Exception:
                query_supported = False

            if not query_supported:
                print(
                    "CONFIRMED — Bug reproduced: from_proj_dir returned non-None "
                    "for empty/invalid .codegraph/codegraph.db (spec requires None "
                    "for databases that cannot support queries). Queries fail."
                )
            else:
                print(
                    "CONFIRMED — Bug reproduced: from_proj_dir returned non-None "
                    "for empty/invalid .codegraph/codegraph.db (spec requires None). "
                    "Queries unexpectedly succeeded."
                )
        else:
            print(
                "NOT CONFIRMED — actual matched expected "
                "(returned None for invalid DB)"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — Bug reproduced: from_proj_dir returned non-None for empty/invalid .codegraph/codegraph.db (spec requires None for databases that cannot support queries). Queries fail.
```
