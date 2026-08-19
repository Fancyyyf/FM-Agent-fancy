# Bug Report: main

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/generate_batch_prompts.py:main`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns 0. On dry-run: prints the batch plan (phase, layer range, function/batch counts with per-batch details) to stdout without writing any files. On non-dry-run: writes batch prompt .txt files under the output directory, one per batch of functions for the specified phase and layer range, each containing code, signatures, and callee specs for every function in that batch; writes a manifest.json describing all batches (including already-specced functions on resume); removes stale batch files from the output directory that do not belong to the current run. On resume, functions whose .spec.json and .info.json are both ready are excluded from prompt generation. Raises ValueError if batch_size is not strictly positive or if the requested layer range is outside [0, total_layers - 1].

---

### Actual Behavior

If args.batch_size <= 0, a ValueError with message "--batch-size must be > 0" is raised and no subsequent statements execute. Otherwise, if after reading topdown_layers.json and parsing layers spec the condition start_layer < 0 or end_layer >= total_layers holds, a ValueError with message "layer range {args.layers} out of bounds [0, {total_layers - 1}]" is raised and no further assignments occur. Otherwise (normal termination): args is defined with all attributes reflecting the command line and args.batch_size > 0; work_dir is a Path object resolving to the fm_agent/ working directory (parent of the directory containing this script); repo_root is work_dir.parent; fm_agent_prefix is the string of the relative path from repo_root to work_dir followed by '/'; phases_json is the parsed dict of phases.json and project = phases_json['project']; languages and exts are list values from phases_json (defaulting to [] if missing); ext_to_lang is a dict mapping each extension from exts (lowercased and with leading dot removed) to the corresponding language from languages; topdown_path is the path to the requested phase's topdown_layers.json, topdown its parsed dict, layers = topdown.get('layers', []), and total_layers = len(layers); start_layer and end_layer are the inclusive bounds from parsing args.layers and satisfy 0  start_layer  end_layer < total_layers; output_dir is a Path object, equal to Path(args.output_dir) if args.output_dir was truthy, else work_dir / 'spec_prompts' / f'batch_prompts_{project}_phase{args.phase:02d}'; func_to_layer maps each function name across all layers to its layer index (after stripping fm_agent_prefix from the file path if present); all_funcs maps the same names to their function metadata dicts (with the possibly modified file field); manifest_batches, total_functions, skipped_functions, batch_index, write_targets are initialized respectively as an empty list, 0, 0, 0, and an empty list. No filesystem side effects ... (line truncated to 2000 chars)

---

## Code Evidence

Line 1 - Line 40: The code only parses arguments, validates them, reads JSON configs, and initialises data structures. It never reaches the specification-required logic for generating batch prompts, writing output files, creating manifest.json, removing stale files, or handling resume/dry-run.

---

## Trigger Condition

The code block ends after initialisation (line 40). For a valid input that passes all validation, the code does nothing further, violating the specification which mandates file generation, manifest creation, stale-file cleanup, and dry-run output. Any conforming input with batch_size > 0 and an in-range layer spec results in complete omission of the required behaviour.

---

## How to trigger the bug

The logic verification incorrectly concluded that `main()` ends at line 40. In reality, the function spans 138 lines (in the extracted version) and lines 41–138 contain the full batch-generation logic: layer iteration, batch chunking, dry-run output, manifest creation, file writing, and stale-file cleanup. The probe confirmed via `inspect.getsource()` that all seven required code patterns are present.

### Inputs

| Parameter | Value |
|---|---|
| Module | `src.generate_batch_prompts` |
| Function | `main` |
| Inspection method | `inspect.getsource(generate_batch_prompts.main)` |

### Expected (spec-correct) Output

The spec requires `main()` to contain logic for batch prompt generation, manifest creation, dry-run output, file writing, stale cleanup, and resume support.

### Actual (buggy) Output

The `main()` function already contains all required logic. The source is 138 lines, not 40 as claimed by the logic verification.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import inspect
from pathlib import Path

_repo_root = Path(".").resolve()
sys.path.insert(0, str(_repo_root))

from src import generate_batch_prompts

main_source = inspect.getsource(generate_batch_prompts.main)
lines = len(main_source.strip().split("\n"))

# If lines > 40 and patterns exist, the bug is NOT CONFIRMED
# actual (buggy) output: main() has only ~40 lines (per verification claim)
# expected (correct) output: main() has 138 lines with full batch logic
print(f"main() source lines: {lines}")
print("build_prompt" in main_source)
print("output_dir.mkdir" in main_source)
print("manifest" in main_source)
```

---

## Probe Script

```python
"""Probe: verify that main() in src/generate_batch_prompts.py extends past line 40
and contains the batch-generation logic claimed missing by the logic verification."""

import sys
import inspect
from pathlib import Path

# Add repo root to path so the src package is importable
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

try:
    from src import generate_batch_prompts

    main_source = inspect.getsource(generate_batch_prompts.main)
    source_lines = main_source.strip().split("\n")

    # The logic verification claims the function ends at line 40
    # of the extracted version with only init code.
    # Check that the source has more than 40 non-trivial lines.
    line_count = len(source_lines)
    beyond_init = line_count > 40

    # Check for key patterns the spec requires but verification claims are missing
    has_build_prompt = "build_prompt" in main_source
    has_output_mkdir = "output_dir.mkdir" in main_source
    has_manifest = "manifest" in main_source
    has_dry_run = "dry_run" in main_source
    has_write_targets = "write_targets" in main_source
    has_stale = "stale" in main_source
    has_resume = "args.resume" in main_source

    all_required_patterns = (
        has_build_prompt
        and has_output_mkdir
        and has_manifest
        and has_dry_run
        and has_write_targets
        and has_stale
        and has_resume
    )

    # The bug claim: code "ends after initialisation (line 40)"
    # and "does nothing further".
    # If the code DOES have batch-generation logic, the bug is NOT CONFIRMED.
    bug_confirmed = not (beyond_init and all_required_patterns)

    if bug_confirmed:
        verdict = "CONFIRMED"
        details = (
            f"bug confirmed: main() source is {line_count} lines, "
            f"beyond_init={beyond_init}, all_patterns={all_required_patterns}"
        )
    else:
        verdict = "NOT CONFIRMED"
        details = (
            f"main() source extends to {line_count} lines (beyond the claimed 40-line cutoff) "
            f"and contains all required batch-generation patterns: "
            f"build_prompt={has_build_prompt}, output_dir.mkdir={has_output_mkdir}, "
            f"manifest={has_manifest}, dry_run={has_dry_run}, "
            f"write_targets={has_write_targets}, stale={has_stale}, "
            f"resume={has_resume}"
        )

    print(f"{verdict} — {details}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — main() source extends to 138 lines (beyond the claimed 40-line cutoff) and contains all required batch-generation patterns: build_prompt=True, output_dir.mkdir=True, manifest=True, dry_run=True, write_targets=True, stale=True, resume=True
```
