def backup_file(
    path: Path,
    now: datetime | None = None,
    *,
    private: bool = False,
) -> Path | None:
    if not path.exists():
        return None
    now = now or datetime.now()
    suffix = now.strftime("%Y%m%d-%H%M%S")
    if private:
        backup_dir = _private_backup_root()
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.chmod(0o700)
        path_slug = str(path.parent.resolve()).strip(os.sep).replace(os.sep, "_") or "project"
        backup_base = backup_dir / f"{path_slug}__{path.name}.bak.{suffix}"
    else:
        backup_base = path.with_name(f"{path.name}.bak.{suffix}")

    # Reserve a distinct destination before copying so rapid or concurrent
    # configuration changes never overwrite an earlier backup.
    mode = 0o600 if private or path.name == ".env" else 0o644
    attempt = 0
    while True:
        backup = (
            backup_base
            if attempt == 0
            else backup_base.with_name(f"{backup_base.name}.{attempt}")
        )
        try:
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        except FileExistsError:
            attempt += 1
            continue
        else:
            os.close(fd)
            break

    try:
        shutil.copy2(path, backup)
    except Exception:
        backup.unlink(missing_ok=True)
        raise
    if private or path.name == ".env":
        backup.chmod(0o600)
    return backup
