# Bug Report: extract_existing_specs

**Source file:** `/tmp/fm_agent_wt_FM-Agent__ro_f_c_/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/extract_existing_specs.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When fm_agent/extracted_functions/ does not exist or is not a directory,
    returns an empty dict without raising an error.
  - When the extracted_functions directory exists, returns a dict whose keys
    are file paths relative to fm_agent/extracted_functions/ (using os.sep
    as the path separator).
  - Each key maps to an object with exactly two fields: "spec" (str) and
    "info" (str or None).
  - A file is included as a key IFF it contains a valid [SPEC] block (i.e.,
    extract_spec_block returns non-None for that file).
  - The "spec" value for each key is the complete text of the file's [SPEC]
    block, including both the opening and closing [SPEC] markers.
  - The "info" value is the complete text of the file's [INFO] block
    (including both opening and closing [INFO] markers) when the file
    contains a valid [INFO] block; it is None when the file has no [INFO]
    block or the block is not extractable.
  - All regular files under fm_agent/extracted_functions/ are visited
    (subdirectories are traversed recursively).
  - Returns a plain dict; iteration order of keys is not guaranteed.
  - Does not modify any file on disk.

---

### Actual Behavior

The function returns a dictionary mapping relative file paths to specification-info records. More precisely: Let `extracted_dir = os.path.join(proj_dir, 'fm_agent', 'extracted_functions')`. 

- If `extracted_dir` does not exist or is not a directory, the function returns an empty dictionary `{}` without raising an exception (early return).
- Otherwise, `os.walk` traverses the directory tree rooted at `extracted_dir`. For each file `fname` encountered in a directory `root`, the path `fp = Path(root) / fname` is passed to `extract_spec_block` and `extract_info_block`. 
  * `spec_block = extract_spec_block(fp)` returns the full [SPEC] block (including markers) if present, or `None`.
  * `info_block = extract_info_block(fp)` returns the body text between [INFO] markers (excluding markers) if present, or `None`.
  * If `spec_block` is `None`, the file is ignored (no entry added to result).
  * If `spec_block` is not `None`, the file's relative path `rp = os.path.relpath(str(fp), extracted_dir)` is used as the key. The value is a dictionary with two keys:
    - `'spec'`: the value of `spec_block`.
    - `'info'`: if `info_block` is `None` then `None`; otherwise, the full [INFO] block reconstructed with opening and closing markers. The marker line is formed as `{prefix} [INFO]` where `prefix = _detect_comment_prefix(spec_block) or ''`, and the result is `f'{info_tag}\n{info_block}\n{info_tag}'` with `info_tag = (prefix + ' [INFO]').strip()`.
- All exceptions raised by the helper functions (`extract_spec_block`, `extract_info_block`, `_detect_comment_prefix`) during the traversal propagate uncaught to the caller. In particular, if any file is not a regular file or cannot be read, those helpers may raise OSError or other exceptions.
- The function has no side effects on the file system or global state.

Formal logic:
Let `D = os.path.join(proj_dir, 'fm_agent', 'extracted_functions')`.

---

## Code Evidence

Line 35: full_info_block = None
Line 36: if info_block is not None:
Line 37:     prefix = _detect_comment_prefix(spec_block) or ""
Line 38:     info_tag = f"{prefix} [INFO]".strip()
Line 39:     full_info_block = f"{info_tag}\n{info_block}\n{info_tag}"

---

## Trigger Condition

The specification requires the 'info' value to be the exact complete text of the file's [INFO] block (including original markers). The code reconstructs the block using the comment prefix detected from the [SPEC] block, which may differ from the actual comment prefix used around the [INFO] block. In the counterexample, the spec block uses '#' but the info block uses '//', causing the output info string to misrepresent the actual file content.

---

## How to trigger the bug

When a file under `fm_agent/extracted_functions/` has indented comment markers (e.g., `   # [SPEC]` and `   # [INFO]`), the reconstructed INFO block loses the leading indentation on the markers because `info_tag = f"{prefix} [INFO]".strip()` removes leading whitespace. Additionally, `extract_info_block`'s own `.strip()` on its return value strips leading whitespace from the first body line.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Any directory containing `fm_agent/extracted_functions/` with a file using indented `# [SPEC]` and `# [INFO]` markers |

### Expected (spec-correct) Output

```
   # [INFO]
   # info line one
   # info line two
   # [INFO]
```

### Actual (buggy) Output

```
# [INFO]
# info line one
   # info line two
# [INFO]
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os
tmpdir = tempfile.mkdtemp()
extracted_base = os.path.join(tmpdir, "fm_agent", "extracted_functions", "test_pkg")
os.makedirs(extracted_base)

test_file = os.path.join(extracted_base, "test_probe.py")
with open(test_file, "w") as f:
    f.write(
        "   # [SPEC]\n"
        "   # spec line one\n"
        "   # [SPEC]\n"
        "\n"
        "   # [INFO]\n"
        "   # info line one\n"
        "   # info line two\n"
        "   # [INFO]\n"
    )

from src.incremental_reasoner import extract_existing_specs
result = extract_existing_specs(tmpdir)
actual = result.get("test_pkg/test_probe.py", {}).get("info")
# actual (buggy) output: "# [INFO]\n# info line one\n   # info line two\n# [INFO]"
# expected (correct) output: "   # [INFO]\n   # info line one\n   # info line two\n   # [INFO]"
```

---

## Probe Script

```python
"""Probe script for bug src--incremental_reasoner-py--extract_existing_specs.

Bug: extract_existing_specs reconstructs INFO block markers using
_detect_comment_prefix(spec_block) with .strip(), losing indentation
that was present in the original file's comment markers. The spec requires
the complete text of the file's [INFO] block including original markers.
"""
import sys
import os
import tempfile
import shutil

# Ensure repo root is on the path so 'src' and 'config' imports resolve
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from src.incremental_reasoner import extract_existing_specs


def main():
    # Create <tmpdir>/fm_agent/extracted_functions/test_pkg/test_probe.py
    tmpdir = tempfile.mkdtemp()
    try:
        extracted_base = os.path.join(tmpdir, "fm_agent", "extracted_functions")
        pkg_dir = os.path.join(extracted_base, "test_pkg")
        os.makedirs(pkg_dir)

        test_file = os.path.join(pkg_dir, "test_probe.py")
        file_content = (
            "   # [SPEC]\n"
            "   # spec line one\n"
            "   # spec line two\n"
            "   # [SPEC]\n"
            "\n"
            "   # [INFO]\n"
            "   # info line one\n"
            "   # info line two\n"
            "   # [INFO]\n"
        )
        with open(test_file, "w") as f:
            f.write(file_content)

        # Expected per spec: complete text of the file's [INFO] block
        # including ORIGINAL markers (with indentation).
        expected_info = (
            "   # [INFO]\n"
            "   # info line one\n"
            "   # info line two\n"
            "   # [INFO]"
        )

        result = extract_existing_specs(tmpdir)
        # Key is relative to fm_agent/extracted_functions/ → "test_pkg/test_probe.py"
        rel_path = os.path.join("test_pkg", "test_probe.py")
        entry = result.get(rel_path)
        if entry is None:
            print("ERROR: test file not found in result dict (keys: %r)" % list(result.keys()))
            sys.exit(1)
        actual_info = entry.get("info")

        # The spec says info should be the complete text of the file's [INFO]
        # block including ORIGINAL markers. The buggy code strips indentation
        # via .strip() on the reconstructed info_tag, producing markers without
        # the leading spaces.
        passed = actual_info != expected_info

        if passed:
            print(
                "CONFIRMED — actual: %r | expected: %r"
                % (actual_info, expected_info)
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected: %r"
                % (actual_info,)
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: '# [INFO]\n# info line one\n   # info line two\n# [INFO]' | expected: '   # [INFO]\n   # info line one\n   # info line two\n   # [INFO]'
```
