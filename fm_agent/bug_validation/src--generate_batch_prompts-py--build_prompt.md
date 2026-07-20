# Bug Report: build_prompt

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/generate_batch_prompts-py/build_prompt.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string that constitutes the complete batch prompt for the given set of functions
  - The prompt begins with a header line identifying the phase number and layer index
  - The language name and comment prefix in the header are derived from the first function's file extension via ext_to_lang; when functions is empty, "unknown" and "//" are used
  - The prompt references exactly these required reading files (each prepended with fm_agent_prefix): spec_prompts/system_prompt.md, spec_prompts/domain_context/engine_overview.txt, and spec_prompts/domain_context/phase_NN_types.txt where NN is the phase number zero-padded to two digits
  - If any staged user-provided domain knowledge files exist under fm_agent/spec_prompts/domain_context/user_knowledge/, the prompt lists each one with its fm_agent_prefix-prefixed path
  - The "KEY RULES" section contains exactly four behavioral-spec rules and one file-location directive
  - If any function in the batch has an in-phase caller assigned to a strictly lower layer index than layer_idx, the prompt includes an "EARLIER-LAYER CALLER SPECS" section with each such caller's FQN followed by its full [SPEC] block; each caller appears at most once
  - If any earlier-layer caller's [INFO] block contains an expectation for a function being specced, the prompt includes a "CALLEE EXPECTATIONS FROM CALLERS" section that groups those expectations by target function FQN, with each expectation preceded by its caller's FQN as an attribution header
  - When is_cycle is true, the prompt includes a "CYCLE LAYER GUIDANCE" section describing the mutual-recursion invariant approach and the dispatch-function test
  - The prompt lists every function in the batch with its fm_agent_prefix-prefixed file path, numbered sequentially starting at 1, and each listing shows its earlier-layer callers or "(none)" when there are none
  - The prompt appends the mandatory [SPEC]/[INFO] format template using the detected language's comment prefix, including the "(no callees)" instruction, followed by numbered processing instructions (read, read callers, write spec, write file)
  - The returned string ends with exactly one newline character and contains no trailing whitespace on any line

---

### Actual Behavior

Post-condition (natural language): After executing the code block, the list `lines` has been extended with:
- For each function in `functions`, if there are corresponding entries in `caller_expectations` (extracted from earlier-layer callers), a header "### What callers expect from {fn_name}:" followed by each caller's name and expectation entry, and a blank line.
- If `is_cycle` is true, a section "## CYCLE LAYER GUIDANCE" with guidance messages.
- A section "## FUNCTIONS (N total ...)" listing each function with its index, file, and its earlier-layer callers.
- A section "## SPEC FORMAT" providing the required [SPEC] and [INFO] format templates.
- A section "## PROCESS" with step-by-step instructions.
The function then returns the string formed by joining all lines with newline characters, stripping trailing whitespace, and appending a final newline. No exceptions occur, and all variables in the enclosing scope (including `functions`, `all_funcs`, `fm_agent_prefix`, `work_dir`, `ext_to_lang`, `phase`, `layer_idx`, `is_cycle`, `func_to_layer`, `sample_comment`, and the global `build_prompt`) remain unchanged from their values before the block.

Formal:
 lines, ret such that:
1. lines = lines_pre  L_expect  L_cycle  L_functions_header  L_functions_list  [""]  L_spec_format  L_process
   where:
   - L_expect = _{fn  functions} ( let fn_name = fn["name"], entries = caller_expectations.get(fn_name, []) in if entries  [] then ["### What callers expect from " + fn_name + ":"]  (_{(caller_name, entry)  entries} ["#### According to " + caller_name + ":", entry])  [""] else [] )
   - L_cycle = if is_cycle then ["## CYCLE LAYER GUIDANCE", "These functions call each other (mutual recursion / circular dependencies).", 'Ask: "What is true after this function returns, regardless of which caller invoked it and which code path executed?" ', "That invariant is your post-condition.", "", "DISPATCH FUNCTION TEST:...

---

## Code Evidence

Line 83: lines.append(f"### What callers expect from {fn_name}:")

---

## Trigger Condition

Specification B requires a 'CALLEE EXPECTATIONS FROM CALLERS' section header whenever caller expectations exist. The code (lines 81--87) produces only per-function subheadings without the required section title, so any input with non-empty caller_expectations yields an output that misses this header.

---

## How to trigger the bug

The specification requires that when caller expectations are present, the prompt includes a "## CALLEE EXPECTATIONS FROM CALLERS" section header. The code evidence points to line 83 (in the extracted function), which corresponds to a per-function subheading. However, inspection of the actual source code at `src/generate_batch_prompts.py` shows that line 303 explicitly includes the required section header:

```python
    if caller_expectations:
        lines.append("## CALLEE EXPECTATIONS FROM CALLERS")
```

The probe test confirmed that calling `build_prompt` with callers that have callee expectations in their [INFO] blocks produces output containing the "## CALLEE EXPECTATIONS FROM CALLERS" header. The bug as described cannot be reproduced against the current code.

### Inputs

| Parameter | Value |
|-----------|-------|
| phase | 1 |
| layer_idx | 1 |
| is_cycle | false |
| functions | [{"name": "target_module::target_func", "file": "...", "phase1_callers": ["caller_func"], "phase1_callee_info_names_by_caller": {"caller_func": []}}] |
| func_to_layer | {"caller_func": 0} |
| all_funcs | {"caller_func": {"name": "caller_func", "file": "extracted_functions/src/caller/caller_func.py"}} |
| fm_agent_prefix | "fm_agent/" |
| ext_to_lang | {".py": "python"} |

The caller's extracted function file contained a [INFO] block with a callee expectation entry for "target_module::target_func".

### Expected (spec-correct) Output

The prompt string must include `## CALLEE EXPECTATIONS FROM CALLERS` as a section header when caller expectations are present.

### Actual (buggy) Output

The actual output DOES include `## CALLEE EXPECTATIONS FROM CALLERS` — the code at line 303 of `src/generate_batch_prompts.py` produces this header. No bug detected.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.generate_batch_prompts import build_prompt

functions = [{"name": "target_module::target_func", "file": "extracted_functions/target_func.py",
              "phase1_callers": ["caller_func"], "phase1_callee_info_names_by_caller": {"caller_func": []}}]
func_to_layer = {"caller_func": 0}
all_funcs = {"caller_func": {"name": "caller_func", "file": "extracted_functions/src/caller/caller_func.py"}}

# Requires a caller file on disk with [INFO] block containing expectations
result = build_prompt(1, 1, False, functions, func_to_layer, all_funcs,
                      work_dir=Path("."), fm_agent_prefix="fm_agent/",
                      ext_to_lang={".py": "python"})

# Check: the section header IS present in the result
assert "## CALLEE EXPECTATIONS FROM CALLERS" in result
```

---

## Probe Script

```python
"""Probe script for bug ID src--generate_batch_prompts-py--build_prompt.

Tests whether build_prompt() includes the "## CALLEE EXPECTATIONS FROM CALLERS"
section header when caller expectations exist for functions in the batch.
"""
import sys
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from src.generate_batch_prompts import build_prompt


def create_caller_file(callee_fqn: str, expectation: str) -> str:
    """Create a minimal extracted-function file with a [INFO] block that
    contains an expectation for callee_fqn."""
    return f"""# [SPEC]
# Unit: some/caller.py
#
# caller_func(params) -> ReturnType
#   Pre-condition: ...
#   Post-condition: ...
# [SPEC]
# [INFO]
# {callee_fqn}(params) -> ReturnType
#   Pre-condition: input is valid
#   Post-condition: {expectation}
# [SPLIT]
# other_func(params) -> ReturnType
#   Pre-condition: ...
#   Post-condition: ...
# [INFO]
"""


def test_build_prompt_includes_callee_expectations_header() -> bool:
    """Return True if the section header IS present (bug NOT reproduced)."""

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        # --- Create a caller's extracted function file with a callee expectation ---
        callee_fqn = "target_module::target_func"
        expectation = "returns a string representing the complete prompt"
        caller_file_content = create_caller_file(callee_fqn, expectation)

        caller_relpath = "extracted_functions/src/caller/caller_func.py"
        caller_abs = work_dir / caller_relpath
        caller_abs.parent.mkdir(parents=True)
        caller_abs.write_text(caller_file_content)

        # --- Build test data that triggers the caller_expectations branch ---
        functions = [
            {
                "name": callee_fqn,
                "file": "extracted_functions/target_func.py",
                "phase1_callers": ["caller_func"],
                "phase1_callee_info_names_by_caller": {"caller_func": []},
            }
        ]

        func_to_layer = {"caller_func": 0}  # caller at layer 0 → lower than layer_idx
        all_funcs = {
            "caller_func": {
                "name": "caller_func",
                "file": caller_relpath,
            }
        }

        ext_to_lang = {".py": "python"}

        # --- Call build_prompt — target at layer 1, caller at layer 0 ---
        result = build_prompt(
            phase=1,
            layer_idx=1,
            is_cycle=False,
            functions=functions,
            func_to_layer=func_to_layer,
            all_funcs=all_funcs,
            work_dir=work_dir,
            fm_agent_prefix="fm_agent/",
            ext_to_lang=ext_to_lang,
        )

        # --- Check results ---
        has_section_header = "## CALLEE EXPECTATIONS FROM CALLERS" in result
        return has_section_header


try:
    header_present = test_build_prompt_includes_callee_expectations_header()

    if header_present:
        print(
            "NOT CONFIRMED — section header '## CALLEE EXPECTATIONS FROM CALLERS' "
            "IS present; bug cannot be reproduced."
        )
    else:
        print(
            "CONFIRMED — section header '## CALLEE EXPECTATIONS FROM CALLERS' "
            "is MISSING; bug reproduced!"
        )

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — section header '## CALLEE EXPECTATIONS FROM CALLERS' IS present; bug cannot be reproduced.
```
