import sys
import os
from types import SimpleNamespace

# Add repo root to path so the package entry point resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import src.env_check as env_check
except Exception as e:
    print(f"ERROR: failed to import package: {e}")
    sys.exit(1)

# config.LLM_API_KEY is a truthy non-string value (integer 42).
# The specification requires LLM_API_KEY to be a non-empty *string*,
# so a non-string value should yield (False, error_message).
# The actual code only checks truthiness, so it will return (True, None).
config = SimpleNamespace(LLM_API_KEY=42)

try:
    actual = env_check._check_llm_api_key(config)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Spec-correct expected output: False because 42 is not a string
expected = (False, "LLM_API_KEY is not set in .env file")
passed = actual != expected

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
