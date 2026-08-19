import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

try:
    from src.configure_llm import remove_legacy_llm_env_overrides

    # Trigger: line with 'export LLM_MODEL' that has NO '=' sign
    # LLM_MODEL is in ENV_LEGACY_LLM_KEYS, so spec says it should be removed.
    # Bug: env_key becomes "" because sep is empty, so line is kept.
    test_input = "export LLM_MODEL\n"

    cleaned, removed = remove_legacy_llm_env_overrides(test_input)

    # Spec requires: cleaned should be "" (line removed), removed should be ("LLM_MODEL",)
    spec_cleaned = ""
    spec_removed = ("LLM_MODEL",)

    # The bug is confirmed if actual behavior does NOT match spec
    passed = (cleaned != spec_cleaned) or (removed != spec_removed)
    actual_str = repr((cleaned, removed))
    expected_str = repr((spec_cleaned, spec_removed))
except Exception as e:
    actual_str = f"Exception: {type(e).__name__}: {e}"
    expected_str = repr(("", ("LLM_MODEL",)))
    passed = True

if passed:
    print(f"CONFIRMED — actual: {actual_str} | expected: {expected_str}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_str}")
