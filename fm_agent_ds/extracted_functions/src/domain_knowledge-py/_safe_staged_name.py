def _safe_staged_name(source_path, used_names):
    basename = os.path.basename(source_path)
    stem, ext = os.path.splitext(basename)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "knowledge"
    ext = ext.lower()
    candidate = f"{stem}{ext}"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    index = 2
    while True:
        candidate = f"{stem}_{index}{ext}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        index += 1
