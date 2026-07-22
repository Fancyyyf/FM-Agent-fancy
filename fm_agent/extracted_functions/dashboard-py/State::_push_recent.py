    def _push_recent(self, ts, stage, status, summary):
        when = ts.strftime("%H:%M:%S") if ts else ""
        self.recent_events.appendleft((when, stage, status, summary))
