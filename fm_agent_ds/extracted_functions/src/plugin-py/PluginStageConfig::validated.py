    def validated(self) -> List[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors = []
        if self.type not in ("pass", "replace", "modify"):
            errors.append(
                "stage type must be 'pass', 'replace', or 'modify', "
                f"got '{self.type}'"
            )
        if self.type == "replace" and not self.replace_cmd:
            errors.append("type=replace requires 'replace_cmd'")
        if (
            self.type == "modify"
            and not self.input_md
            and not self.output_process
        ):
            errors.append(
                "type=modify requires at least one of 'input_md' or 'output_process'"
            )
        return errors
