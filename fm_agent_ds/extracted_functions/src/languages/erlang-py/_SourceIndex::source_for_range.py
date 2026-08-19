    def source_for_range(self, lsp_range: dict) -> str:
        start = self.position_to_offset(lsp_range["start"])
        end = self.position_to_offset(lsp_range["end"])
        return self.source[start:end]
