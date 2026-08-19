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
