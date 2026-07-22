    def _verify(rel):
        fpath = os.path.join(extracted_dir, rel)
        language = _VERIFY_EXT_TO_LANG.get(os.path.splitext(fpath)[1], "C")
        _, verdict = _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir=work_dir)
        return rel, verdict
