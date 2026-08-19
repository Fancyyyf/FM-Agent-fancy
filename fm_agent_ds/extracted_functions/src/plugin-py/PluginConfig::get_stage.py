    def get_stage(self, stage_name: str) -> Optional[PluginStageConfig]:
        """Return the stage config for *stage_name*, or None if not configured."""
        return self.stages.get(stage_name)
