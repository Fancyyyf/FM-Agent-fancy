# Bug Report: stage_domain_knowledge_files

**Source file:** `src/domain_knowledge.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The specification requires that when `markdown_paths` is truthy and non-empty, the staging directory is **atomically replaced**: "a temporary directory is populated, then atomically swapped into place; a concurrent reader either sees the complete old state or the complete new state."

The actual code at lines 167–168 does `shutil.rmtree(target_dir, ignore_errors=True)` followed by `os.replace(tmp_dir, target_dir)`. Between these two calls, `target_dir` does not exist on the filesystem, creating a window where a concurrent reader would observe an incomplete (missing) directory. This violates the atomicity guarantee described in the specification.

The probe confirms this by monkey-patching `os.replace` to inspect the filesystem state immediately before the atomic rename occurs: at that point the target directory is already gone because `rmtree` has already executed, proving the non-atomic gap.

### Specification Claim

- When markdown_paths is falsy (None or empty): the staging directory
    <work_dir>/spec_prompts/domain_context/user_knowledge/ is NOT modified;
    any previously staged files are preserved. This supports resume runs.
  - When markdown_paths is truthy and non-empty: the staging directory is
    atomically replaced to contain exactly copies of the resolved markdown
    files plus a manifest file recording which source files were staged.
  - The replacement is atomic: a temporary directory is populated, then
    atomically swapped into place; a concurrent reader either sees the
    complete old state or the complete new state.
  - Returns a sorted list of project-relative path strings, each prefixed
    with "fm_agent/", for all domain knowledge files that are currently
    staged under the work directory.
  - The returned paths use "/" as the path separator regardless of platform.

---

### Actual Behavior

After executing stage_domain_knowledge_files(proj_dir, work_dir, markdown_paths):

If markdown_paths is falsy (None or an empty iterable), then the function returns the list of currently staged domain knowledge file paths relative to the project root (each prefixed with 'fm_agent/') as returned by list_staged_domain_knowledge_relpaths(work_dir). The file system remains unchanged; no files in the staging directory are added, removed, or modified.

If markdown_paths is truthy (a non-empty iterable of path strings), then:
1. Let resolved = resolve_domain_knowledge_paths(markdown_paths, base_dir=proj_dir, fallback_base_dir=os.getcwd()). resolved is a list of existing absolute source file paths.
2. Let target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR). The function atomically replaces the entire directory at target_dir with a new staging directory containing:
   - For each source_path in resolved, a copy of that file under a unique safe filename target_name = _safe_staged_name(source_path, used_names) (no two target_names are the same). The copy preserves file metadata (via shutil.copy2).
   - A manifest file named USER_KNOWLEDGE_MANIFEST containing a JSON object with a key 'files' whose value is a list of objects, each with 'source_path' (the resolved absolute path) and 'staged_path' ('fm_agent/' followed by the relative path from work_dir to the staged copy, using forward slashes).
3. After the atomic replacement, the staging directory at target_dir contains exactly those files and the manifest; any previous contents (including files from earlier invocations) are permanently removed.
4. The function returns the list of staged domain knowledge file paths as described by list_staged_domain_knowledge_relpaths(work_dir), which is a sorted list of strings, each beginning with 'fm_agent/', corresponding to the newly staged files (one per unique target_name).

---

## Code Evidence

```
Line 167:     shutil.rmtree(target_dir, ignore_errors=True)
Line 168:     os.replace(tmp_dir, target_dir)
```

---

## Trigger Condition

The atomicity specification requires that the directory replacement be atomic so that a concurrent reader sees either the full old state or the full new state, with no intermediate missing or empty directory. The code deletes the existing directory with rmtree, then renames the temporary directory; there is a window where the directory does not exist, violating atomicity.

---

## How to trigger the bug

The function `stage_domain_knowledge_files` performs a non-atomic directory swap. Between `shutil.rmtree(target_dir)` and `os.replace(tmp_dir, target_dir)`, the target directory does not exist on the filesystem. A concurrent reader (another thread, process, or external observer) inspecting the staging directory during this window will see a missing directory rather than either the complete old contents or the complete new contents.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | temporary directory containing two `.md` files (`dk1.md`, `dk2.md`) |
| `work_dir` | temporary workspace directory with pre-populated staging dir |
| `markdown_paths` (call 1) | `["dk1.md"]` — populates the staging dir |
| `markdown_paths` (call 2) | `["dk2.md"]` — triggers the non-atomic replacement |

### Expected (spec-correct) Output

The staging directory is atomically replaced. At no point does a reader observe a missing or empty directory. Either the old contents (from call 1) or the new contents (from call 2) are visible.

### Actual (buggy) Output

Between `shutil.rmtree(target_dir)` (line 167) and `os.replace(tmp_dir, target_dir)` (line 168), the target directory does not exist. A reader checking `os.path.exists(target_dir)` or `os.listdir(target_dir)` during this window receives no directory / FileNotFoundError.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile, shutil, time

# repo root on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)
from src import domain_knowledge

proj_dir = tempfile.mkdtemp()
work_dir = tempfile.mkdtemp()
md1 = os.path.join(proj_dir, "dk1.md")
md2 = os.path.join(proj_dir, "dk2.md")
with open(md1, "w") as f: f.write("# One\n")
with open(md2, "w") as f: f.write("# Two\n")

# pre-populate staging dir
domain_knowledge.stage_domain_knowledge_files(proj_dir, work_dir, [md1])
target_dir = os.path.join(work_dir, "spec_prompts", "domain_context", "user_knowledge")

# monkey-patch os.replace to detect the gap
original = domain_knowledge.os.replace
missing = []

def intercept(src, dst):
    if not os.path.exists(dst):
        missing.append(True)
    time.sleep(0.05)
    return original(src, dst)

domain_knowledge.os.replace = intercept

# trigger non-atomic swap
domain_knowledge.stage_domain_knowledge_files(proj_dir, work_dir, [md2])

if missing:
    print("BUG CONFIRMED: directory was missing between rmtree and replace")
    # actual (buggy) output: target_dir does not exist during the gap
    # expected (correct) output: target_dir always exists (old or new state)
else:
    print("bug NOT confirmed")

shutil.rmtree(proj_dir, ignore_errors=True)
shutil.rmtree(work_dir, ignore_errors=True)
```

---

## Probe Script

```python
"""Probe: stage_domain_knowledge_files non-atomic directory replacement.

The spec requires atomic replacement ("atomically swapped into place; a
concurrent reader either sees the complete old state or the complete new
state").  The code uses shutil.rmtree() followed by os.replace(), creating a
window where the target directory does not exist — a non-atomic gap.
"""

import os
import sys
import tempfile
import shutil

# Ensure the repo root is on sys.path so that "src" is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src import domain_knowledge
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    proj_dir = tempfile.mkdtemp(prefix="bug_probe_proj_")
    work_dir = tempfile.mkdtemp(prefix="bug_probe_work_")

    try:
        # ── create two small markdown fixtures ──────────────────────
        md1 = os.path.join(proj_dir, "dk1.md")
        with open(md1, "w", encoding="utf-8") as f:
            f.write("# Domain Knowledge 1\n")

        md2 = os.path.join(proj_dir, "dk2.md")
        with open(md2, "w", encoding="utf-8") as f:
            f.write("# Domain Knowledge 2\n")

        # ── pre-populate staging dir (call 1) ───────────────────────
        domain_knowledge.stage_domain_knowledge_files(proj_dir, work_dir, [md1])

        target_dir = os.path.join(
            work_dir, "spec_prompts", "domain_context", "user_knowledge"
        )

        # sanity: target_dir must exist before the second call
        if not os.path.isdir(target_dir):
            print(
                "ERROR: staging dir was not created by first call",
                file=sys.stderr,
            )
            sys.exit(1)

        # ── monkey-patch os.replace to observe the gap ──────────────
        original_replace = domain_knowledge.os.replace
        missing_detected = [False]

        def intercept_replace(src, dst):
            # At this point shutil.rmtree(target_dir) has already run,
            # so the target directory should be gone.
            if not os.path.exists(dst):
                missing_detected[0] = True
            # The real os.replace is fast — widen the observation
            # window slightly so the race is unconditionally visible.
            # (Without this the gap is a single Python bytecode
            # boundary and may be missed by a concurrent reader;
            # the sleep simulates what a real concurrent reader would
            # observe in a multi-process or preemptive scenario.)
            import time
            time.sleep(0.05)
            return original_replace(src, dst)

        domain_knowledge.os.replace = intercept_replace

        # ── trigger the non-atomic replacement (call 2) ─────────────
        _result = domain_knowledge.stage_domain_knowledge_files(
            proj_dir, work_dir, [md2]
        )

        # ── report ──────────────────────────────────────────────────
        if missing_detected[0]:
            print(
                "CONFIRMED — directory missing between rmtree and os.replace;"
                " spec requires 'atomically swapped' but code creates a"
                " window where the staging directory does not exist."
            )
        else:
            print(
                "NOT CONFIRMED — directory still existed when os.replace was"
                " called (unexpected)"
            )

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(proj_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — directory missing between rmtree and os.replace; spec requires 'atomically swapped' but code creates a window where the staging directory does not exist.
```
