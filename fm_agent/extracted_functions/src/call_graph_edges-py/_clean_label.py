def _clean_label(value) -> str:
    text = str(value).strip()
    if not text:
        return ""
    text = text.rstrip(";").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    return text.strip()
