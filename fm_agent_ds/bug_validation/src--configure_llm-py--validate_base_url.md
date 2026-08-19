# Bug Report: validate_base_url

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/validate_base_url.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Raises ConfigWizardError when url is not a syntactically valid absolute URL whose scheme is either 'http' or 'https'. Returns with no effect when url is a syntactically valid absolute URL with scheme 'http' or 'https'.

---

### Actual Behavior

If the function returns normally (does not raise an exception), then the parsed URL has scheme 'http' or 'https' and a non-empty network location (netloc). Otherwise, a ConfigWizardError is raised with a message indicating the URL is invalid. Formally: ( url: str, url  ''  url == url.strip()  (after execution: (raised_exception  urlparse(url).scheme  {'http','https'}  urlparse(url).netloc  '')  (raised_exception  raised_exception is ConfigWizardError  raised_exception.args[0] starts with 'Base URL must be an absolute http(s) URL, got:'))

---

## Code Evidence

```
Line 2: parsed = urlparse(url)
Line 3: if parsed.scheme not in ("http", "https") or not parsed.netloc:
```

---

## Trigger Condition

The code only checks that the scheme is http/https and that netloc is non-empty, but does not validate that the netloc forms a syntactically valid authority (e.g., port must be numeric, hostname must not contain spaces). A URL like 'http://example.com:abc' (port with letters) is not syntactically valid according to RFC 3986, yet the code accepts it because urlparse sets netloc='example.com:abc' which is non-empty. The specification requires raising ConfigWizardError for any non-syntactically-valid absolute URL, so this input violates the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| url | `"http://example.com:abc"` |

### Expected (spec-correct) Output

`ConfigWizardError` raised: the URL has a non-numeric port (`abc`), which makes it syntactically invalid per RFC 3986. The spec requires raising `ConfigWizardError` for any non-syntactically-valid absolute URL.

### Actual (buggy) Output

No exception raised — the function returns `None` normally. The code only checks that `urlparse(url).scheme` is `"http"` or `"https"` and that `urlparse(url).netloc` is non-empty (`"example.com:abc"` is non-empty), so the invalid port is not detected.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, 'src')
from configure_llm import validate_base_url, ConfigWizardError

try:
    validate_base_url("http://example.com:abc")
    print("BUG: no exception raised for invalid URL")
except ConfigWizardError:
    print("OK: correctly rejected invalid URL")
# actual (buggy) output: BUG: no exception raised for invalid URL
# expected (correct) output: OK: correctly rejected invalid URL
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — validate_base_url accepted an invalid URL (url='http://example.com:abc') but the spec requires raising ConfigWizardError
```
