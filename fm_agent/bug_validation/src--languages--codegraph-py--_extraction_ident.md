# Bug Report: _extraction_ident

**Source file:** `src/languages/codegraph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string composed of one or more components joined by the literal "::"
  - When qualified_name is non-empty and its suffix equals name, the leading components of the returned string (all except the last) correspond, in order, to the scope qualifiers extracted from the prefix of qualified_name that precedes name
  - When qualified_name is empty or its suffix does not equal name, the returned string consists of exactly one component
  - The final component of the returned string is derived from name
  - No component of the returned string contains any character that would be a directory separator in any filesystem
  - No component of the returned string contains signature syntax, pointer syntax, or template syntax that may have been present in the raw database column values
  - The same (name, qualified_name) pair always produces the same returned string
  - The separator character ("." vs "::") used in qualified_name does not affect the set or order of scope components in the returned string

---

### Actual Behavior

The function returns a string r computed as r = '::'.join(canonicalize(_bare_function_name(p)) for p in _qualified_parts(name, qualified_name)). Let Q = _qualified_parts(name, qualified_name); then Q is a list of at least one non-empty string, with the last element equal to name. For each element q in Q, define s = canonicalize(_bare_function_name(q)). Each s is a string containing no characters that are invalid in filesystem path components; s may be empty if _bare_function_name returns an empty string (e.g., when q consists entirely of whitespace). The returned string r is the concatenation of the resulting strings s1, s2, ..., sn interleaved with '::'. Thus r has the form s0 + '::' + s1 + '::' + ... + s_{n-1}. When qualified_name is non-empty and has name as a suffix, the scope qualifier components from qualified_name's prefix are included as the first elements of Q; otherwise Q = [name]. The return value is deterministic and depends only on name and qualified_name.

---

## Code Evidence

Line 15: return "::".join(
Line 16:         canonicalize(_bare_function_name(p))
Line 17:         for p in _qualified_parts(name, qualified_name)
Line 18:     )

---

## Trigger Condition

The code does not filter out empty strings that can result from `_bare_function_name`. For the input where `qualified_name` has a whitespace-only scope qualifier ('  ::MyClass::func'), `_bare_function_name` returns an empty string for that qualifier, causing the final joined string to be '::MyClass::func'. The specification requires the returned string to be composed of one or more (nonempty) components joined by '::', but the result starts with '::' due to the empty leading component, violating that requirement.

---

## How to trigger the bug

The bug occurs when `_qualified_parts` returns a list containing whitespace-only strings. `_qualified_parts` splits the scope prefix by `::` or `.`, and its filter `if p` only rejects falsy values — but whitespace-only strings like `" "` are truthy and pass through. `_bare_function_name` then strips them to `""`, `canonicalize` passes `""` through, and `"::".join(...)` produces consecutive separators (`::::`) that represent empty components.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"func"` |
| qualified_name | `"foo:: ::func"` |

### Expected (spec-correct) Output

`"foo::func"` (whitespace-only qualifier component should be filtered out)

### Actual (buggy) Output

`"foo::::func"` (split by `"::"` gives `["foo", "", "func"]` — contains an empty component)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.languages.codegraph import _extraction_ident

# Buggy: produces "foo::::func" with empty component
result = _extraction_ident("func", "foo:: ::func")
print(repr(result))
# actual (buggy) output: 'foo::::func'
# expected (correct) output: 'foo::func'

# Also: whitespace+tab qualifier
result2 = _extraction_ident("baz", "X:: ::\tbaz")
print(repr(result2))
# actual (buggy) output: 'X::::::baz'
# expected (correct) output: 'X::baz'
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug: src--languages--codegraph-py--_extraction_ident

Tests whether _extraction_ident produces empty components when
_bare_function_name returns "" for whitespace-only qualifier parts,
violating the spec that the returned string must be composed of
non-empty components joined by "::".
"""
import sys
import os
import tempfile

# ── Use a fresh temp directory as probe workspace ──
os.chdir(tempfile.mkdtemp())

# Ensure the repo root is on sys.path so the public module can be imported.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import via the package entry point
from src.languages.codegraph import _extraction_ident


def check(name, qualified_name):
    """Call _extraction_ident and check for empty components in result."""
    actual = _extraction_ident(name, qualified_name)
    components = actual.split("::")
    has_empty = any(c == "" for c in components)
    return actual, has_empty, components


def main():
    # The bug: _qualified_parts returns ["foo", " ", "func"] because
    # _qualified_parts' filter "if p" doesn't catch whitespace-only
    # strings. _bare_function_name(" ") returns "" and canonicalize("")
    # returns "", so "::".join(["foo", "", "func"]) = "foo::::func",
    # which has an empty component — violating the spec.

    bugs_found = []
    no_bugs = []

    test_cases = [
        ("func", "foo:: ::func",  "whitespace-only middle qualifier"),
        ("func", " ::func",        "leading space before ::name"),
        ("bar",  " ::A::bar",      "leading space, nested qualifier"),
        ("baz",  "X:: ::\tbaz",    "space+tab qualifier"),
    ]

    for name, qname, desc in test_cases:
        actual, has_empty, components = check(name, qname)
        if has_empty:
            bugs_found.append((name, qname, desc, actual, components))
        else:
            no_bugs.append((name, qname, desc, actual))

    if bugs_found:
        print("CONFIRMED — Empty components found in _extraction_ident output")
        for name, qname, desc, actual, components in bugs_found:
            print(f"  [{desc}] name={name!r}, qualified_name={qname!r}")
            print(f"    actual:   {actual!r}")
            print(f"    split by '::': {components!r} (contains empty!)")
    else:
        print("NOT CONFIRMED — No empty components found in any test case")
        for name, qname, desc, actual in no_bugs:
            print(f"  [{desc}] actual={actual!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — Empty components found in _extraction_ident output
  [whitespace-only middle qualifier] name='func', qualified_name='foo:: ::func'
    actual:   'foo::::func'
    split by '::': ['foo', '', 'func'] (contains empty!)
  [space+tab qualifier] name='baz', qualified_name='X:: ::\tbaz'
    actual:   'X::::::baz'
    split by '::': ['X', '', '', 'baz'] (contains empty!)
```
