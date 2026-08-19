    def elapsed(self):
        if self.first_event_time is None:
            return None
        end = self.last_event_time or datetime.now(timezone.utc)
        return (end - self.first_event_time).total_seconds()
