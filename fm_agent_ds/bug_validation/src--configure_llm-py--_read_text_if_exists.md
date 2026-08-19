# Bug Report: _read_text_if_exists

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_read_text_if_exists.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the full contents of the file at path decoded as UTF-8 text when the file exists and the process has permission to read it. Returns an empty string when the file at path does not exist.

---

### Actual Behavior

Natural language: If the file does not exist, the function returns an empty string. If it exists and can be read, the function returns the file's contents decoded with UTF-8. If an OSError (e.g., PermissionError, FileNotFoundError from a race) occurs during reading, that exception is raised. The path argument is not modified. Formal logic: ( (path.exists() -> (return_value = path.read_text(encoding='utf-8') if no OSError) )  (path.exists() -> return_value = "") )  (exception is OSError). More precisely: post: (return_value = ""  path.exists())  ( s: str, s = path.read_text(encoding='utf-8')  return_value = s  path.exists())  ( e: OSError, raised e).

---

## Code Evidence

Line 4: return path.read_text(encoding="utf-8")

---

## Trigger Condition

The specification requires that when the file exists and the process has permission to read it, the function returns the file's contents decoded as UTF8 text. For a file containing invalid UTF8 bytes, read_text raises a UnicodeDecodeError instead of returning a string, violating the specification's return guarantee.

---

## How to trigger the bug

The function `_read_text_if_exists` delegates to `pathlib.Path.read_text(encoding="utf-8")`. When the target file exists but contains invalid UTF-8 byte sequences, `read_text` raises `UnicodeDecodeError` rather than returning a string. The specification states the function returns the file contents — it makes no allowance for a `UnicodeDecodeError` being raised, which contradicts the spec's return guarantee.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` | A `pathlib.Path` pointing to a file containing invalid UTF-8 bytes (e.g., `b'\xff\xfe'`) |

### Expected (spec-correct) Output

A string containing the file contents (the spec claims the function always returns the file contents as a string when the file exists).

### Actual (buggy) Output

`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 5: invalid start byte`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.configure_llm import _read_text_if_exists

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "bad.bin"
    test_file.write_bytes(b"hello\xff\xfeworld")
    result = _read_text_if_exists(test_file)
    # Raises UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path


def main() -> None:
    # Add project's src/ to path to import configure_llm as a module
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root / "src"))

    try:
        from configure_llm import _read_text_if_exists  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"ERROR: cannot import configure_llm: {exc}")
        sys.exit(1)

    # Create a temp directory for the invalid-UTF-8 fixture
    with tempfile.TemporaryDirectory() as tmpdir:
        # Invalid UTF-8 bytes: 0xFF is never valid in UTF-8
        invalid_utf8 = b"hello\xff\xfeworld"
        test_file = Path(tmpdir) / "invalid_utf8.bin"
        test_file.write_bytes(invalid_utf8)

        assert test_file.exists(), "fixture file must exist"

        try:
            actual = _read_text_if_exists(test_file)
            # If we reach here, no exception was raised
            print(
                f"NOT CONFIRMED — function returned without error: {actual!r}"
            )
        except UnicodeDecodeError as exc:
            # Bug confirmed: spec says "returns the file's contents",
            # but UnicodeDecodeError was raised for invalid UTF-8 bytes.
            print(
                f"CONFIRMED — UnicodeDecodeError raised for file with invalid UTF-8 bytes: {exc}"
            )
        except Exception as exc:
            print(
                f"ERROR: unexpected exception {type(exc).__name__}: {exc}"
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — UnicodeDecodeError raised for file with invalid UTF-8 bytes: 'utf-8' codec can't decode byte 0xff in position 5: invalid start byte
```
