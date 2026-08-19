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
