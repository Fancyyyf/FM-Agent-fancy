#!/usr/bin/env python3
"""Probe script for bug ID: src--configure_llm-py--validate_llm_setting.

Tests whether validate_llm_setting() correctly raises ConfigWizardError
for ALL recognized keys when given invalid values, as required by the spec.

Bug summary: The spec claims every recognized key is validated, but
'name' and 'effort' keys are not validated at all — they silently
accept empty/invalid values instead of raising ConfigWizardError.
"""
import sys
import os
import tempfile

# FM-Agent self-validation guard: use a temp directory as workspace
tmpdir = tempfile.mkdtemp(prefix="probe_validate_llm_setting_")
os.chdir(tmpdir)

sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.configure_llm import (
        validate_llm_setting,
        ConfigWizardError,
        _LLM_TOML_KEYS,
        _EFFORTS,
    )

    bugs: list[str] = []
    non_confirmed: list[str] = []

    # ------------------------------------------------------------------
    # Test 1: 'name' key — spec requires non-empty trimmed string
    # ------------------------------------------------------------------
    for val in ["", "   "]:
        try:
            result = validate_llm_setting("name", val)
            bugs.append(
                f"'name' key with {val!r}: returned {result!r} — "
                f"spec requires ConfigWizardError for empty/whitespace trimmed value"
            )
        except ConfigWizardError:
            non_confirmed.append(f"'name' key with {val!r}: correctly raised ConfigWizardError")
        except Exception as e:
            bugs.append(
                f"'name' key with {val!r}: raised {type(e).__name__}='{e}' — "
                f"spec requires ConfigWizardError"
            )

    # Valid name values should pass
    for val in ["my-model", "a"]:
        try:
            result = validate_llm_setting("name", val)
            if result is not None:
                bugs.append(f"'name' key with {val!r}: unexpected return {result!r}")
            else:
                non_confirmed.append(f"'name' key with {val!r}: correctly returned None")
        except Exception as e:
            bugs.append(
                f"'name' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"on valid input"
            )

    # ------------------------------------------------------------------
    # Test 2: 'effort' key — spec requires membership in fixed set
    # ------------------------------------------------------------------
    invalid_efforts = ["invalid", "x", "super_high", "unknown_effort"]
    for val in invalid_efforts:
        if val in _EFFORTS:
            continue  # should not happen but be safe
        try:
            result = validate_llm_setting("effort", val)
            bugs.append(
                f"'effort' key with {val!r}: returned {result!r} — "
                f"spec requires ConfigWizardError for value outside {_EFFORTS}"
            )
        except ConfigWizardError:
            non_confirmed.append(
                f"'effort' key with {val!r}: correctly raised ConfigWizardError"
            )
        except Exception as e:
            bugs.append(
                f"'effort' key with {val!r}: raised {type(e).__name__}='{e}' — "
                f"spec requires ConfigWizardError"
            )

    # Valid effort values should pass
    for val in _EFFORTS:
        try:
            result = validate_llm_setting("effort", val)
            if result is not None:
                bugs.append(f"'effort' key with {val!r}: unexpected return {result!r}")
            else:
                non_confirmed.append(f"'effort' key with {val!r}: correctly returned None")
        except Exception as e:
            bugs.append(
                f"'effort' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"on valid input"
            )

    # ------------------------------------------------------------------
    # Test 3: 'base_url' key — verify it DOES raise ConfigWizardError
    #         (trigger_condition claimed wrong exception, but code is fine)
    # ------------------------------------------------------------------
    invalid_urls = ["", "   ", "not-a-url", "ftp://example.com", "http:///"]
    for val in invalid_urls:
        try:
            validate_llm_setting("base_url", val)
            bugs.append(f"'base_url' key with {val!r}: returned without error")
        except ConfigWizardError:
            pass  # correct
        except Exception as e:
            bugs.append(
                f"'base_url' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"instead of ConfigWizardError"
            )

    # ------------------------------------------------------------------
    # Test 4: 'api_style' key — verify it DOES raise ConfigWizardError
    # ------------------------------------------------------------------
    for val in ["grok", "invalid"]:
        try:
            validate_llm_setting("api_style", val)
            bugs.append(f"'api_style' key with {val!r}: returned without error")
        except ConfigWizardError:
            pass  # correct
        except Exception as e:
            bugs.append(
                f"'api_style' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"instead of ConfigWizardError"
            )

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    if bugs:
        print(f"CONFIRMED — found {len(bugs)} spec violation(s):")
        for b in bugs:
            print(f"  - {b}")
        print(
            f"(base_url and api_style correctly raise ConfigWizardError; "
            f"the bug is that 'name' and 'effort' keys have no validation "
            f"against their spec constraints)"
        )
    else:
        print("NOT CONFIRMED — all recognized keys validated correctly with ConfigWizardError")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
