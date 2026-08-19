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
