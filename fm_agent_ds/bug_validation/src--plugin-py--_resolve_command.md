# Bug Report: _resolve_command

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/plugin-py/_resolve_command.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string formed by processing each whitespace-delimited token of cmd independently. For each token that starts with "/" or "$": the token is preserved unchanged. For each remaining token: if plugin_root / token resolves to an existing regular file on the filesystem, the token is replaced by the string representation of its absolute path; otherwise, the token is preserved unchanged. The relative order of tokens in the returned string matches the order in cmd.

---

### Actual Behavior

The function returns a string r such that, letting tokens be the list of non-empty strings obtained by splitting the input cmd on whitespace, for each index i, token t = tokens[i], if t starts with '/' or '$' then r contains t at the corresponding position; otherwise, if the path plugin_root / t exists and is a file, r contains the absolute path string of that file; otherwise r contains t unchanged. The tokens are joined by a single space. Formally: Let tokens = cmd.split(); let resolved be a list of strings with length |tokens| such that for all i from 0 to |tokens|-1, (tokens[i].startswith('/')  tokens[i].startswith('$')  resolved[i] = tokens[i])  ((tokens[i].startswith('/')  tokens[i].startswith('$'))  (plugin_root / tokens[i]).is_file()  resolved[i] = str(plugin_root / tokens[i]))  ((tokens[i].startswith('/')  tokens[i].startswith('$'))  (plugin_root / tokens[i]).is_file()  resolved[i] = tokens[i]); then r = ' '.join(resolved).

---

## Code Evidence

Line 10: if token.startswith("/") or token.startswith("$"):

---

## Trigger Condition

The specification (docstring) explicitly states that tokens starting with '/', '$', or '-' must be left unchanged. The code only checks for '/' and '$', omitting the '-' case. Consequently, any token starting with '-' that happens to exist as a file under plugin_root will be replaced by its absolute path, directly violating the required behavior.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| cmd | `"-testfile other_token"` |
| plugin_root | a temp directory containing a file named `-testfile` |

### Expected (spec-correct) Output

`"-testfile other_token"`

### Actual (buggy) Output

`"/tmp/tmpg7ihe4nq/-testfile other_token"` (the `-testfile` token was replaced with its absolute path)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, sys
from pathlib import Path
sys.path.insert(0, "src")
from plugin import _resolve_command

tmpdir = tempfile.TemporaryDirectory()
tmpdir_path = Path(tmpdir.name)
(tmpdir_path / "-testfile").write_text("dummy")
result = _resolve_command("-testfile other_token", tmpdir_path)
print(result)
# actual (buggy) output: '/tmp/tmpXXX/-testfile other_token'
# expected (correct) output: '-testfile other_token'
```

---

## Probe Script

```python
"""Probe script for _resolve_command bug: missing '-' check on line 74.

Spec: Tokens starting with '/', '$', or '-' are left unchanged.
Code: Only checks '/' and '$', omitting '-'.
Bug: A token starting with '-' that exists as a file under plugin_root
     gets replaced by its absolute path instead of being preserved.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

try:
    from plugin import _resolve_command
except ImportError as e:
    print(f"ERROR: Failed to import _resolve_command: {e}")
    sys.exit(1)

try:
    # Create a temp directory with a file whose name starts with '-'
    tmpdir = tempfile.TemporaryDirectory()
    tmpdir_path = Path(tmpdir.name)
    dash_file = tmpdir_path / "-testfile"
    dash_file.write_text("dummy content")

    # Call _resolve_command with the dash-prefixed token
    cmd = "-testfile other_token"
    actual = _resolve_command(cmd, tmpdir_path)

    # Per spec: "-testfile" should be preserved unchanged since it starts with '-'
    # Per buggy code: it will be replaced with its absolute path
    expected = "-testfile other_token"

    if actual != expected:
        print(f"CONFIRMED - actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED - actual matched expected: {actual!r}")

    tmpdir.cleanup()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED - actual: '/tmp/tmpg7ihe4nq/-testfile other_token' | expected: '-testfile other_token'
```
