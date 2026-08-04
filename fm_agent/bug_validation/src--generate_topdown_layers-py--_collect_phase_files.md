# Bug Report: _collect_phase_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_collect_phase_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (fpath, module_name) tuples. For each source_file path listed in each module of phase_data, the source file extension separator '.' is replaced by '-' to derive the extracted-function directory name, and that directory is searched under proj_dir/extracted_functions/. Every regular file found in that directory whose filename does not match the metadata sidecar naming pattern is included as one tuple where fpath is the absolute path to the file and module_name is the 'name' from the enclosing module object. Source files whose corresponding extracted-function directory does not exist under proj_dir/extracted_functions/ contribute no tuples. Each fpath is unique within the returned list. Results are ordered by module order in phase_data, then by source_file order, then by filesystem traversal order within each directory. The returned list may be empty if no extracted-function directories exist for any source file in the phase.

---

### Actual Behavior

Returns a list results = [(fpath, module_name), ...] that contains exactly one tuple for each regular file found by os.walk inside the directories derived from phase_data's modules' source files, excluding metadata sidecar files. Formally: Let R be the returned list. R is empty at first. For each module m in phase_data.get('modules', []) in the given list order, let m_name = m['name']. For each source file s in m.get('source_files', []) in its list order: let B = os.path.basename(s), D = os.path.dirname(s), dot = B.rfind('.'). Set dir_name = (B[:dot] + '-' + B[dot+1:] if dot > 0 else B). Set func_dir = os.path.join(proj_dir, 'extracted_functions', D, dir_name) if D else os.path.join(proj_dir, 'extracted_functions', dir_name). If os.path.isdir(func_dir), then for each (root, _dirs, fnames) in the order yielded by os.walk(func_dir) and for each fname in fnames in the order yielded: let fpath = os.path.join(root, fname). If os.path.isfile(fpath) and not _is_metadata_sidecar(fname) evaluates to True, then (fpath, m_name) is appended to R. No other elements are appended. The final value of R is the return value.

---

## Code Evidence

```
Line 7: for module in phase_data.get("modules", []):
Line 9:     for src_file in module.get("source_files", []):
Line 28:                     if os.path.isfile(fpath) and not _is_metadata_sidecar(fname):
Line 29:                         results.append((fpath, module_name))
```

---

## Trigger Condition

The code can produce duplicate fpath entries when the same extracted-function directory is traversed more than once (e.g., because the same source file appears in multiple modules), violating the specifications requirement that each fpath be unique in the returned list.

---

## How to trigger the bug

When `phase_data` contains two modules that both reference the same source file (e.g., `"foo/bar.cpp"`), the derived `func_dir` is identical for both modules. The `os.walk` on `func_dir` is executed twice — once per module — and each file found is appended to the results list with a different `module_name`. This produces duplicate fpath entries.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory with `extracted_functions/foo/bar-cpp/` containing `func_a.cpp` and `func_b.cpp` |
| `phase_data["modules"]` | `[{"name": "module_A", "source_files": ["foo/bar.cpp"]}, {"name": "module_B", "source_files": ["foo/bar.cpp"]}]` |

### Expected (spec-correct) Output

`[(<fpath_func_a>, "module_A"), (<fpath_func_b>, "module_A")]` — each fpath appears at most once.

### Actual (buggy) Output

`[(<fpath_func_b>, "module_A"), (<fpath_func_a>, "module_A"), (<fpath_func_b>, "module_B"), (<fpath_func_a>, "module_B")]` — each fpath appears twice (once per module).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.generate_topdown_layers import _collect_phase_files

with tempfile.TemporaryDirectory() as proj_dir:
    extracted_base = os.path.join(proj_dir, "extracted_functions")
    func_dir = os.path.join(extracted_base, "foo", "bar-cpp")
    os.makedirs(func_dir)
    for fname in ("func_a.cpp", "func_b.cpp"):
        with open(os.path.join(func_dir, fname), "w") as f:
            f.write("// extracted function\n")

    phase_data = {
        "modules": [
            {"name": "module_A", "source_files": ["foo/bar.cpp"]},
            {"name": "module_B", "source_files": ["foo/bar.cpp"]},
        ]
    }

    results = _collect_phase_files(proj_dir, phase_data)
    for fpath, mod in results:
        print(f"  {os.path.relpath(fpath, proj_dir)} -> module={mod}")

# actual (buggy) output: 4 entries — func_a and func_b each appear twice (with module_A, module_B)
# expected (correct) output: 2 entries — func_a and func_b each appear once
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'src' is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.generate_topdown_layers import _collect_phase_files

    with tempfile.TemporaryDirectory() as proj_dir:
        # Create mock extracted_function directory
        extracted_base = os.path.join(proj_dir, "extracted_functions")
        func_subdir = os.path.join(extracted_base, "foo", "bar-cpp")
        os.makedirs(func_subdir)

        # Create mock extracted function files
        func_a = os.path.join(func_subdir, "func_a.cpp")
        func_b = os.path.join(func_subdir, "func_b.cpp")
        for f in (func_a, func_b):
            with open(f, "w") as fh:
                fh.write("// extracted function\n")

        # Phase data where the same source_file appears in TWO different modules
        phase_data = {
            "modules": [
                {"name": "module_A", "source_files": ["foo/bar.cpp"]},
                {"name": "module_B", "source_files": ["foo/bar.cpp"]},
            ]
        }

        results = _collect_phase_files(proj_dir, phase_data)

        # Check uniqueness by fpath
        fpaths = [r[0] for r in results]
        seen = set()
        duplicates = set()
        for fp in fpaths:
            if fp in seen:
                duplicates.add(fp)
            seen.add(fp)

        if duplicates:
            print(
                "CONFIRMED — duplicate fpaths found in result:",
                [os.path.relpath(d, proj_dir) for d in duplicates],
            )
            print("Results:")
            for fpath, mod in results:
                print(f"  {os.path.relpath(fpath, proj_dir)} -> module={mod}")
        else:
            print(f"NOT CONFIRMED — all fpaths unique ({len(fpaths)} entries)")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — duplicate fpaths found in result: ['extracted_functions/foo/bar-cpp/func_a.cpp', 'extracted_functions/foo/bar-cpp/func_b.cpp']
Results:
  extracted_functions/foo/bar-cpp/func_b.cpp -> module=module_A
  extracted_functions/foo/bar-cpp/func_a.cpp -> module=module_A
  extracted_functions/foo/bar-cpp/func_b.cpp -> module=module_B
  extracted_functions/foo/bar-cpp/func_a.cpp -> module=module_B
```
