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
