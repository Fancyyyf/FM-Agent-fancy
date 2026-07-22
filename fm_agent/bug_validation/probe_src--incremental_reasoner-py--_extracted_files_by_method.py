"""Probe script for bug: _extracted_files_by_method returns defaultdict(list),
which mutates the mapping when a caller accesses a missing key and modifies
the returned list. The spec requires that mutating the returned list does NOT
affect the mapping."""

import os
import sys
import tempfile
from collections import defaultdict


# The function under test — exact copy from src/incremental_reasoner.py lines 423-451.
# It only depends on os and defaultdict (both stdlib), so a direct copy is safe.
def _extracted_files_by_method(func_dir):
    """``{key: [abs_path, ...]}`` for every extracted-function file under
    ``func_dir``, walked recursively. Each file is registered under BOTH keys so a
    caller can look it up whichever kind of name it holds:

      - its bare stem (``Flush``) — the regex change detector reports names
        without a class, so a bare name matches every same-named member;
      - its class-qualified identifier (``LocalStorage::Flush``) — scope ranking
        gets qualified names from codegraph spans, so this gives an exact match.

    A free function (``func_dir/foo.ext``) has identical stem and identifier, so it
    is registered once."""
    index = defaultdict(list)
    if not os.path.isdir(func_dir):
        return index
    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.join(root, fn)
            stem = fn[: fn.rfind(".")] if "." in fn else fn
            index[stem].append(abs_path)
            bare = stem.split("::")[-1]
            if bare != stem:
                index[bare].append(abs_path)
    return index


def main():
    errors = []

    # Test 1: non-existent directory — returns empty mapping.
    # Per spec, accessing missing key should return empty list WITHOUT mutating mapping.
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = os.path.join(tmpdir, "does_not_exist")
        result = _extracted_files_by_method(nonexistent)

        # Capture initial length of the mapping
        initial_keys = set(result.keys())

        # Access a missing key — this triggers defaultdict's factory, creating the key
        returned_list = result["nonexistent_key"]

        # Mutate the returned list
        returned_list.append("/fake/path")

        # Check if the mapping was mutated (BUG: defaultdict adds the key)
        final_keys = set(result.keys())

        if "nonexistent_key" in final_keys:
            errors.append(
                "BUG CONFIRMED (Test 1): accessing missing key 'nonexistent_key' and "
                "mutating returned list modified the mapping. "
                f"Initial key count: {len(initial_keys)}, "
                f"Final key count: {len(final_keys)}. "
                "Spec requires: mutating returned list does NOT affect the mapping."
            )
        else:
            errors.append(
                "Test 1 passed: mapping was not mutated by accessing missing key."
            )

    # Test 2: directory with files — access a key NOT present in the mapping.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files so the mapping has legitimate entries
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "Foo.py"), "w") as f:
            f.write("")
        with open(os.path.join(tmpdir, "subdir", "Bar.py"), "w") as f:
            f.write("")

        result = _extracted_files_by_method(tmpdir)

        # These keys SHOULD be present (from the files we created)
        existing_keys_before = set(result.keys())
        assert "Foo" in existing_keys_before, f"Expected 'Foo' in keys, got {existing_keys_before}"
        assert "Bar" in existing_keys_before, f"Expected 'Bar' in keys, got {existing_keys_before}"

        # Access a key NOT in the mapping (a function name that doesn't exist)
        missing_key = "NonExistentFunction"
        assert missing_key not in existing_keys_before, f"{missing_key} should not be in mapping"

        returned_list_2 = result[missing_key]
        returned_list_2.append("/another/fake/path")

        keys_after = set(result.keys())
        if missing_key in keys_after:
            errors.append(
                "BUG CONFIRMED (Test 2): accessing missing key 'NonExistentFunction' "
                "and mutating returned list modified the mapping with existing files. "
                f"Keys before: {sorted(existing_keys_before)}, "
                f"Keys after: {sorted(keys_after)}. "
                "Spec requires: mutating returned list does NOT affect the mapping."
            )
        else:
            errors.append(
                "Test 2 passed: mapping was not mutated by accessing missing key "
                "when mapping already has entries."
            )

    # Report
    if errors:
        # Print bug reports first, then the verdict
        for err in errors:
            print(err)
        print("CONFIRMED")
    else:
        print("NOT CONFIRMED — all tests passed; mapping was not mutated")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
