# [SPEC]
# Unit: src/languages/registry-py/call_edges_all.py
#
# call_edges_all(proj_dir: str, lang_keys) -> tuple[dict, set]
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory containing indexed source files
#   - lang_keys is an iterable of language key strings (e.g., "python", "go")
#   - REGISTRY is a mapping from language keys to objects exposing a call_edges method
#
# Post-condition:
#   - Returns (edges, langs) where edges is a dict mapping each caller's
#     fully-qualified function name to the set of fully-qualified names of
#     functions it directly calls, and langs is the set of language keys for
#     which the codegraph backend returned a result (even if empty).
#   - A language in lang_keys that is absent from REGISTRY is silently
#     skipped — it contributes no edges and is omitted from langs.
#   - For each language present in REGISTRY, if its call_edges method returns
#     None (backend unavailable), the language is excluded from langs,
#     signaling the caller to use regex-based edge detection for that language.
#   - For each language whose call_edges returns a dict, the language is added
#     to langs and its caller-to-callees mappings are merged into the returned
#     edges dict. When the same caller FQN appears in results from multiple
#     languages, the callee sets are unioned; no callee FQN is duplicated.
# [SPEC]

# [INFO]
# call_edges(proj_dir: str) -> dict | None
#   Pre-condition: proj_dir is a valid path to a project directory
#   Post-condition: Returns a dict mapping each caller FQN to the set of its
#     callee FQNs when the codegraph backend is available for the language;
#     returns None when the backend is unavailable, signaling the caller to
#     use regex-based call-edge detection for this language.
# [INFO]

def call_edges_all(proj_dir: str, lang_keys) -> tuple:
    """Call call_edges for each language in lang_keys and merge results.

    Returns (edges, langs) where edges is {caller_fqn: {callee_fqns}} and langs is
    the set of language keys codegraph handled (it returned a dict, even if empty
    — None means the backend was unavailable and the caller should use regex).
    """
    edges = {}
    langs = set()
    for lang in lang_keys:
        if lang not in REGISTRY:
            continue
        result = REGISTRY[lang].call_edges(proj_dir)
        # A handler returns None when its backend (codegraph) is unavailable, and
        # a dict (possibly empty) when it handled the language. Treat "handled but
        # no edges" as codegraph-authoritative — add the language to `langs` so the
        # caller uses the codegraph path — instead of falling back to regex, which
        # would otherwise invent edges (e.g. match a function's own signature) for
        # a genuinely call-free project.
        if result is not None:
            langs.add(lang)
            for key, callees in result.items():
                edges.setdefault(key, set()).update(callees)
    return edges, langs
