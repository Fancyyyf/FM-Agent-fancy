def _escape_component(value: str) -> str:
    result = []
    for char in value:
        if char.isascii() and (char.isalnum() or char == "_"):
            result.append(char)
        else:
            result.append(f"_{ord(char):02x}")
    return "".join(result)
