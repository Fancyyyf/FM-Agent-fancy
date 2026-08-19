# Bug Report: build_prompt

**Source file:** `src/generate_batch_prompts.py` (lines 208-368)
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a single string that constitutes a complete, self-contained LLM prompt for generating behavioral specifications. The prompt begins with a header identifying the phase number and layer index, followed by the detected programming language of the first function's file extension according to ext_to_lang. It instructs reading the mandatory domain-context files: system_prompt.md, engine_overview.txt, the phase-specific types file (named with the phase number zero-padded to two digits), and any user-provided markdown files found in the staged domain-knowledge directory under work_dir. Behavioral spec writing rules are included. For every caller whose layer index (from func_to_layer) is strictly less than layer_idx and whose identity appears in any function's phase-caller metadata, its formatted spec block is included (read from its adjacent .spec.json sidecar). Callee expectations extracted from those same callers' .info.json sidecars are included for each function, matching by the function's name and any info-name aliases from its phase-callee-info-names metadata. When is_cycle is true, cycle-layer guidance is appended describing mutual-recursion invariant principles and dispatch-function contract rules. Every function in functions is enumerated with its file path relative to fm_agent_prefix and annotated with the set of its earlier-layer callers (callers whose layer is strictly less than layer_idx). The prompt closes with the mandatory SPEC FORMAT section (documenting the .spec.json and .info.json output schemas) and the PROCESS section (listing the sequential steps for processing each function). The returned string has no trailing whitespace and ends with exactly one newline character.

---

### Actual Behavior

The function returns a string `R` formed by `"\n".join(L).rstrip() + "\n"`, where `L` is the `lines` list after the execution of lines 81153. The list `L` is built from the initial `lines` (which, per the precondition, may already contain the earlierlayer caller spec header and entries if any valid spec blocks were found) by appending the following items in order:

1. The value of the variable `block` (a string).
2. An empty string (`''`).
3. If the variable `caller_expectations` is truthy (i.e. nonempty and not `None`):
   a. The string `"## CALLEE EXPECTATIONS FROM CALLERS"`.
   b. For each function metadata dictionary `fn` in `functions`, in iteration order:
      - Let `fn_name = fn["name"]`, `entries = caller_expectations.get(fn_name, [])`.
      - If `entries` is nonempty:
         * The string `f"### What callers expect from {fn_name}:"`
         * For each `(caller_name, entry)` in `entries` (preserving order):
             The string `f"#### According to {caller_name}:"`
             The string `entry`
         * An empty string.
4. If the variable `is_cycle` is truthy:
   a. The string `"## CYCLE LAYER GUIDANCE"`.
   b. The following fixed strings in order:
      - `"These functions call each other (mutual recursion / circular dependencies)."`
      - `'Ask: "What is true after this function returns, regardless of which caller invoked it and which code path executed?" That invariant is your post-condition.'`
      - `""` (empty string)
      - `"DISPATCH FUNCTION TEST: If your spec has N bullets where N equals the number"`
      - `"of switch arms / dispatch cases, you are transcribing the implementation."`
      - `"A dispatch function's contract is the invariant that holds ACROSS ALL cases."`
      - `""` (empty string)
5. The string `f"## FUNCTIONS ({len(functions)} total - process ALL)"`.
6. For each pair `(idx, fn)` produced by `enumerate(functions, start=1)`:
   a. `fn_... (line truncated to 2000 chars)

---

## Code Evidence

Line 81-153: The code block does not append the required header identifying phase number and layer index, the detected programming language, the domaincontext file reading instructions, the behavioral spec writing rules, or the formatted spec blocks from earlierlayer callers. The resulting string lacks these mandatory elements, violating specification (B).

---

## Trigger Condition

The specification requires a complete prompt containing a header (phase, layer, language), domaincontext file instructions, behavioral spec rules, and formatted earlierlayer caller spec blocks. The code block (lines 81153) adds only a subset of those elements. With an empty initial `lines`, the returned string misses the required header, language detection, filereading instructions, spec rules, and caller spec blocks, producing a concrete output that does not satisfy (B).

---

## How to trigger the bug

The bug report mischaracterizes the function by describing only a **subset** of the code (lines 81-153) while ignoring the preceding lines (12-76 in the extracted version / 219-248 in the source). The function initializes `lines = []` on line 219 and then appends **all** required elements before the return on line 368:

| Line range | Element | Matches spec_claim |
|---|---|---|
| 224-225 | Header with phase number and layer index | ✓ |
| 226-229 | Detected programming language | ✓ |
| 231-241 | Domain-context file reading instructions (system_prompt.md, engine_overview.txt, phase types, user knowledge) | ✓ |
| 243-248 | KEY RULES (behavioral spec writing rules) | ✓ |
| 285-292 | Formatted spec blocks from earlier-layer callers (when present) | ✓ |
| 294-305 | Callee expectations from callers (when present) | ✓ |
| 307-318 | Cycle-layer guidance (when is_cycle) | ✓ |
| 320-330 | Function enumeration with earlier-layer callers | ✓ |
| 332-357 | SPEC FORMAT section | ✓ |
| 358-367 | PROCESS section | ✓ |
| 368 | `.rstrip() + "\n"` — no trailing whitespace, one newline | ✓ |

The `actual_behavior` incorrectly describes only lines 81-153 as contributing to the output, but lines 12-76 (header, language, domain-context, KEY RULES) and lines 78-85 (caller spec blocks) are **already** part of `lines` before line 81 executes. The function produces a complete prompt with all mandated sections.

### Inputs

| Parameter | Value |
|---|---|
| phase | 1 |
| layer_idx | 0 |
| is_cycle | False |
| functions | [] (empty list) |
| func_to_layer | {} |
| all_funcs | {} |
| work_dir | Path(".") |
| fm_agent_prefix | "fm_agent/" |
| ext_to_lang | {"py": "python"} |

### Expected (spec-correct) Output

A string containing: phase/layer header, language detection, domain-context file instructions, KEY RULES, SPEC FORMAT, and PROCESS sections.

### Actual (buggy) Output

Same as expected — all sections are present. Output length: 1658 characters.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.generate_batch_prompts import build_prompt
from pathlib import Path

result = build_prompt(
    phase=1,
    layer_idx=0,
    is_cycle=False,
    functions=[],
    func_to_layer={}, all_funcs={},
    work_dir=Path("."),
    fm_agent_prefix="fm_agent/",
    ext_to_lang={"py": "python"},
)

# Verify all required sections are present
assert "Phase 1" in result          # header with phase
assert "Layer 0" in result          # header with layer
assert "Language:" in result        # language detection
assert "system_prompt.md" in result # domain-context instructions
assert "KEY RULES" in result        # behavioral spec rules
assert "PROCESS" in result          # PROCESS section
assert "SPEC FORMAT" in result      # SPEC FORMAT section
print("All sections present — no bug detected")
// actual (buggy) output: All sections present — no bug detected
// expected (correct) output: All sections present — no bug detected
```

---

## Probe Script

```python
import sys
import os

# Add repo root to path: probe is at fm_agent/bug_validation/probe_*.py (3 levels down)
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    # Load the package via public entry point
    from src.generate_batch_prompts import build_prompt
    from pathlib import Path

    # Call with empty functions list — the spec_claim requires header, language,
    # domain-context instructions, KEY RULES (spec writing rules) even with no functions.
    # If the function is correct, these should all be present.
    result = build_prompt(
        phase=1,
        layer_idx=0,
        is_cycle=False,
        functions=[],
        func_to_layer={},
        all_funcs={},
        work_dir=Path("."),
        fm_agent_prefix="fm_agent/",
        ext_to_lang={"py": "python"},
    )

    missing = []
    if "Phase 1" not in result:
        missing.append("phase number in header")
    if "Layer 0" not in result:
        missing.append("layer index in header")
    if "Language:" not in result:
        missing.append("language detection")
    if "system_prompt.md" not in result:
        missing.append("domain-context file instruction (system_prompt.md)")
    if "KEY RULES" not in result:
        missing.append("behavioral spec writing rules (KEY RULES)")
    if "PROCESS" not in result:
        missing.append("PROCESS section")
    if "SPEC FORMAT" not in result:
        missing.append("SPEC FORMAT section")

    if missing:
        print(f"CONFIRMED — missing required sections: {'; '.join(missing)}")
    else:
        print(f"NOT CONFIRMED — all required sections present in build_prompt output "
              f"(length={len(result)} chars)")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — all required sections present in build_prompt output (length=1658 chars)
```
