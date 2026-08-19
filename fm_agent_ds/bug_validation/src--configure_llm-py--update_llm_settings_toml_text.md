# Bug Report: update_llm_settings_toml_text

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Raises ConfigWizardError when updates is empty. Raises ConfigWizardError when any key-value pair in updates fails validation (the key is not a recognized LLM configuration field name, or the value does not conform to the expected format for that field). Raises ConfigWizardError when text is not parseable as valid TOML by the standard library parser, or when text decodes to a non-table TOML value. Otherwise returns a string containing valid TOML in which: for every key in updates, the corresponding field under the [llm] section is set to updates[key]; every other TOML section, every field outside the updated keys, every comment, and all whitespace outside the updated field values is preserved unchanged from text. When text does not contain an [llm] section, a new [llm] section is appended containing all fields from updates.

---

### Actual Behavior

The function update_llm_settings_toml_text either returns a modified TOML string that integrates all desired LLM settings from `updates` into the `[llm]` section of the input `text`, or raises an error if preconditions are violated. More precisely:

- If `updates` is falsy (e.g., empty dict), it raises ConfigWizardError('Provide at least one LLM setting to update.').
- If any (key, value) pair in `updates` fails `validate_llm_setting(key, value)`, the error raised by that function propagates (this error indicates that `key` is unrecognized or `value` does not meet the field's type/format constraints).
- If `text` cannot be parsed as TOML for any reason (i.e., `tomllib.loads(text)` raises a `tomllib.TOMLDecodeError`), it raises ConfigWizardError('Existing fm-agent.toml is invalid TOML; refusing to overwrite it.').
- If `text` decodes successfully but the result is a truthy value that is not a dict (e.g., a string, integer, array), it raises ConfigWizardError('Existing fm-agent.toml must decode to a table/object.').

Otherwise (all checks pass), the function returns a new string `r` that is a valid TOML document, satisfying:
1. `r` contains a `[llm]` section (top-level table).
2. In that `[llm]` section, for every key `k` in `updates`, there is exactly one keyvalue line of the form `{k:<9} = {_quote_toml_string(updates[k])}` (where `_quote_toml_string` produces a TOML-valid quoted string). Any preexisting value for such a key in the original `[llm]` section is replaced; if a key was absent, it is added at the end of the section.
3. All other content of `text` (other sections, comments, formatting, blank lines outside `[llm]`) is preserved in `r`, except that if the original `text` was empty, `r` consists solely of `[llm]\n` followed by the required keyvalue lines (each terminated by a newline).
4. When the original `text` contained an `[llm]` section, any existing LLM keys not mentioned in `updates` remain unchanged in `r`.

---

## Code Evidence

Line 37: kv_match = _KV_RE.match(line)
Line 38: if kv_match and kv_match.group(2) in target:

---

## Trigger Condition

The code uses a regex (_KV_RE) to identify key-value lines. When a key is quoted (e.g., "api_key"), the regex may not match, causing the original line to be treated as a non-key line. The key is not recognized, so the original line is preserved unchanged and the new key-value pair is appended later (lines 44-47). The output contains duplicate keys, which is invalid TOML and does not replace the field as required by the specification.

---

## How to trigger the bug

When the input TOML text uses quoted keys (valid TOML syntax per the TOML spec) under the `[llm]` section, the regex `_KV_RE` on line 365 only matches bare keys (`[A-Za-z0-9_]+`). Quoted keys like `"name"` are not matched, so the original quoted-key line is preserved unchanged in the output, AND a new bare-key line is appended — producing duplicate key entries. The specification requires the old field to be replaced, not duplicated.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` | `'[llm]\n"name" = "old-model"\nprovider = "old-provider"\n'` |
| `updates` | `{"name": "new-model"}` |

### Expected (spec-correct) Output

A TOML string where `"name"` is replaced with `"new-model"` (no duplicate `name` key):

```
[llm]
name      = "new-model"
provider  = "old-provider"
```

### Actual (buggy) Output

The quoted-key line is preserved AND a new bare-key line is appended:

```
[llm]
"name" = "old-model"
provider = "old-provider"
name      = "new-model"
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from configure_llm import update_llm_settings_toml_text

text = '[llm]\n"name" = "old-model"\nprovider = "old-provider"\n'
updates = {"name": "new-model"}
result = update_llm_settings_toml_text(text, updates)
print(result)
# actual (buggy) output: [llm]\n"name" = "old-model"\nprovider = "old-provider"\nname      = "new-model"\n
# expected (correct) output: [llm]\nname      = "new-model"\nprovider = "old-provider"\n
```

---

## Probe Script

```python
import sys
import os

# The probe is run from the repo root. Ensure src/ is importable.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_project_root, 'src'))

try:
    from configure_llm import update_llm_settings_toml_text
except Exception as e:
    print(f'ERROR importing module: {e}')
    sys.exit(1)

# Test: input TOML with quoted key "name" under [llm]
# The spec says the old value should be replaced with the new one.
# The bug: _KV_RE regex only matches bare keys [A-Za-z0-9_]+,
# so quoted keys like "name" are not recognized. The old line
# is preserved AND a new bare-key line is appended — producing duplicates.
text = '[llm]\n"name" = "old-model"\nprovider = "old-provider"\n'
updates = {"name": "new-model"}

try:
    actual = update_llm_settings_toml_text(text, updates)
except Exception as e:
    print(f'ERROR calling function: {e}')
    sys.exit(1)

# Count how many lines set "name" (either quoted or bare)
name_lines = [l for l in actual.split('\n') if l.strip() and 'name' in l and '=' in l]
duplicate_keys = len(name_lines) > 1

if duplicate_keys:
    print(f'CONFIRMED — duplicate "name" keys found in output ({len(name_lines)} occurrences)')
    print(f'  Actual output: {actual!r}')
    print(f'  Expected: single "name" key with value "new-model"')
else:
    print(f'NOT CONFIRMED — no duplicate keys found: {actual!r}')
```

### Probe Output

```
CONFIRMED — duplicate "name" keys found in output (2 occurrences)
  Actual output: '[llm]\n"name" = "old-model"\nprovider = "old-provider"\nname      = "new-model"\n'
  Expected: single "name" key with value "new-model"
```
