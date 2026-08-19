import sys
import os
import types

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Pre-populate sys.modules with mocks BEFORE importing pipeline_setup
config_mod = types.ModuleType("config")
config_mod.OPENCODE_MAX_RETRIES = 10
config_mod.OPENCODE_SETUP_MODEL = "test"
sys.modules["config"] = config_mod

# Mock src submodules (imported by pipeline_setup at module level)
for name, symbols in [
    ("src.file_utils", ["_is_test_file", "_json_file_is_valid",
                        "_iter_project_source_files", "_is_under_submodules"]),
    ("src.opencode_trace", ["run_opencode_traced"]),
    ("src.llm_client", ["build_llm_cli_command"]),
    ("src.domain_knowledge", ["format_domain_knowledge_bullets",
                               "list_staged_domain_knowledge_relpaths"]),
]:
    mod = sys.modules[name] = types.ModuleType(name)
    for sym in symbols:
        setattr(mod, sym, lambda *a, **kw: None)

sys.path.insert(0, PROJ_ROOT)

try:
    from src.pipeline_setup import _build_domain_context_regen_prompt

    # --- Test Case ---
    # Bug: line 81-85 filters `old is not None` but spec says filter only None-**valued** entries.
    # trigger_condition: {None: 2} — key=None, value=2 (not None)
    #   Spec: retains → cleanup overview trigger fires
    #   Code: discards → "does not need updating"

    phase_source_files = {1: ["test_file.py"]}
    phase_cleanup = {"renumbered": {None: 2}}

    actual = _build_domain_context_regen_prompt(phase_source_files, phase_cleanup)

    has_cleanup_update = "Review engine_overview.txt and update" in actual
    says_no_update = "does not need updating" in actual

    # CONFIRMED when buggy code discards {None:2} → overview says "does not need updating"
    passed = says_no_update and not has_cleanup_update

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        "CONFIRMED — actual output says 'does not need updating' "
        "(None-keyed entry {None: 2} was discarded by the code); "
        "expected output should include 'Review engine_overview.txt and update' "
        "(spec keeps None-keyed entry when value is not None)"
    )
else:
    print(
        f"NOT CONFIRMED — actual has_cleanup_update={has_cleanup_update}, "
        f"says_no_update={says_no_update}"
    )
