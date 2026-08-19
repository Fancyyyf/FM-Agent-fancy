"""Probe script for bug: adapter_for_api_style returns wrong package for 'openai' style."""
import sys
import os
import tempfile

# Use a fresh temporary directory for any runtime artifacts (not in fm_agent/)
with tempfile.TemporaryDirectory(prefix="bug_probe_") as tmpdir:
    # We must not write runtime outputs under fm_agent/
    os.chdir(tmpdir)

try:
    # Import through the public module entry point
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.configure_llm import adapter_for_api_style, ConfigWizardError

    # Test 1: 'openai' should return '@ai-sdk/openai' per spec
    actual_openai = adapter_for_api_style("openai")
    expected_openai = "@ai-sdk/openai"
    openai_bug = actual_openai != expected_openai

    # Test 2: 'anthropic' should return '@ai-sdk/anthropic' (sanity check)
    actual_anthropic = adapter_for_api_style("anthropic")
    expected_anthropic = "@ai-sdk/anthropic"
    anthropic_ok = actual_anthropic == expected_anthropic

    # Test 3: Unknown style should raise ConfigWizardError
    unknown_raises = False
    try:
        adapter_for_api_style("gemini")
    except ConfigWizardError:
        unknown_raises = True
    except Exception:
        pass

    # Overall verdict: bug is confirmed when openai returns wrong package
    if openai_bug:
        print(
            "CONFIRMED — actual: "
            f"{actual_openai!r} | expected: {expected_openai!r}"
        )
    else:
        print(
            "NOT CONFIRMED — actual matched expected: "
            f"{actual_openai!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
