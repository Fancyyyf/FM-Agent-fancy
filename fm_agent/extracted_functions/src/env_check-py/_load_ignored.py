def _load_ignored(work_dir):
    path = _memory_path(work_dir)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except IOError:
            pass
    return set()
