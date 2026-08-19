import sys
import os
import tempfile

project_root = os.path.abspath("/home/fancy/Projects_Vault/FM-Agent")
workspace = tempfile.mkdtemp(prefix="fm_agent_probe_")
os.chdir(workspace)

try:
    sys.path.insert(0, project_root)

    from src.languages.codegraph import CodeGraphExtractor
    from src.incremental_reasoner import _codegraph_functions_by_file

    # Mock CodeGraphExtractor.from_proj_dir to return a mock extractor
    # that has get_functions_by_file which, like the real implementation,
    # returns {} for unrecognized lang keys.
    class MockExtractor:
        def get_functions_by_file(self, lang_key, proj_dir=None):
            # Real _CG_LANG keys for reference
            cg_langs = {
                "python":     ["python"],
                "go":         ["go"],
                "rust":       ["rust"],
                "c":          ["c"],
                "cpp":        ["cpp"],
                "java":       ["java"],
                "javascript": ["javascript", "jsx"],
                "typescript": ["typescript", "tsx"],
            }
            if lang_key not in cg_langs:
                return {}
            # Recognized key — return a dummy mapping
            return {os.path.join(project_root, "dummy.py"): {"func": "def f(): pass"}}

    original_from_proj_dir = CodeGraphExtractor.from_proj_dir
    CodeGraphExtractor.from_proj_dir = classmethod(lambda cls, proj_dir: MockExtractor())

    # Test: unrecognized lang_key should NOT raise an exception.
    # Spec says: "Returns a dict ... or None if no index."
    # An unrecognized key matches no files → empty dict {} is correct.
    actual = _codegraph_functions_by_file(project_root, ["nonexistent_lang_key"])
    expected = {}

    if isinstance(actual, dict) and actual == expected:
        print(f"NOT CONFIRMED — no exception; returned {actual!r} (expected {expected!r})")
    elif isinstance(actual, dict):
        print(f"CONFIRMED — returned {actual!r} (expected {expected!r})")
    else:
        print(f"NOT CONFIRMED — returned {actual!r} instead of dict")

    # Restore original
    CodeGraphExtractor.from_proj_dir = original_from_proj_dir

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
