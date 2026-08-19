# Bug Report: collect_relevent_function_scope

**Source file:** `src/incremental_reasoner-py/collect_relevent_function_scope.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of unique extracted-function file paths, each expressed relative to the extracted_functions directory with '/' separators, and each denoting an existing extracted function file whose behavior is judged relevant to developer_intent. Relevance scope guarantee: the candidate space is narrowed from the modules of the phase plan by intent-relevance judgments at module, file, and function granularity, and every module containing a changed source file participates regardless of the module-level judgment, and every changed source file inside a participating module participates regardless of the file-level judgment, so the changed scope is never dropped. Any source file inside a participating module for which no function relevance ranking can be produced contributes all of its extracted function files at a neutral lowest score instead of being dropped. Ranking guarantee: every returned path carries a relevance score derived from intent-signal scoring (heuristic multi-tier signal matching with call-graph and class-scope enrichments, and LLM re-ranking where triggered); the list is sorted by descending score with the path as a deterministic tie-breaker, so every entry is at least as relevant as all entries after it, and every unscored fallback entry sorts after every scored entry. Truncation guarantee: when range is not None, only the first range entries of the sorted list are returned; when range is None, all selected entries are returned. The return value is an empty list when the phase plan contains no modules, when no module is judged relevant and no module contains a changed file, or when no participating file contributes any extracted function file. Selection failures never raise; a failed or invalid module selection behaves as an empty selection, a failed file selection falls back to the full file list of that module, and paths returned by selections that do not belong to the module's source files are ignored. The function does not modify any source file; its only writes are scope-selection artifacts under proj_dir/fm_agent.

---

### Actual Behavior

Upon successful return, the function yields a list of strings representing extracted-function file paths relative to proj_dir/fm_agent/extracted_functions, ordered by descending relevance score with respect to developer_intent, and truncated to at most `range` entries when `range` is not None (all entries returned when `range` is None). The list is empty if and only if (a) phases.json contained no modules across any phase, (b) the LLM module-selection pass returned None or selected no modules, (c) the opencode file-selection pass returned None or selected no files, or (d) the function-ranking pass produced no scored functions for any selected file. When non-empty, every element is a path that resolves to an existing file under proj_dir/fm_agent/extracted_functions and corresponds to a function located in a source file that belongs to a module selected in pass 1, a file selected in pass 2, and a function ranked in pass 3. The set of candidate source files considered in pass 3 is the intersection of files chosen by the opencode agent and the keys of changed_functions (expressed as project-relative paths). No element appears more than once. The function does not modify any source file, phases.json, or the extracted_functions directory. Formal specification: LET work_dir = proj_dir/fm_agent, extracted_dir = work_dir/extracted_functions, phases_data = parse(work_dir/phases.json), modules = flatten([(p.phase, m) for p in phases_data.phases for m in p.modules]). IF modules =  THEN return = []. ELSE LET selected_modules = _llm_select_json() validated by _validate_module_selection, selected_files = union of _opencode_select_json results per selected module, ranked_funcs = union of rank_functions_in_file(f, ) for f in selected_files  changed_source_rels, result_paths = map each ranked function to its extracted-function file path under extracted_dir via _extracted_func_dir and _extracted_files_by_method. return = result_paths[:range] if range is not None else result_paths, sorted by descending score. EXCEPTIONS: If work_dir/phases.json is missing, unreadable, or not valid JSON, _load_phases raises (OSError, json.JSONDecodeError, or equivalent) and the exception propagates uncaught. LLM and agent failures (returning None) do not raise; they cause the corresponding pass to contribute an empty selection, ultimately yielding []. The structured trace under work_dir records all LLM and agent exchanges. No filesystem mutation occurs outside trace logging.

---

## Code Evidence

Line 35: changed_source_rels = {
Line 36:     os.path.relpath(abs_src, proj_dir).replace(os.sep, "/")
Line 37:     for abs_src in changed_functions
Line 38: }

---

## Trigger Condition

Condition B requires that 'every changed source file inside a participating module participates regardless of the file-level judgment, so the changed scope is never dropped' and that 'a failed file selection falls back to the full file list of that module.' Condition A instead computes the pass-3 candidate set as the intersection of opencode-selected files and changed_source_rels (lines 35-38 build changed_source_rels, which is then intersected with the opencode result). When the opencode agent omits a changed file from its selection, the intersection drops it, violating the guarantee that changed files are never excluded. Additionally, condition B requires every module containing a changed source file to participate regardless of the LLM module-level judgment, but condition A only considers modules selected by the LLM in pass 1, with no override for modules containing changed files.

---

## How to trigger the bug

The reported gap claims that `collect_relevent_function_scope` computes its pass-3
candidate set as the *intersection* of the opencode-selected files and the changed
source files (so a changed file the opencode agent omits is dropped), and that
modules are only considered when the LLM selected them in pass 1 (no override for
modules containing changed files).

Reading the actual source (`src/incremental_reasoner.py`, function
`collect_relevent_function_scope`) shows the opposite structure:

- Pass 1 builds `relevant_modules` with an explicit override: a module participates
  if the LLM selected it **or** any of its `source_files` is a changed source file
  (`or any(sf.replace("\\", "/") in changed_source_rels ...)`).
- Pass 2 force-adds every changed file of a participating module to `chosen` when
  the opencode selection omitted it (`for sf in changed_in_module: if sf not in
  chosen: chosen.append(sf)`), and falls back to the module's full file list when
  the selection fails (`chosen = list(source_files)`).
- Pass 3 iterates `filtered_modules` directly; there is no intersection with
  `changed_source_rels`, which is used only for the two inclusion overrides above.

The probe attempted to reproduce the reported behavior by driving the real function
(in a fresh temporary fixture project, LLM/opencode boundaries mocked, no FM-Agent
workflow started) through the exact trigger conditions:

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Fresh `tempfile.mkdtemp()` fixture with `fm_agent/phases.json`, sources, extracted-function files |
| `developer_intent` | `"fix the helper logic that formats values"` |
| `changed_functions` | `{"<proj_dir>/src/helper.py": {"modified": ["x"]}}` (changed file: `src/helper.py`) |
| `range` | `None` |
| phases.json (S1) | module `core` with `source_files: ["src/app.py", "src/helper.py"]` |
| phases.json (S2/S3) | modules `core` (`["src/app.py"]`) and `util` (`["src/helper.py"]`) |
| Pass-1 LLM mock (S1) | `[{"phase": 1, "name": "core"}]` |
| Pass-1 LLM mock (S2) | `[]` (LLM selects nothing) |
| Pass-1 LLM mock (S3) | `[{"phase": 1, "name": "core"}]` (module `util` NOT selected) |
| Pass-2 opencode mock (S1) | `["src/app.py"]` — omits the changed file `src/helper.py` |
| Pass-2 opencode mock (S2) | `None` — selection failure, full-list fallback required |
| Pass-2 opencode mock (S3) | `["src/app.py"]` — omits the changed file in the override-participating module |
| Pass-3 ranker | Mocked deterministic ranking (attempts 1, 3); real `scope.rank_functions_in_file` heuristic ranker (attempt 2) |

### Expected (spec-correct) Output

`['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py']` (S1/S3 — the changed file
`src/helper.py` participates regardless of the file-level and module-level
judgments) / `['src/helper-py/helper_fn.py']` (S2).

### Actual (buggy) Output

The same list as the spec-correct output — the changed file's extracted-function
files were returned in all three scenarios:

`['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py']` (S1, attempt 1),
`['src/helper-py/helper_fn.py']` (S2),
`['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py']` (S3).

Because the actual output matches the spec-correct output, the reported drop of the
changed scope did not occur and the bug is **not confirmed**.

### How to Reproduce

Step-by-step instructions to verify manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point `src.incremental_reasoner`;
   the LLM/opencode selection boundaries are mocked so no network or FM-Agent
   workflow is involved):

```python
import contextlib, io, json, os, sys, tempfile
import src.incremental_reasoner as ir

proj = tempfile.mkdtemp(prefix="scope_demo_")
os.makedirs(os.path.join(proj, "fm_agent"))
json.dump({"phases": [{"phase": 1, "modules": [
    {"name": "core", "description": "Core application logic",
      "source_files": ["src/app.py", "src/helper.py"]}]}]},
    open(os.path.join(proj, "fm_agent", "phases.json"), "w"))
for rel, body in {"src/app.py": "def app_fn(): return 1",
                   "src/helper.py": "def helper_fn(): return 2"}.items():
    p = os.path.join(proj, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(body)
ext = os.path.join(proj, "fm_agent", "extracted_functions")
for d, fn in (("src/app-py", "app_fn.py"), ("src/helper-py", "helper_fn.py")):
    os.makedirs(os.path.join(ext, d), exist_ok=True)
    open(os.path.join(ext, d, fn), "w").write("# stub")

ir._llm_select_json = lambda *a, **k: [{"phase": 1, "name": "core"}]
ir._opencode_select_json = lambda *a, **k: ["src/app.py"]  # omits changed helper.py
ir.rank_functions_in_file = lambda filepath=None, **k: [
    {"name": ("app_fn" if "app" in filepath else "helper_fn"), "score": 0.5}]

with contextlib.redirect_stdout(io.StringIO()):
    result = ir.collect_relevent_function_scope(
        proj, "fix the helper logic that formats values",
        {os.path.join(proj, "src/helper.py"): {"modified": ["helper_fn"]}}, None)
print(result)
# actual output: ['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py']
# expected (correct) output: ['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py']
# (the buggy output claimed in the report would have been ['src/app-py/app_fn.py'],
#  i.e. the changed file dropped — this did not occur)
```

---

## Probe Script

```py
#!/usr/bin/env python3
"""Probe for bug id: src--incremental_reasoner-py--collect_relevent_function_scope

Spec claim under test (from the verification gaps):
  * "every module containing a changed source file participates regardless of the
     module-level judgment"
  * "every changed source file inside a participating module participates regardless
     of the file-level judgment, so the changed scope is never dropped"
  * "a failed file selection falls back to the full file list of that module"

Reported (buggy) behavior: the pass-3 candidate set is the intersection of the
opencode-selected files and changed_source_rels, so a changed file omitted by the
opencode file-selection agent is dropped; and modules are only considered when the
LLM selected them in pass 1 (no override for modules containing changed files).

The probe drives collect_relevent_function_scope through three scenarios in a fresh
temporary fixture project (never the active repo) with the LLM/opencode selection
boundaries mocked (no network, no OpenCode, no FM-Agent workflow):

  S1 file-level guarantee: opencode's file selection omits a changed file that
     belongs to an LLM-selected module -> the changed file's extracted functions
     must still be returned.
  S2 module-level guarantee (LLM selects nothing): the LLM module selection is
     empty, but a module contains a changed file -> that module must still
     participate; opencode file selection fails (None) -> full file-list fallback.
  S3 module-level guarantee (LLM picks another module): the LLM selects only an
     unrelated module; the module holding the changed file must still participate.

Pass criterion: if in ANY scenario the extracted-function files of a changed source
file are missing from the returned list, the spec guarantee is violated and the bug
is CONFIRMED. If every changed file always participates, NOT CONFIRMED.

With --real-rank the probe additionally drops the rank_functions_in_file mock and
runs the real heuristic ranker from scope.py (still LLM-free, llm_client=None) to
rule out any artifact of the ranking mock.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTENT = "fix the helper logic that formats values"


def _bootstrap_deps():
    """Re-exec under the repo venv if the project's deps are unavailable here."""
    try:
        import dotenv  # noqa: F401
        import pydantic_settings  # noqa: F401
    except ImportError:
        venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python")
        if os.path.exists(venv_py) and os.path.abspath(sys.executable) != os.path.abspath(venv_py):
            os.execv(venv_py, [venv_py, os.path.abspath(__file__)] + sys.argv[1:])
        raise


_bootstrap_deps()
sys.path.insert(0, REPO_ROOT)

import src.incremental_reasoner as ir  # noqa: E402

REAL_RANK = "--real-rank" in sys.argv


def build_fixture(modules):
    """Create a throwaway project dir with phases.json, sources, extracted files."""
    proj = tempfile.mkdtemp(prefix="fm_probe_collect_scope_")
    os.makedirs(os.path.join(proj, "fm_agent"))
    with open(os.path.join(proj, "fm_agent", "phases.json"), "w") as f:
        json.dump({"phases": [{"phase": 1, "modules": modules}]}, f)

    sources = {
        "src/app.py": "def app_fn():\n    return 1\n",
        "src/helper.py": "def helper_fn():\n    return 2\n",
    }
    for rel, body in sources.items():
        path = os.path.join(proj, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(body)

    ext_base = os.path.join(proj, "fm_agent", "extracted_functions")
    extracted_rel = {}
    for src_rel, fname in (("src/app.py", "app_fn"), ("src/helper.py", "helper_fn")):
        src_dir = os.path.dirname(src_rel)
        base = os.path.basename(src_rel)
        dot = base.rfind(".")
        dir_name = base[:dot] + "-" + base[dot + 1:]
        ext = base[dot + 1:]
        func_dir = os.path.join(ext_base, src_dir, dir_name)
        os.makedirs(func_dir, exist_ok=True)
        fpath = os.path.join(func_dir, fname + "." + ext)
        with open(fpath, "w") as f:
            f.write("# extracted function stub\n")
        extracted_rel[src_rel] = os.path.relpath(fpath, ext_base).replace(os.sep, "/")
    return proj, extracted_rel


def run_case(name, modules, changed_rels, llm_ret, oc_ret, expect_changed):
    """Run collect_relevent_function_scope in one fixture scenario.

    Returns (holds, result, missing) where holds is True iff every changed source
    file's extracted-function file is present in the returned list.
    """
    proj, extracted_rel = build_fixture(modules)
    changed = {
        os.path.join(proj, rel): {"modified": ["x"]} for rel in changed_rels
    }

    ranked_map = {
        "src/app.py": [{"name": "app_fn", "score": 0.9}],
        "src/helper.py": [{"name": "helper_fn", "score": 0.5}],
    }

    def fake_llm(*args, **kwargs):
        return llm_ret

    def fake_oc(proj_dir, work_dir, prompt_relpath, prompt_content,
                result_relpath, stage=None, input_files=None, **kwargs):
        return oc_ret

    def fake_rank(filepath=None, src_path=None, issue=None, signals=None, **kwargs):
        return [dict(e) for e in ranked_map.get(filepath, [])]

    orig = (ir._llm_select_json, ir._opencode_select_json, ir.rank_functions_in_file)
    ir._llm_select_json = fake_llm
    ir._opencode_select_json = fake_oc
    if not REAL_RANK:
        ir.rank_functions_in_file = fake_rank
    try:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            result = ir.collect_relevent_function_scope(proj, INTENT, changed, None)
    finally:
        ir._llm_select_json, ir._opencode_select_json, ir.rank_functions_in_file = orig
        shutil.rmtree(proj, ignore_errors=True)

    missing = [
        extracted_rel[rel] for rel in expect_changed
        if extracted_rel[rel] not in result
    ]
    holds = not missing
    print(
        "[%s] changed-file participation %s | returned=%r | missing=%r"
        % (name, "HOLDS" if holds else "VIOLATED", result, missing)
    )
    return holds, result, missing


def main():
    results = []

    # S1: file-level guarantee. LLM selects module `core`; opencode's file
    # selection omits the changed file src/helper.py.
    results.append(run_case(
        "S1 file-level: opencode omits changed file",
        modules=[{
            "name": "core",
            "description": "Core application logic",
            "source_files": ["src/app.py", "src/helper.py"],
        }],
        changed_rels=["src/helper.py"],
        llm_ret=[{"phase": 1, "name": "core"}],
        oc_ret=["src/app.py"],          # changed file omitted by opencode
        expect_changed=["src/helper.py"],
    ))

    # S2: module-level guarantee with an empty LLM selection; opencode fails
    # (None) so the spec requires the full module file list as fallback.
    results.append(run_case(
        "S2 module-level: LLM selects nothing, file selection fails",
        modules=[
            {"name": "core", "description": "Core application logic",
             "source_files": ["src/app.py"]},
            {"name": "util", "description": "Unrelated utilities",
             "source_files": ["src/helper.py"]},
        ],
        changed_rels=["src/helper.py"],
        llm_ret=[],                     # LLM judges nothing relevant
        oc_ret=None,                    # opencode failure -> full file list
        expect_changed=["src/helper.py"],
    ))

    # S3: module-level guarantee with the LLM selecting only another module,
    # AND opencode succeeding in file selection while omitting the changed
    # file from the override-participating module (both overrides chained).
    results.append(run_case(
        "S3 module-level + file-level: LLM selects only the unrelated module, "
        "opencode omits the changed file",
        modules=[
            {"name": "core", "description": "Core application logic",
             "source_files": ["src/app.py"]},
            {"name": "util", "description": "Unrelated utilities",
             "source_files": ["src/helper.py"]},
        ],
        changed_rels=["src/helper.py"],
        llm_ret=[{"phase": 1, "name": "core"}],   # `util` NOT selected
        oc_ret=["src/app.py"],          # omits src/helper.py for module `util`
        expect_changed=["src/helper.py"],
    ))

    violated = [name for name, (holds, _r, _m) in
                zip(("S1", "S2", "S3"), results) if not holds]
    if violated:
        print("CONFIRMED - changed-scope guarantee violated in: %s" % ", ".join(violated))
        return 0
    print("NOT CONFIRMED - every changed source file participated in all scenarios "
          "(module- and file-level overrides are present in the current code)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print("ERROR: %s: %s" % (type(exc).__name__, exc))
        sys.exit(1)

```

### Probe Output

```
[S1 file-level: opencode omits changed file] changed-file participation HOLDS | returned=['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py'] | missing=[]
[S2 module-level: LLM selects nothing, file selection fails] changed-file participation HOLDS | returned=['src/helper-py/helper_fn.py'] | missing=[]
[S3 module-level + file-level: LLM selects only the unrelated module, opencode omits the changed file] changed-file participation HOLDS | returned=['src/app-py/app_fn.py', 'src/helper-py/helper_fn.py'] | missing=[]
NOT CONFIRMED - every changed source file participated in all scenarios (module- and file-level overrides are present in the current code)
```
