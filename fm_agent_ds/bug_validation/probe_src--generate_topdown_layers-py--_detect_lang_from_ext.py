import sys
import os

# Add project root to sys.path so 'src' package is importable
project_root = "/home/fancy/Projects_Vault/FM-Agent"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.generate_topdown_layers import _detect_lang_from_ext
    from src import extract

    # Sanity check 1: with current registry, dotless filenames return None
    actual_normal = _detect_lang_from_ext("Makefile")
    assert actual_normal is None, f"Expected None for dotless 'Makefile', got {actual_normal!r}"

    # Inject empty-string key to demonstrate the spec violation
    original_has_empty_key = "" in extract.EXT_TO_LANG
    original_value = extract.EXT_TO_LANG.get("")
    extract.EXT_TO_LANG[""] = "python"

    # Bug trigger: dotless filename should return None per spec,
    # but code delegates to EXT_TO_LANG.get("") which now returns "python"
    actual = _detect_lang_from_ext("Makefile")
    expected = None  # Spec: returns None when no dot in filename

    passed = actual != expected

    # Restore EXT_TO_LANG
    if original_has_empty_key:
        extract.EXT_TO_LANG[""] = original_value
    else:
        del extract.EXT_TO_LANG[""]

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
