# Bug Report: _run_generate_phases

**Source file:** `src/pipeline_setup-py/_run_generate_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None. All effects are confined to files under work_dir (plus whatever a delegated or post-processing plugin command itself does); no file under proj_dir is created or modified. The same governing plugin-hook rule as every setup stage runner applies: a skip hook returns immediately without producing phases.json and no completeness guarantee applies on that path; a replace hook leaves phase-plan generation entirely to the plugin's replacement command and returns only after that command completes successfully; a modify hook runs the built-in flow with the plugin-supplied workflow and, when the hook declares a post-processing command, runs that command after the generation loop; when plugin_stage is None the built-in flow runs. In the built-in flow: a workflow file named workflow_generate_phases.md is staged inside work_dir before any agent invocation, specialized to the concrete project root so that source_files entries are required to be paths relative to the project root without a project-directory-name prefix, and including an appended section listing the user-provided domain-knowledge files when any are staged. When resume=True and the existing phases.json already satisfies the phase-plan schema, no agent invocation takes place and the existing phases.json is preserved unchanged. Otherwise a setup LLM agent is invoked with a prompt directing it to follow the staged workflow and carrying the standing constraints that fm_agent/ is an output-only workspace, phases.json must never list paths inside fm_agent/, and no project file may be modified; when submodules is given the prompt restricts the plan to source files under those directories; when is_incremental the prompt requires updating the existing phases.json in place  adding entries for new files, removing entries whose files no longer exist, and preserving still-accurate entries; when the existing phases.json fails schema validation the prompt includes every outstanding schema violation to repair and forbids satisfying the schema by using an empty source_files array unless the module genuinely owns no files. A candidate plan is accepted only when it satisfies the phase-plan schema and, additionally, when submodules was given it covers the current source files under those directories (every current in-scope non-test source file is listed, no listed file lies outside the directories, and no listed file is absent from disk), and when is_incremental phases.json was either rewritten during this invocation or covers the project's current source tree; in full mode schema validity alone suffices for acceptance. Unaccepted attempts are retried up to OPENCODE_MAX_RETRIES times with a fixed 10-second delay between attempts, and each attempt is recorded as a trace event under stage 'generate_phases_json' declaring the staged workflow and any staged user-knowledge files as inputs and phases.json as the declared output. A return not taken via the skip hook guarantees that work_dir/phases.json exists, is valid JSON satisfying the phase-plan schema, and is ready for the caller's post-processing  including the submodule-coverage and incremental-update properties above when the corresponding run mode was requested. If no acceptable plan can be produced within the retry budget, the process terminates with exit code 1.

---

### Actual Behavior

The function _run_generate_phases terminates via one of the following mutually exclusive paths:

**Path A  Plugin 'pass' (early return):** If plugin_stage is not None and plugin_stage.type == 'pass', the function prints a skip diagnostic and returns None immediately. No filesystem mutations occur; phases.json (if previously present in work_dir) is untouched.

**Path B  Plugin 'replace' (early return or exception):** If plugin_stage is not None and plugin_stage.type == 'replace', the function prints a diagnostic and invokes run_plugin_command(plugin_stage.replace_cmd, plugin_root, proj_dir, label='generate_phase_plan'). If the plugin command exits with code 0, the function returns None; the plugin command is solely responsible for producing or updating work_dir/phases.json. If the plugin command exits non-zero, a subprocess-related exception propagates and the function does not return normally.

**Path C  Normal / 'modify' flow (code continues past line 14):** Reached when plugin_stage is None, or plugin_stage.type is neither 'pass' nor 'replace'. The following local state is established:
   phases_json == os.path.join(work_dir, 'phases.json').
   prev_mtime is the float mtime of phases_json if the file existed at entry, else None.
   phase_plan_errors is the list returned by _phase_plan_schema_errors(phases_json) when the file existed, else the empty list [].
   _resume_skip is True iff (resume is True) AND _phase_plan_complete(work_dir) returned True; otherwise False.
   If _resume_skip is True, a RESUME diagnostic is printed but execution does NOT return; it falls through.
   If plugin_stage is not None AND plugin_stage.type == 'modify' AND plugin_stage.input_md is truthy:
       The file at plugin_root / plugin_stage.input_md is copied (preserving metadata via shutil.copy2) to work_dir/workflow_generate_phases.md.
       user_knowledge_paths is the sorted list of staged domain-knowledge relative paths under work_dir.
       If user_knowledge_paths is non-empty, the file work_dir/workflow_generate_phases.md is opened in append mode and a '## User-Provided Domain Knowledge' Markdown section is appended, containing instructional text and one bullet per entry from format_domain_knowledge_bullets(user_knowledge_paths). The file handle is closed after the append.
       If user_knowledge_paths is empty, workflow_generate_phases.md remains as copied with no appended section.
   If the 'modify' sub-condition is not met, no workflow file is written or modified by this visible portion.

**Invariants across all paths:**
   proj_dir, work_dir, script_dir, is_incremental, resume, submodules, plugin_stage, and plugin_root are not mutated.
   No exception is raised by the visible code itself except: (a) FileNotFoundError / OSError from os.path.getmtime, shutil.copy2, or open if the referenced paths are inaccessible; (b) the exception from run_plugin_command on Path B; (c) any exception from _phase_plan_schema_errors or _phase_plan_complete is NOT expected per their contracts (they return error lists / False rather than raising).
   The code block as shown is syntactically incomplete (the function body continues beyond line 40); the guarantees above cover only the statements visible through line 40. Subsequent statements in the full function may further mutate work_dir contents, invoke the LLM agent, or perform additional validation.

Formally:
  (plugin_stage  None  plugin_stage.type = 'pass')  RETURN(None)  filesystem_unchanged
  (plugin_stage  None  plugin_stage.type = 'replace')  (run_plugin_command succeeds  RETURN(None))  (run_plugin_command fails  RAISE)
  OTHERWISE  LET phases_json = work_dir  'phases.json' IN
    prev_mtime = ( phases_json ? mtime(phases_json) : None) 
    phase_plan_errors = ( phases_json ? _phase_plan_schema_errors(phases_json) : []) 
    _resume_skip = (resume  _phase_plan_complete(work_dir)) 
    (plugin_stage  None  plugin_stage.type = 'modify'  plugin_stage.input_md 
       work_dir/'workflow_generate_phases.md' 
      (user_knowledge_paths  []  file_contains_domain_knowledge_section(work_dir/'workflow_generate_phases.md')))

---

## Code Evidence

Line 27:         shutil.copy2(workflow_src, workflow_dst)

---

## Trigger Condition

The specification states that the modify hook 'runs the built-in flow with the plugin-supplied workflow' and that in the built-in flow the workflow file is 'specialized to the concrete project root so that source_files entries are required to be paths relative to the project root without a project-directory-name prefix' (as performed by _prepare_workflow_file for the default workflow). In the modify path the code copies the plugin-supplied Markdown to work_dir/workflow_generate_phases.md with a bare shutil.copy2 and then appends the domain-knowledge section, but never rewrites the source_files path instruction to reference the concrete proj_dir. The _prepare_workflow_file helper, whose post-condition explicitly performs this specialization, is not invoked nor is any equivalent rewriting applied. Consequently the staged workflow still contains the plugin author's generic placeholder rather than the project-specific path constraint required by the specification.

---

## How to trigger the bug

The probe builds a fresh throwaway project directory (`proj_dir`) containing a
schema-valid `fm_agent/phases.json`, then calls `_run_generate_phases` (imported
via the `src` package) with a plugin `modify` hook whose `input_md` workflow
still carries the generic repo-root `source_files` instruction. `resume=True`
plus the schema-valid `phases.json` takes the spec's own "no agent invocation"
resume path, so no LLM/OpenCode process is ever started and the function's
workflow-staging behavior is observable in isolation.

On the **modify** path (lines 929–946 of `src/pipeline_setup.py`) the plugin
markdown is copied with a bare `shutil.copy2` and the domain-knowledge section
is appended — but `_prepare_workflow_file` (which performs the project-root
specialization, lines 866–900) is never invoked. The staged
`work_dir/workflow_generate_phases.md` therefore still contains the plugin
author's generic placeholder instead of the instruction specialized to the
concrete project root. A control run of the same function with
`plugin_stage=None` (built-in flow) proves the asymmetry: the staged workflow
there IS specialized to the concrete project root.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | fresh temp dir `.../fake_project` (contains `hello.py` and `fm_agent/`) |
| `work_dir` | `<proj_dir>/fm_agent` with pre-seeded schema-valid `phases.json` |
| `script_dir` | FM-Agent repo root |
| `is_incremental` | `False` |
| `resume` | `True` |
| `submodules` | `None` |
| `plugin_stage` | `PluginStageConfig(type='modify', input_md='custom_generate_phases.md')` |
| `plugin_root` | fresh temp dir containing `custom_generate_phases.md` with the generic line: '- `phases[*].modules[*].source_files` — relative paths from repo root of all source files that belong to this module.' |

### Expected (spec-correct) Output

Staged `work_dir/workflow_generate_phases.md` specialized to the concrete
project root — the generic repo-root instruction replaced exactly as the
built-in flow does, e.g. containing
``relative paths from the project root `<abspath(proj_dir)>` ...`` — so
`source_files` entries are required to be paths relative to the project root
without a project-directory-name prefix.

### Actual (buggy) Output

Staged `work_dir/workflow_generate_phases.md` is a byte-for-byte copy of the
plugin input (plus the domain-knowledge section when knowledge files are
staged): the generic placeholder '- `phases[*].modules[*].source_files` — relative paths from repo root of all source files that belong to this module.' is preserved, and the
concrete project root path never appears in the file.

### How to Reproduce

1. Navigate to the repo root.
2. Run the probe (it uses a fresh temp workspace and never starts an FM-Agent
   workflow; `resume=True` + valid `phases.json` is the spec's no-agent path):

```bash
python3 fm_agent/bug_validation/probe_src--pipeline_setup-py--_run_generate_phases.py
```

Minimal reproduction core (package entry point `src`):

```python
from pathlib import Path
from src.pipeline_setup import _run_generate_phases
from src.plugin import PluginStageConfig
import src.pipeline_setup as ps

ps.run_opencode_traced = lambda *a, **k: (_ for _ in ()).throw(
    RuntimeError("no agent launch allowed in probe"))

# proj_dir/work_dir: fresh temp dirs; work_dir/phases.json pre-seeded
# schema-valid so resume=True never invokes the agent.
_run_generate_phases(proj_dir, work_dir, REPO_ROOT, resume=True,
                     plugin_stage=PluginStageConfig(
                         type="modify", input_md="custom_generate_phases.md"),
                     plugin_root=Path(plugin_root))

staged = open(f"{work_dir}/workflow_generate_phases.md").read()
# actual (buggy) output: generic "repo root" instruction kept, proj_dir absent
# expected (correct) output: instruction rewritten to reference abspath(proj_dir)
assert PROJ_DIR_ABS not in staged  # buggy: True — specialization missing
```

---

## Probe Script

```python
"""Probe for bug `src--pipeline_setup-py--_run_generate_phases`.

Spec claim: in the built-in flow the staged workflow_generate_phases.md is
"specialized to the concrete project root" — and a 'modify' plugin hook "runs
the built-in flow with the plugin-supplied workflow".

Reported bug: on the modify path the plugin-supplied markdown is copied with a
bare shutil.copy2 and never rewritten to reference the concrete project root
(_prepare_workflow_file is skipped), so the staged workflow keeps the generic
repo-root placeholder.

FM-Agent self-validation guard: this probe never starts an FM-Agent workflow.
run_opencode_traced is replaced by a hard-failing stub, and resume=True with a
schema-valid phases.json makes _run_generate_phases skip agent invocation
entirely (the spec-sanctioned "no agent invocation" resume path). All fixtures
live in a fresh temporary directory.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# The exact generic instruction line that _prepare_workflow_file is supposed to
# rewrite (verbatim from src/pipeline_setup.py, lines 879-880).
GENERIC_LINE = (
    "- `phases[*].modules[*].source_files` — relative paths from repo root of all source files "
    "that belong to this module."
)


def main():
    from src.pipeline_setup import _run_generate_phases
    from src.plugin import PluginStageConfig
    import src.pipeline_setup as pipeline_setup

    # FM-Agent guard: absolutely no OpenCode / agent subprocess may start.
    def _forbidden_agent_call(*args, **kwargs):
        raise RuntimeError("SAFETY: probe attempted to launch OpenCode — forbidden")

    pipeline_setup.run_opencode_traced = _forbidden_agent_call

    # ---- Fresh probe-owned workspace (never the active repo) -------------
    tmp = tempfile.mkdtemp(prefix="probe_run_generate_phases_")
    try:
        proj_dir = os.path.join(tmp, "fake_project")
        work_dir = os.path.join(proj_dir, "fm_agent")
        os.makedirs(work_dir)
        proj_dir_abs = os.path.abspath(proj_dir)

        # Dummy project source file.
        with open(os.path.join(proj_dir, "hello.py"), "w") as f:
            f.write("x = 1\n")

        # Schema-valid phases.json => resume=True takes the no-agent path.
        phases = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [{"name": "core", "source_files": ["hello.py"]}],
                }
            ]
        }
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump(phases, f)

        # Plugin fixture: a 'modify' hook whose workflow still carries the
        # generic repo-root placeholder (what a plugin author would ship).
        plugin_root = os.path.join(tmp, "plugin_root")
        os.makedirs(plugin_root)
        plugin_input_rel = "custom_generate_phases.md"
        plugin_input_body = (
            "# Custom phase plan workflow\n\n"
            f"{GENERIC_LINE}\n\n"
            "Write `fm_agent/phases.json` according to the rules above.\n"
        )
        with open(os.path.join(plugin_root, plugin_input_rel), "w") as f:
            f.write(plugin_input_body)

        stage = PluginStageConfig(type="modify", input_md=plugin_input_rel)

        # ---- Run under test: modify-hook path ----------------------------
        ret_modify = _run_generate_phases(
            proj_dir,
            work_dir,
            REPO_ROOT,
            is_incremental=False,
            resume=True,
            submodules=None,
            plugin_stage=stage,
            plugin_root=Path(plugin_root),
        )

        staged_path = os.path.join(work_dir, "workflow_generate_phases.md")
        if not os.path.exists(staged_path):
            print("ERROR: staged workflow file was not produced")
            return 1
        with open(staged_path, "r") as f:
            staged_modify = f.read()

        # ---- Control run: built-in flow (plugin_stage=None) --------------
        # Same resume-skip conditions; _prepare_workflow_file must specialize.
        os.remove(staged_path)
        ret_control = _run_generate_phases(
            proj_dir,
            work_dir,
            REPO_ROOT,
            is_incremental=False,
            resume=True,
            submodules=None,
            plugin_stage=None,
            plugin_root=None,
        )
        with open(staged_path, "r") as f:
            staged_control = f.read()

        # ---- Oracle -------------------------------------------------------
        # Spec-correct behavior for the modify path: staged workflow
        # specialized to the concrete project root (generic line replaced).
        modify_generic_kept = GENERIC_LINE in staged_modify
        modify_specialized = proj_dir_abs in staged_modify and not modify_generic_kept

        control_generic_kept = GENERIC_LINE in staged_control
        control_specialized = proj_dir_abs in staged_control and not control_generic_kept

        bug_reproduced = (
            ret_modify is None
            and ret_control is None
            and control_specialized      # built-in flow does specialize (oracle sanity)
            and modify_generic_kept      # modify path kept the generic placeholder
            and not modify_specialized   # and never injected the concrete project root
        )

        print(
            f"DETAIL: modify path -> generic line kept: {modify_generic_kept}, "
            f"specialized to {proj_dir_abs!r}: {modify_specialized}"
        )
        print(
            f"DETAIL: built-in control path -> generic line kept: {control_generic_kept}, "
            f"specialized: {control_specialized}"
        )

        if bug_reproduced:
            print(
                "CONFIRMED — modify-hook staged workflow lacks project-root "
                f"specialization; still contains generic instruction: {GENERIC_LINE!r} "
                f"| expected specialization referencing: {proj_dir_abs!r}"
            )
            return 0
        print(
            "NOT CONFIRMED — modify-hook staged workflow matched the spec "
            "(was specialized to the concrete project root)"
        )
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — probe must never crash silently
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)

```

### Probe Output

```
[Pipeline] Stage 1/6: RESUME — phases.json found, skipping phase plan generation.
[Pipeline] Stage 1/6: RESUME — phases.json found, skipping phase plan generation.
DETAIL: modify path -> generic line kept: True, specialized to '/tmp/probe_run_generate_phases_4sxa8od5/fake_project': False
DETAIL: built-in control path -> generic line kept: False, specialized: True
CONFIRMED — modify-hook staged workflow lacks project-root specialization; still contains generic instruction: '- `phases[*].modules[*].source_files` — relative paths from repo root of all source files that belong to this module.' | expected specialization referencing: '/tmp/probe_run_generate_phases_4sxa8od5/fake_project'
```
