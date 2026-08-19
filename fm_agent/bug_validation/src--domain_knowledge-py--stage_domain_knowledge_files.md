# Bug Report: stage_domain_knowledge_files

**Source file:** `/tmp/fm_agent_wt_FM-Agent_l5vkw0lv/snapshot/fm_agent/extracted_functions/src/domain_knowledge-py/stage_domain_knowledge_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of strings sorted in ascending order whose elements are exactly the project-relative paths of the staged user-knowledge Markdown files under work_dir, written with '/' separators and prefixed 'fm_agent/'; the staging manifest and any non-Markdown file never appear in the result. When markdown_paths is falsy the function performs no filesystem mutation at all and returns the previously staged Markdown files unchanged ([] if the staging directory does not exist). When markdown_paths is non-empty, after return the staging directory contains exactly one copy per distinct requested source file (requested entries resolving to the same canonical file count once), one staging manifest in JSON form holding a 'files' array with one entry per staged file mapping that file's absolute source path to its project-relative staged path, and nothing else. The replacement of the staging directory is atomic: any observer sees either the complete previous file set or the complete new file set, never a mix. Staged file names are mutually distinct across the directory, filesystem-safe, and carry the source file's extension lower-cased. Raises ValueError, before staging any file, when any requested entry resolves to a path that does not exist, is not a regular file, or has a non-Markdown extension; a raised validation error leaves no partially staged directory behind.

---

### Actual Behavior

The function terminates via one of the following mutually exclusive outcomes:

**Path A  Early return (markdown_paths is falsy):**
No filesystem mutation occurs. The return value equals list_staged_domain_knowledge_relpaths(work_dir): a possibly-empty list of project-relative '/'-separated path strings (prefixed 'fm_agent/') naming the Markdown files currently present in the staging directory under work_dir, in ascending sorted order, excluding the manifest and non-Markdown files. If the staging directory does not exist, the return value is [].

**Path B  ValueError propagation:**
If resolve_domain_knowledge_paths raises ValueError (because some entry in markdown_paths resolves to a nonexistent path, a non-regular file, or a non-Markdown extension), that ValueError propagates unchanged. No staging directory is created or modified; any pre-existing staging directory and its contents remain untouched. The temporary directory (target_dir + '.tmp') may or may not exist depending on when the exception occurred, but no atomic replacement has taken place.

**Path C  OS/IO exception during filesystem operations:**
If any of os.makedirs, shutil.rmtree, shutil.copy2, open/json.dump, or os.replace raises OSError (or a subclass such as PermissionError, FileNotFoundError, IsADirectoryError), that exception propagates. The pre-existing staging directory at os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR) may have been removed (line 36) without replacement if the exception occurred between lines 36 and 37; otherwise it remains intact. The temporary directory may exist in a partially-populated state. No partial manifest is guaranteed to be valid.

**Path D  Normal completion (markdown_paths is truthy and all operations succeed):**
Let resolved = resolve_domain_knowledge_paths(markdown_paths, base_dir=proj_dir, fallback_base_dir=os.getcwd()), which is a list of absolute paths to existing regular Markdown files with no duplicates.

1. The directory target_dir := os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR) exists and contains exactly len(resolved) Markdown files plus one manifest file named USER_KNOWLEDGE_MANIFEST. No other files or subdirectories are present.
2. Each resolved source file has been copied (preserving metadata via copy2) into target_dir under a filesystem-safe name produced by _safe_staged_name; all staged file names within target_dir are mutually distinct.
3. The manifest file is a valid UTF-8 JSON document of the form {"files": entries} where entries is a list of len(resolved) objects, each with keys "source_path" (the absolute source path) and "staged_path" (the string "fm_agent/<USER_KNOWLEDGE_REL_DIR>/<target_name>" with '/' separators), in the same order as resolved.
4. The temporary directory (target_dir + '.tmp') no longer exists (it was atomically renamed to target_dir via os.replace).
5. The parent directory of target_dir (i.e., work_dir) exists.
6. The return value equals list_staged_domain_knowledge_relpaths(work_dir): a list of project-relative '/'-separated path strings naming the staged Markdown files in ascending sorted order, excluding the manifest. The list has exactly len(resolved) elements.
7. All pre-existing contents of the former staging directory (if any) have been irreversibly removed and replaced by the new staging content.

Formally, for Path D:
   i  [0, len(resolved)): ! f_i  target_dir such that f_i is a regular file, f_i is the copy of resolved[i], and name(f_i) = _safe_staged_name(resolved[i], used_names_at_step_i).
  files_in(target_dir) = {f_0, , f_{n-1}}  {USER_KNOWLEDGE_MANIFEST} where n = len(resolved).
  return_value = sorted(["fm_agent/" + USER_KNOWLEDGE_REL_DIR + "/" + name(f_i) for i in range(n) if is_markdown(f_i)]).
  exists(target_dir + ".tmp").

---

## Code Evidence

Line 36: shutil.rmtree(target_dir, ignore_errors=True)
Line 37: os.replace(tmp_dir, target_dir)

(In the full implementation file `src/domain_knowledge.py`, these are lines 169–170.)

---

## Trigger Condition

The specification requires: 'The replacement of the staging directory is atomic: any observer sees either the complete previous file set or the complete new file set, never a mix.' The code implements the replacement as two separate operations: first shutil.rmtree(target_dir) removes the existing staging directory, then os.replace(tmp_dir, target_dir) renames the temporary directory into place. Between these two system calls the staging directory does not exist, so a concurrent observer sees neither the old nor the new file set. This is not a mix, but it is also neither 'the complete previous file set' nor 'the complete new file set', violating the explicit either/or guarantee. An atomic swap (e.g., via a symlink indirection or rename-over-empty-directory pattern) would be needed to satisfy the specification.

---

## How to trigger the bug

The probe seeds the staging directory under a fresh temporary `work_dir` with a complete previous file set (`old_notes.md`), then calls `stage_domain_knowledge_files()` through the public package import (`from src.domain_knowledge import ...`, exactly as `main.py` imports it) with one new Markdown source file. A spy wraps `os.replace` and records the state of the staging directory at the exact moment the final swap call is invoked, holding the window open briefly, while a concurrent observer thread continuously lists the staging directory before, during, and after the call.

Because the code removes the staging directory with `shutil.rmtree(target_dir)` *before* renaming the new directory into place with `os.replace(tmp_dir, target_dir)`, the staging directory does not exist at swap time: the probe observed `pre_swap_target_exists=False`, and the concurrent observer collected 240 samples (out of 241 total) that were neither the complete old set `['old_notes.md']` nor the complete new set `['manifest.json', 'new_notes.md']` — the directory was simply absent. A spec-compliant atomic swap would keep the target observable with one of the two complete sets at every instant.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Fresh empty temp dir (used only as `base_dir` for path resolution) |
| `work_dir` | Fresh temp dir containing a pre-staged set: `spec_prompts/domain_context/user_knowledge/old_notes.md` |
| `markdown_paths` | `[<temp>/new_notes.md]` — absolute path of a new Markdown file containing `"new knowledge"` |

### Expected (spec-correct) Output

The call returns `['fm_agent/spec_prompts/domain_context/user_knowledge/new_notes.md']`, and during the replacement the staging directory is always present containing either the complete previous file set (`['old_notes.md']`) or the complete new file set (`['manifest.json', 'new_notes.md']`) — at swap time the target still exists (atomic swap), and every observer sample is one of those two complete sets.

### Actual (buggy) Output

The return value is correct (`['fm_agent/spec_prompts/domain_context/user_knowledge/new_notes.md']`) and the final directory contents are correct, but the replacement itself is not atomic: at the instant `os.replace` is invoked the staging directory no longer exists (`pre_swap_target_exists=False`, `pre_swap_listing=None`), and 240 of 241 concurrent observer samples saw neither the old nor the new file set (the directory was absent), violating the either/or guarantee.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile, threading, time
sys.path.insert(0, os.getcwd())
from src.domain_knowledge import USER_KNOWLEDGE_REL_DIR, stage_domain_knowledge_files

work = tempfile.mkdtemp()
proj_dir = os.path.join(work, "proj"); os.makedirs(proj_dir)
work_dir = os.path.join(work, "fm_agent_work")
staging = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR); os.makedirs(staging)
open(os.path.join(staging, "old_notes.md"), "w").write("previous knowledge")  # previous set
new_src = os.path.join(work, "new_notes.md")
open(new_src, "w").write("new knowledge")

obs, real_replace = [], os.replace
def spy(src, dst, *a, **k):           # hold the swap window open, record target state
    obs.append(os.path.exists(dst))
    time.sleep(0.5)
    return real_replace(src, dst, *a, **k)
os.replace = spy
try:
    ret = stage_domain_knowledge_files(proj_dir, work_dir, [new_src])
finally:
    os.replace = real_replace
print(os.path.exists(staging) if obs else None, ret)
// actual (buggy) output: False ['fm_agent/spec_prompts/domain_context/user_knowledge/new_notes.md']
//   -> staging dir absent at swap time: observers see neither the old nor the new set
// expected (correct) output: True ['fm_agent/spec_prompts/domain_context/user_knowledge/new_notes.md']
//   -> target present at swap time; every instant shows a complete old or new set
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for bug src--domain_knowledge-py--stage_domain_knowledge_files.

Bug claim: stage_domain_knowledge_files() must replace the staging directory
atomically: any observer sees either the complete previous file set or the
complete new file set, never a mix (and never neither). The implementation
does a two-step swap:

    shutil.rmtree(target_dir, ignore_errors=True)   # old set gone
    os.replace(tmp_dir, target_dir)                 # new set appears

Between those two calls the staging directory does not exist at all, so an
observer sampling it in that window sees neither the old nor the new set.

Probe strategy (deterministic, no timing race):
  1. Seed the staging dir in a fresh temp work_dir with a previous file set
     (old_notes.md), then call stage_domain_knowledge_files() with a new
     markdown source via the public package import used by main.py.
  2. A spy wraps os.replace: at the very moment the swap call is invoked it
     records whether target_dir exists; it then holds the window open briefly.
  3. A concurrent observer thread continuously lists the staging dir before,
     during, and after the call.
  4. Spec-correct => every observation is either the complete old set or the
     complete new set, and target_dir still exists at swap time.
     Buggy => target_dir is absent at swap time / observer sees neither set.

Self-contained: no network, no test framework; all fixtures live in fresh
temporary directories that are removed at the end. Does NOT start any
FM-Agent workflow; only the single function under test is exercised.
"""

import os
import shutil
import sys
import tempfile
import threading
import time

# Repo root = two level-ups from fm_agent/bug_validation/. Put it on sys.path
# so the package entry-point import used by main.py resolves when this probe
# is run from the repo root.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

OLD_NAME = "old_notes.md"
NEW_NAME = "new_notes.md"
WINDOW_SECONDS = 0.5


def main():
    from src.domain_knowledge import (  # public import, as used by main.py
        USER_KNOWLEDGE_MANIFEST,
        USER_KNOWLEDGE_REL_DIR,
        stage_domain_knowledge_files,
    )

    work = tempfile.mkdtemp(prefix="probe_stage_dk_")
    old_replace = os.replace
    observations = {}
    samples = []
    stop = threading.Event()

    proj_dir = os.path.join(work, "proj")
    work_dir = os.path.join(work, "fm_agent_work")
    staging = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    new_src = os.path.join(work, NEW_NAME)

    def observer():
        while not stop.is_set():
            try:
                sample = sorted(os.listdir(staging)) if os.path.isdir(staging) else None
            except OSError:
                sample = None
            samples.append(sample)
            time.sleep(0.002)

    obs_thread = threading.Thread(target=observer, daemon=True)

    try:
        os.makedirs(proj_dir)
        # Complete previous file set already staged.
        os.makedirs(staging)
        with open(os.path.join(staging, OLD_NAME), "w", encoding="utf-8") as f:
            f.write("previous knowledge")
        pre_call_listing = sorted(os.listdir(staging))

        with open(new_src, "w", encoding="utf-8") as f:
            f.write("new knowledge")

        old_set = [OLD_NAME]
        new_set = sorted([NEW_NAME, USER_KNOWLEDGE_MANIFEST])

        def spy_replace(src, dst, *args, **kwargs):
            if os.path.abspath(dst) == os.path.abspath(staging):
                observations["swap_seen"] = True
                observations["pre_swap_target_exists"] = os.path.exists(dst)
                observations["pre_swap_listing"] = (
                    sorted(os.listdir(dst)) if os.path.isdir(dst) else None
                )
                # Hold the window open so the concurrent observer can sample it.
                time.sleep(WINDOW_SECONDS)
            return old_replace(src, dst, *args, **kwargs)

        os.replace = spy_replace
        obs_thread.start()
        try:
            returned = stage_domain_knowledge_files(proj_dir, work_dir, [new_src])
        finally:
            os.replace = old_replace
            stop.set()
        obs_thread.join(timeout=5)

        post_call_listing = sorted(os.listdir(staging)) if os.path.isdir(staging) else None
        expected_return = [
            "fm_agent/" + USER_KNOWLEDGE_REL_DIR.replace(os.sep, "/") + "/" + NEW_NAME
        ]

        # Sanity: the call must have actually staged the new set end-to-end,
        # otherwise the observation would be meaningless.
        staged_ok = (
            pre_call_listing == old_set
            and post_call_listing == new_set
            and returned == expected_return
            and observations.get("swap_seen") is True
        )

        # Spec-correct behavior: target still present at swap time (atomic
        # swap over the live directory), and EVERY observer sample is either
        # the complete old set or the complete new set.
        bad_samples = [s for s in samples if s != old_set and s != new_set]
        atomic = (
            staged_ok
            and observations.get("pre_swap_target_exists") is True
            and not bad_samples
        )

        detail = (
            f"pre_call={pre_call_listing!r} "
            f"pre_swap_exists={observations.get('pre_swap_target_exists')!r} "
            f"pre_swap_listing={observations.get('pre_swap_listing')!r} "
            f"post_call={post_call_listing!r} "
            f"neither_old_nor_new_samples={len(bad_samples)} "
            f"total_samples={len(samples)}"
        )
        if not staged_ok:
            print(f"ERROR: staging path did not complete as expected; {detail}")
            sys.exit(1)

        if not atomic:
            print(
                "CONFIRMED — staging dir absent during swap window; observer saw "
                f"neither the old nor the new file set | {detail} | "
                "expected: target present at swap time and every sample in "
                f"{{{old_set!r}, {new_set!r}}}"
            )
        else:
            print(f"NOT CONFIRMED — replacement observed as atomic | {detail}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        os.replace = old_replace
        stop.set()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — staging dir absent during swap window; observer saw neither the old nor the new file set | pre_call=['old_notes.md'] pre_swap_exists=False pre_swap_listing=None post_call=['manifest.json', 'new_notes.md'] neither_old_nor_new_samples=240 total_samples=241 | expected: target present at swap time and every sample in {['old_notes.md'], ['manifest.json', 'new_notes.md']}
```
