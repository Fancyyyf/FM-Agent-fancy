"""Minimal probe for validate_base_url bug: accepts invalid port in URL."""

import sys
import os

# Isolate from the active fm_agent/ directory — run from a temp dir
work_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    f"_tmp_probe_{os.path.basename(__file__)}",
)
os.makedirs(work_dir, exist_ok=True)
os.chdir(work_dir)

# Add the repo's src/ to the path so we can import configure_llm
repo_src = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"
)
sys.path.insert(0, repo_src)

try:
    from configure_llm import validate_base_url, ConfigWizardError

    # URL with a non-numeric port: syntactically invalid per RFC 3986
    url = "http://example.com:abc"

    actual = None
    raised = False
    try:
        validate_base_url(url)
    except ConfigWizardError:
        raised = True
    except Exception as exc:
        print(f"ERROR: unexpected exception: {exc}")
        sys.exit(1)

    # Spec requires raising ConfigWizardError for syntactically invalid URLs.
    # If the function returned normally (no exception), the bug is confirmed.
    expected_raises = True
    passed = raised != expected_raises  # True → bug reproduced

    if passed:
        print(
            "CONFIRMED — validate_base_url accepted an invalid URL "
            f"(url={url!r}) but the spec requires raising ConfigWizardError"
        )
    else:
        print(
            f"NOT CONFIRMED — validate_base_url correctly raised ConfigWizardError "
            f"for {url!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
