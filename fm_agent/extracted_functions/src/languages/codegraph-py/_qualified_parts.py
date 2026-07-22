# [SPEC]
# Unit: src/languages/codegraph.py
#
# _qualified_parts(name: str, qualified_name: str) -> list
#
# Pre-condition:
#   - name and qualified_name are strings
#
# Post-condition:
#   - Returns a list of non-empty strings
#   - The last element of the returned list equals name
#   - When qualified_name is non-empty and has name as a suffix, the elements before the last are the scope qualifier components extracted from the prefix of qualified_name that precedes name, split on "::" or "."
#   - When qualified_name is empty or does not have name as a suffix, the returned list is [name]
#   - The character used as the scope separator in qualified_name ("." or "::") does not affect the set or order of components in the returned list
#   - The same (name, qualified_name) pair always produces the same returned list
# [SPEC]

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
