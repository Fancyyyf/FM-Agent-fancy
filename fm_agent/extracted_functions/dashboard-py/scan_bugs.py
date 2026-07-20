# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/scan_bugs.py
#
# State.scan_bugs(self) -> None
#
# Pre-condition:
#   - self.bug_dir is a Path object pointing to a directory that may contain
#     *.result.json files.
#   - self.stage_counts is a dict mapping stage name strings to dicts whose
#     values are integers representing operation counts per status.
#
# Post-condition:
#   - self.bugs_confirmed equals the number of *.result.json files in
#     self.bug_dir whose parsed "confirmation_status" field, after
#     lowercasing, contains the substring "confirm".
#   - self.bugs_not_confirmed equals the number of remaining *.result.json
#     files in self.bug_dir — those whose parsed "confirmation_status"
#     field, after lowercasing, does NOT contain "confirm", including files
#     where the field is absent, the file cannot be read, or the content is
#     not valid JSON.
#   - self.bugs_pending equals max(0, C - (self.bugs_confirmed +
#     self.bugs_not_confirmed)), where C is the sum of all integer values
#     under self.stage_counts["bug_validation"], or 0 if the key
#     "bug_validation" is absent from self.stage_counts.
#   - If self.bug_dir does not exist, self.bugs_confirmed,
#     self.bugs_not_confirmed, and self.bugs_pending are all set to 0 and
#     no directory scanning occurs.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def scan_bugs(self):
        self.bugs_confirmed = 0
        self.bugs_not_confirmed = 0
        if not self.bug_dir.exists():
            return
        for path in self.bug_dir.glob("*.result.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                continue
            status = (d.get("confirmation_status") or "").lower()
            if "not" in status:
                self.bugs_not_confirmed += 1
            elif "confirm" in status:
                self.bugs_confirmed += 1
            else:
                self.bugs_not_confirmed += 1  # treat unknown as not confirmed
        # pending = bug_validation opencode_calls with success status, minus results files
        bv = self.stage_counts.get("bug_validation", {})
        bv_done = sum(bv.values())
        self.bugs_pending = max(0, bv_done - (self.bugs_confirmed + self.bugs_not_confirmed))
