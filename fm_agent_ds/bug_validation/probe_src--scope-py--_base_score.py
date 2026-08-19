import sys
import os

# ── Load the package via its public entry point ───────────────────────────────
# Run from repo root: sys.path[0] handles the import chain
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

try:
    import scope as scope_module
except ImportError:
    # The module has relative imports (.extract, .llm_client); try as a package
    try:
        import src.scope as scope_module
    except ImportError as e2:
        print(f'ERROR: Could not import scope module: {e2}')
        sys.exit(1)

_base_score = scope_module._base_score

# ── Bug test: traceback function name matches a NAME PART but NOT the full name ──
# The spec claims that only the full name is tested case-insensitively against
# traceback-function signals. The code additionally matches individual name parts
# (line 385: tf.lower() in parts), causing a false positive W_TRACEBACK contribution.

empty = set()

# name "some_sort_data" decomposes via _name_parts into parts including "sort"
# signals['traceback_funcs'] contains "sort" — a part match but NOT a full-name match
name = "some_sort_data"
signals = {
    'traceback_funcs': {"sort"},
    'backtick_idents': empty,
    'dotted_refs': empty,
    'plain_idents': empty,
    'exception_types': empty,
    'all_words': empty,
}

try:
    actual = _base_score(name, empty, empty, empty, 1, signals)
    # Expected: 0.0 — only the full name should be tested against traceback_funcs.
    # "sort" != "some_sort_data", so no match should occur.
    expected = 0.0
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
