import sys
from unittest.mock import MagicMock

try:
    import src.languages.rust
    import src.languages.codegraph

    # Save original for cleanup
    _original = src.languages.rust.CodeGraphExtractor

    # Patch CodeGraphExtractor to return a result with an empty list for one file
    mock_extractor_cls = MagicMock()
    mock_cg = MagicMock()
    mock_cg.get_functions_by_file.return_value = {
        "/proj/src/lib.rs": [("add", "fn add() { 1 + 2 }")],
        "/proj/src/empty.rs": [],  # file with zero functions -> empty list, violates spec
    }
    mock_extractor_cls.from_proj_dir.return_value = mock_cg
    src.languages.rust.CodeGraphExtractor = mock_extractor_cls

    result = src.languages.rust.batch_extract("/proj")

    # Restore original
    src.languages.rust.CodeGraphExtractor = _original

    has_empty = any(isinstance(v, list) and len(v) == 0 for v in result.values())

    if has_empty:
        actual_empty_files = [k for k, v in result.items() if isinstance(v, list) and len(v) == 0]
        print(
            f'CONFIRMED — spec requires every value be a non-empty list, '
            f'but these files have empty lists: {actual_empty_files!r}. '
            f'Full result: {result!r}'
        )
    else:
        print(f'NOT CONFIRMED — no empty lists found: {result!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
