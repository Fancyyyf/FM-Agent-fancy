# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::codegraph-py::_qualified_parts` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: (none).

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
def _qualified_parts(name: str, qualified_name: str) -> list:
    """Split codegraph's ``qualified_name`` into ``[*scope_parts, name]``.

    Member functions carry their enclosing class (and namespace) so they can be
    told apart by class instead of by an opaque line-order suffix:

        free function ``main``                 -> ``['main']``
        C++ ``LocalStorage::Flush``            -> ``['LocalStorage', 'Flush']``
        nested ``ns::Widget::draw``            -> ``['ns', 'Widget', 'draw']``
        dot-scoped (Python/Java) ``Foo.bar``   -> ``['Foo', 'bar']``

    codegraph joins scopes with ``::`` (C/C++) or ``.`` (Python, Java, ...); both
    are normalised here. If ``qualified_name`` is missing or does not end with
    ``name`` (unexpected shape), we fall back to the bare name so behaviour never
    regresses below the previous name-only scheme.
    """
    q = (qualified_name or "").strip()
    if not q or not q.endswith(name):
        return [name]
    scope = q[: -len(name)].rstrip(":.")
    if not scope:
        return [name]
    parts = [p for p in re.split(r"::|\.", scope) if p]
    return parts + [name]
```

## Specs of this function's callers

### src::languages::codegraph-py::_extraction_ident

# [SPEC]
# Unit: src/languages/codegraph.py
#
# _extraction_ident(name: str, qualified_name: str) -> str
#
# Pre-condition:
#   - name and qualified_name are strings obtained from the codegraph database for a single function or method node
#
# Post-condition:
#   - Returns a string composed of one or more components joined by the literal "::"
#   - When qualified_name is non-empty and its suffix equals name, the leading components of the returned string (all except the last) correspond, in order, to the scope qualifiers extracted from the prefix of qualified_name that precedes name
#   - When qualified_name is empty or its suffix does not equal name, the returned string consists of exactly one component
#   - The final component of the returned string is derived from name
#   - No component of the returned string contains any character that would be a directory separator in any filesystem
#   - No component of the returned string contains signature syntax, pointer syntax, or template syntax that may have been present in the raw database column values
#   - The same (name, qualified_name) pair always produces the same returned string
#   - The separator character ("." vs "::") used in qualified_name does not affect the set or order of scope components in the returned string
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::codegraph-py::_extraction_ident

# _qualified_parts(name: str, qualified_name: str) -> list
#   Pre-condition:
#     - name and qualified_name are strings
#   Post-condition:
#     - Returns a list of non-empty strings
#     - The last element of the returned list equals name
#     - When qualified_name is non-empty and has name as a suffix, the elements before the last are the scope qualifier components extracted from the prefix of qualified_name that precedes name, split on "::" or "."
#     - When qualified_name is empty or does not have name as a suffix, the returned list is [name]
#     - The character used as the scope separator in qualified_name ("." or "::") does not affect the set or order of components in the returned list

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. This function has no callees, so produce no [INFO] block.
4. Write your answer to `fm_agent/spec_generate_127.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
