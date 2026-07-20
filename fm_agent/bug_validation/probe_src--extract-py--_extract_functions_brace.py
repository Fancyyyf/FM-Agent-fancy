import sys
import os

# Ensure the repo root is on sys.path so `import src.extract` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.extract import _extract_functions_brace, LANG_CONFIG
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

rust_lines = [
    '#[derive(Debug)]',
    'pub fn add(a: i32, b: i32) -> i32 {',
    '    a + b',
    '}',
    '',
    '#[test]',
    'fn test_add() {',
    '    assert_eq!(add(1, 2), 3);',
    '}',
    '',
    'fn main() {',
    '    println!("{}", add(1, 2));',
    '}',
]

lang_key = 'rust'
lang_cfg = LANG_CONFIG['rust']

try:
    result = _extract_functions_brace(rust_lines, lang_key, lang_cfg)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

print(f'Result: {result}')
print(f'Number of functions found: {len(result)}')

names = [name for name, _, _ in result]

# Check that "test_add" is NOT in the results (it has #[test])
test_add_skipped = all(name != 'test_add' for name in names)

# Check that "add" and "main" ARE in the results
add_found = any(name == 'add' for name in names)
main_found = any(name == 'main' for name in names)

all_ok = test_add_skipped and add_found and main_found and len(result) == 2

if all_ok:
    print(f'NOT CONFIRMED — all assertions passed: add_found={add_found}, main_found={main_found}, test_add_skipped={test_add_skipped}, count={len(result)}')
else:
    print(f'CONFIRMED — add_found={add_found}, main_found={main_found}, test_add_skipped={test_add_skipped}, result={result!r}')
