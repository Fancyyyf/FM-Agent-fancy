# Bug Report: _build_domain_context_regen_prompt

**Source file:** `src/pipeline_setup-py/_build_domain_context_regen_prompt.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string containing a complete agent instruction prompt for regenerating per-phase domain-context type files. The prompt lists each phase number in phase_source_files in ascending order, each with the directive to rewrite the corresponding phase_NN_types.txt file from scratch using the phase's current source files. When phase_source_files is empty or yields no entries, the prompt states that no phase type files need regeneration. The prompt forbids modifying files under user_knowledge/ and restricts edits to engine_overview.txt and phase_NN_types.txt only. If phase_cleanup, after filtering out None-valued entries and identity renumberings (old == new), contains at least one removed phase or one renumbered phase where old differs from new, the prompt instructs the agent to update engine_overview.txt to match the final phase numbers after cleanup. Otherwise, the prompt instructs the agent to modify engine_overview.txt only if it explicitly references a changed phase number.

---

### Actual Behavior

Natural language: The function _build_domain_context_regen_prompt returns a string S and has no side effects on the input arguments, no exceptions, and no other observable state changes. S follows the pattern: 'Regenerate per-phase domain-context files under fm_agent/spec_prompts/domain_context/ (named phase_NN_types.txt) so each reflects its phase's CURRENT source_files:\n\n' + changes_text + '\n\nRules:\n- Base each file on the types in that phase\'s source files; do not invent new types.\n- Do NOT modify any other files. Only edit engine_overview.txt and phase_NN_types.txt files directly under fm_agent/spec_prompts/domain_context/. Do NOT edit files under fm_agent/spec_prompts/domain_context/user_knowledge/.\n' + overview_rule. The changes_text is built as: if phase_source_files is empty, it is '  - No phase_NN_types.txt files need regeneration; only update engine_overview.txt if cleanup made its phase references stale.'; otherwise, it is a newline-separated list of lines, one per phase number in sorted ascending order, each line containing the instruction '  - phase <num>: REGENERATE phase_<num:02d>_types.txt from scratch. Its source_files are now: <comma-space-separated list of file paths>. READ them in the project and write the real types/structs/invariants they define. Do not leave the file empty or invent content.' The overview_rule is determined by processing phase_cleanup (None is treated as {}). removed_phases is the list obtained from phase_cleanup['removed_phases'] with any None entries removed; renumbered_changes is the dict from phase_cleanup['renumbered'] excluding any pair where old is None, new is None, or old equals new. If removed_phases is non-empty or renumbered_changes is non-empty, overview_rule = '- Review engine_overview.txt and update any phase-numbered references so they match the final phases.json after cleanup (' + cleanup_details + ').' where cleanup_details is a semicolon-joined string of the removal li...

---

## Code Evidence

Line 31:     renumbered_changes = {\nLine 32:         old: new for old, new in renumbered.items()\nLine 33:         if old is not None and new is not None and old != new\nLine 34:     }

---

## Trigger Condition

The specification says to filter out 'None-valued entries' from the renumbered mapping, which conventionally means entries whose value is None. The code additionally filters out entries where the key (old) is None. For an input like {None: 2}, the specification would retain the entry and thus require an engine_overview.txt update instruction. The code discards it, resulting in a different instruction string.

---

## How to trigger the bug

The function `_build_domain_context_regen_prompt` at lines 82-85 filters the `renumbered` dict with the condition `old is not None and new is not None`, but the specification only requires filtering entries where the **value** (`new`) is `None` — not entries where the **key** (`old`) is `None`.

When `phase_cleanup["renumbered"]` contains a key of `None` with a valid non-None value (e.g., `{None: 2}`), the code discards this entry, treating it as if no renumbering occurred. The correct behavior per spec is to retain the entry, triggering the engine_overview.txt update instruction.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phase_source_files` | `{1: ["test_file.py"]}` |
| `phase_cleanup` | `{"renumbered": {None: 2}}` |

### Expected (spec-correct) Output

The returned prompt string includes: `"Review engine_overview.txt and update any phase-numbered references so they match the final phases.json after cleanup (renumbered surviving phase(s): None -> 2)."`

### Actual (buggy) Output

The returned prompt string includes: `"engine_overview.txt does not need updating; touch it only if it explicitly names a phase number that changed."` — the `{None: 2}` entry was discarded by the `old is not None` check at line 84.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.pipeline_setup import _build_domain_context_regen_prompt

result = _build_domain_context_regen_prompt(
    {1: ["test_file.py"]},
    {"renumbered": {None: 2}},
)
print(result)
# actual (buggy) output includes: "...engine_overview.txt does not need updating..."
# expected (correct) output includes: "...Review engine_overview.txt and update..."
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual output says 'does not need updating' (None-keyed entry {None: 2} was discarded by the code); expected output should include 'Review engine_overview.txt and update' (spec keeps None-keyed entry when value is not None)
```
