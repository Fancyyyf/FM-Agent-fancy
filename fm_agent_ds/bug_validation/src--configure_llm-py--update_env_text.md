# Bug Report: update_env_text

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string where (1) exactly one line assigns ENV_SECRET_KEY to api_key, positioned where an existing ENV_SECRET_KEY line appeared or appended at the end if absent; (2) lines whose key, after stripping an optional 'export ' prefix, belongs to a predetermined set of legacy LLM configuration keys are excluded from the output; (3) every other line — blank, comment, or assignment — appears verbatim in its original relative order. When an existing ENV_SECRET_KEY line carries an 'export ' prefix, the rewritten line preserves that prefix. When the key is appended and the input contains no non-blank, non-comment lines, header comment lines precede the appended key line.

---

### Actual Behavior

The function returns a string result obtained by transforming the input text (a .env file content) as follows. Let L = text.splitlines(keepends=True). Process each line ℓ ∈ L in order: let s = ℓ.lstrip(). If s is empty or s.startswith('#'), copy ℓ to output. Otherwise, attempt to parse a key-value assignment. Determine leading whitespace and optional 'export ' prefix: let leading = ℓ[:len(ℓ)-len(s)]; if _ENV_EXPORT_PREFIX_RE.match(s) is successful, let export_prefix = leading + match.group(), let working = leading + s[match.end():]; else export_prefix = '', working = ℓ. Split working at the first '=': key_candidate, sep, _ = working.partition('='). If sep == '' (no '='), copy ℓ to output. Otherwise, let env_key = key_candidate.strip(). If env_key == ENV_SECRET_KEY, output the line f\"{export_prefix}ENV_SECRET_KEY={api_key}\\n\" and set a flag key_written = True. If env_key in ENV_LEGACY_LLM_KEYS, omit the line (do not copy). Else, copy ℓ unchanged. After processing all lines, if key_written is False, append the secret line: if the output list is empty, first prepend the two header comment lines: '# fm-agent secrets — gitignored, do not commit.\\n', '# Only the LLM API key belongs here.\\n'; then append the line ENV_SECRET_KEY={api_key}\\n. Otherwise, if the last line in the output has non-empty stripped content, first append a newline '\\n', then append the secret line; if the last line is already blank (only whitespace), just append the secret line. Finally, return the concatenation of all output lines.

---

## Code Evidence

```text
Line 21: if env_key == ENV_SECRET_KEY:
Line 22: new_lines.append(f"{export_prefix}{ENV_SECRET_KEY}={api_key}\n")
Line 23: key_written = True
Line 24: continue
```

---

## Trigger Condition

The code replaces every occurrence of ENV_SECRET_KEY, producing multiple output lines for the secret key when the input contains more than one. The specification requires exactly one line of that key in the output.

---

## How to trigger the bug

When the input `.env` text contains more than one line assigning `ENV_SECRET_KEY` (e.g., `LLM_API_KEY`), the function writes a replacement line for *every* occurrence instead of only the first. The spec requires exactly one `ENV_SECRET_KEY` assignment in the output.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` | `"LLM_API_KEY=first-old-key\nLLM_API_KEY=second-old-key\nOTHER_VAR=keep_me\n"` |
| `api_key` | `"new-test-api-key"` |

### Expected (spec-correct) Output

Only one `LLM_API_KEY=` line should appear.

### Actual (buggy) Output

The output contains `LLM_API_KEY=new-test-api-key` twice.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, 'src')
from configure_llm import update_env_text

text = "LLM_API_KEY=first-old-key\nLLM_API_KEY=second-old-key\nOTHER_VAR=keep_me\n"
result = update_env_text(text, "new-test-api-key")
print(result.count("LLM_API_KEY="))  # 2 — buggy
# expected (correct): 1
```

---

## Probe Script

```python
import sys
import os

# Use a temporary workspace for any runtime artifacts
tmpdir = os.environ.get("TMPDIR", "/tmp")
os.chdir("/home/fancy/Projects_Vault/FM-Agent")

sys.path.insert(0, "src")

try:
    from configure_llm import update_env_text

    # Input with two LLM_API_KEY lines — spec says exactly one should remain
    input_text = (
        "LLM_API_KEY=first-old-key\n"
        "LLM_API_KEY=second-old-key\n"
        "OTHER_VAR=keep_me\n"
    )
    api_key = "new-test-api-key"

    actual = update_env_text(input_text, api_key)

    occurrences = actual.count("LLM_API_KEY=")

    # Spec requires exactly one ENV_SECRET_KEY line in output
    expected_occurrences = 1

    # Bug reproduced if output has != 1 occurrences
    bug_reproduced = occurrences != expected_occurrences

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_reproduced:
    print(
        f"CONFIRMED — LLM_API_KEY= appears {occurrences} times (expected exactly 1). "
        f"Actual output:\n{actual!r}"
    )
else:
    print(
        f"NOT CONFIRMED — LLM_API_KEY= appears {occurrences} time(s), "
        f"which matches the expected count of {expected_occurrences}."
    )
```

### Probe Output

```
CONFIRMED — LLM_API_KEY= appears 2 times (expected exactly 1). Actual output:
'LLM_API_KEY=new-test-api-key\nLLM_API_KEY=new-test-api-key\nOTHER_VAR=keep_me\n'
```
