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
