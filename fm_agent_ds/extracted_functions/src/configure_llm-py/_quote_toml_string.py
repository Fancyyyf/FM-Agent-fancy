def _quote_toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
