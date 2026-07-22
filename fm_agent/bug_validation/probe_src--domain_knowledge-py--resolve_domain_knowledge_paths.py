"""Probe script for bug: resolve_domain_knowledge_paths calls os.path.abspath
before existence validation, breaking paths through symlinks with '..'."""

import os
import sys
import tempfile
import shutil

# Ensure the project root is on sys.path so 'src' is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    # Create a temporary directory structure:
    #
    #   tmp/
    #   ├── doc.md                # /tmp/xxx/doc.md   ← the actual file
    #   ├── real/                  # directory
    #   └── base/
    #       └── link -> ../real/   # symlink
    #
    # Then call resolve_domain_knowledge_paths with:
    #   base_dir = tmp/base/
    #   paths = ["link/../doc.md"]
    #
    # The OS resolves the path through the symlink:
    #   tmp/base/link/../doc.md
    #     → link resolves to ../real (= tmp/real)
    #     → .. goes up to tmp/
    #     → doc.md = tmp/doc.md  (EXISTS)
    #
    # But os.path.abspath() does LEXICAL normalization:
    #   tmp/base/link/../doc.md  →  tmp/base/doc.md  (does NOT exist)
    #
    # The spec says to use the candidate path directly for checks.
    # The code calls os.path.abspath() at line 58 BEFORE the existence check,
    # turning an existing path into a non-existent one → spurious ValueError.

    tmpdir = tempfile.mkdtemp(prefix="fm_probe_")
    try:
        # Setup directory structure
        base_dir = os.path.join(tmpdir, "base")
        real_dir = os.path.join(tmpdir, "real")
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(real_dir, exist_ok=True)

        # Create the actual markdown file at tmp/doc.md
        doc_path = os.path.join(tmpdir, "doc.md")
        with open(doc_path, "w") as f:
            f.write("# Test doc\n")

        # Create symlink: tmp/base/link -> ../real  (relative symlink)
        link_path = os.path.join(base_dir, "link")
        os.symlink("../real", link_path)

        # Load the target function via the package module
        from src.domain_knowledge import resolve_domain_knowledge_paths

        # The input path: "link/../doc.md" relative to base_dir
        # Through the symlink: link → ../real (= tmp/real), .. → tmp/, doc.md → tmp/doc.md (EXISTS)
        # os.path.abspath makes it: tmp/base/doc.md (does NOT exist) ← BUG
        raw_input = "link/../doc.md"

        try:
            result = resolve_domain_knowledge_paths([raw_input], base_dir=base_dir)
            # If no ValueError, the bug is NOT confirmed
            print(f"NOT CONFIRMED — function returned {result!r} unexpectedly")
        except ValueError as e:
            # The bug is confirmed — the function raised ValueError for a path
            # that actually exists on the filesystem
            expected_path = os.path.join(tmpdir, "doc.md")
            actual_exists = os.path.exists(expected_path)
            print(
                f"CONFIRMED — ValueError raised for existing file: {e}\n"
                f"  actual file path: {expected_path}\n"
                f"  actual file exists: {actual_exists}\n"
                f"  abspath'd path: {os.path.abspath(os.path.join(base_dir, raw_input))}"
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
