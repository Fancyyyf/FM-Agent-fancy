import sys
sys.path.insert(0, '.')
from src.parser import FunctionSpecMap

# Trigger condition: self.signatures is the same object as self.
# The spec requires: self[function_name] == spec, self.signatures[function_name] == signature.
# When self.signatures is self, the second assignment overwrites the first.

m = FunctionSpecMap()
m.signatures = m  # alias - this is the trigger condition

function_name = 'test_func'
spec_value = 'expected spec value'
sig_value = 'expected sig value'

try:
    m.add_entry(function_name, sig_value, spec_value)
    actual = m[function_name]
    expected = spec_value  # per spec, self[function_name] should be spec
    passed = actual != expected  # True means bug confirmed (spec violated)
except Exception as e:
    print(f'ERROR: {e}', flush=True)
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual self[fn]: {actual!r} | expected spec: {expected!r}', flush=True)
else:
    print(f'NOT CONFIRMED — actual matched expected: self[fn]={actual!r}', flush=True)
