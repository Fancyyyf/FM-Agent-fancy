# Bug Report: `_src_rel_to_func_dir`

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple (func_dir, ext) of two strings. func_dir is the absolute path formed by joining the prefix '<proj_dir>/fm_agent/extracted_functions/' with the directory portion of the path of abs_src relative to proj_dir and a transformed basename component. The basename transformation: when the basename of abs_src contains a period character, the portion before the last period is joined by a hyphen to the portion after the last period (e.g., 'loader.cpp' becomes 'loader-cpp'); when the basename contains no period, the basename appears unchanged. ext is the substring of the basename after the last period, excluding the period itself; ext is the empty string when the basename contains no period.

---

### Actual Behavior

After execution, the function returns a tuple \\( (func\\_dir, ext) \\) with no side effects. Let \\( rel = os.path.relpath(abs\\_src, proj\\_dir) \\), \\( src\\_dir = os.path.dirname(rel) \\), \\( base = os.path.basename(rel) \\), and \\( dot = base.rfind(".") \\). If \\( dot > 0 \\), then \\( dir\\_name = base[:dot] + "-" + base[dot+1:] \\) and \\( ext = base[dot+1:] \\); otherwise \\( dir\\_name = base \\) and \\( ext = "" \\). Let \\( extracted\\_base = os.path.join(proj\\_dir, "fm\\_agent", "extracted\\_functions") \\). Then \\( func\\_dir = os.path.join(extracted\\_base, src\\_dir, dir\\_name) \\) if \\( src\\_dir \\neq "" \\), else \\( os.path.join(extracted\\_base, dir\\_name) \\). The returned \\( func\\_dir \\) is a string representing a filesystem path, and \\( ext \\) is a string (possibly empty) representing the derived file extension.

---

## Code Evidence

Line 9: if last_dot > 0:

---

## Trigger Condition

When the basename contains a period at the start (e.g., '.env'), last_dot equals 0, so the condition fails and the code takes the else branch, returning the original basename as dir_name and an empty ext. The specification, however, requires that any basename containing a period be transformed: the empty string before the last period and 'env' after should be joined with a hyphen, giving '-env', and ext should be 'env'. Thus the code's output violates the specification.

---

## How to trigger the bug

The bug occurs when `_src_rel_to_func_dir` is called with an `abs_src` whose basename starts with a period (e.g., `.env`, `.gitignore`, `.bashrc`). The condition `if last_dot > 0` on line 9 is `False` when the period is at position 0, so the else branch runs — returning the original basename and an empty extension instead of the spec-required transformation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory (e.g., `/tmp/tmpXXXXXX`) |
| `abs_src` | `<proj_dir>/src/.env` (a source file with a dotfile basename) |

### Expected (spec-correct) Output

`func_dir` ending in `.../src/-env`, `ext = "env"`

### Actual (buggy) Output

`func_dir` ending in `.../src/.env`, `ext = ""`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _src_rel_to_func_dir
import tempfile, os

with tempfile.TemporaryDirectory() as proj_dir:
    abs_src = os.path.join(proj_dir, "src", ".env")
    os.makedirs(os.path.dirname(abs_src), exist_ok=True)
    with open(abs_src, "w") as f:
        f.write("FOO=bar\n")
    func_dir, ext = _src_rel_to_func_dir(proj_dir, abs_src)
    print(os.path.basename(func_dir))  # actual (buggy): '.env' — expected: '-env'
    print(ext)                         # actual (buggy): ''     — expected: 'env'
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure repo root is on sys.path so that `config` and `src` resolve
_repo_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _src_rel_to_func_dir
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as proj_dir:
        # Create a source file whose basename starts with a period (dotfile)
        abs_src = os.path.join(proj_dir, "src", ".env")
        os.makedirs(os.path.dirname(abs_src), exist_ok=True)
        with open(abs_src, "w") as f:
            f.write("FOO=bar\n")

        actual_func_dir, actual_ext = _src_rel_to_func_dir(proj_dir, abs_src)

        # Per spec: basename `.env` contains a period, so:
        #   portion before last period = "" (empty)
        #   portion after last period  = "env"
        #   dir_name = "" + "-" + "env" = "-env"
        #   ext = "env"
        expected_dir_name = "-env"
        expected_ext = "env"

        actual_dir_name = os.path.basename(actual_func_dir)
        passed = actual_dir_name != expected_dir_name or actual_ext != expected_ext

        if passed:
            print(
                f"CONFIRMED — actual: dir_name={actual_dir_name!r}, ext={actual_ext!r}"
                f" | expected: dir_name={expected_dir_name!r}, ext={expected_ext!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected:"
                f" dir_name={actual_dir_name!r}, ext={actual_ext!r}"
            )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: dir_name='.env', ext='' | expected: dir_name='-env', ext='env'
```
