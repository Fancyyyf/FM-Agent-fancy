import sys
import os

# Ensure repo root is on sys.path for the src package import
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

try:
    from src.domain_knowledge import resolve_domain_knowledge_paths

    base_dir = os.getcwd()
    # Non-existent file — spec says it should be silently excluded,
    # but the code raises ValueError (the bug)
    paths = ["nonexistent_markdown_file.md"]

    actual = resolve_domain_knowledge_paths(paths, base_dir)
    expected = []  # spec: invalid entries excluded → empty result

    if actual != expected:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except ValueError as e:
    # The ValueError itself confirms the bug — spec requires silent exclusion
    print(f"CONFIRMED — ValueError raised instead of excluding invalid entry: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
