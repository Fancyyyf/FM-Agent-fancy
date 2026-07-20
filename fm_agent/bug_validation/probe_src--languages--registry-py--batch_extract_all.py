import sys
import os

# Ensure repo root is on sys.path so we can import src
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.registry import batch_extract_all, REGISTRY, LanguageHandler

    # Save original registry for restoration
    original_registry = dict(REGISTRY)

    # Clear real handlers and install a single mock handler
    REGISTRY.clear()

    # Construct a non-normalized absolute path (contains ".." component)
    non_normalized = os.path.join("/tmp", "a", "..", "b", "file.py")
    normalized = os.path.normpath(non_normalized)
    # non_normalized = "/tmp/a/../b/file.py"
    # normalized      = "/tmp/b/file.py"

    def mock_batch_extract(proj_dir):
        return {non_normalized: [("func1", "def func1():\n    pass")]}

    mock_handler = LanguageHandler(
        batch_extract=mock_batch_extract,
        call_edges=lambda _proj_dir: {},
        function_spans=lambda _proj_dir, _filepath: None,
    )
    REGISTRY["mock"] = mock_handler

    # Exercise the public API
    funcs, langs = batch_extract_all("/tmp")

    keys = list(funcs.keys())

    # Restore original registry before asserting
    REGISTRY.clear()
    REGISTRY.update(original_registry)

    if len(keys) != 1:
        print(f"NOT CONFIRMED — unexpected number of keys: {len(keys)} (expected 1)")
    elif keys[0] == non_normalized and keys[0] != normalized:
        print(f"CONFIRMED — actual: {keys[0]!r} | expected (normalized): {normalized!r}")
    elif keys[0] == normalized:
        print(f"NOT CONFIRMED — key is already normalized: {keys[0]!r}")
    else:
        print(f"NOT CONFIRMED — unexpected key: {keys[0]!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
