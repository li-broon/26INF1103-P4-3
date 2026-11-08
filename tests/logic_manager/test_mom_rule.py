# ------- #
# Imports
# ------- #

from src.logic_manager.rules.mom_reporting_rule import MomReportingRule


# Tests for the MOM Reporting Rule (the Multi-Condition Rule: Hospitalised OR Lost Time Injury OR High/Critical Severity)
class TestMomReportingRule:

    def setup_method(self):
        self._rule = MomReportingRule()

    # Hospitalised Incidents Must be Reported, 10 Days after the Incident
    def test_hospitalised_is_mom_reportable(self):
        flag, deadline = self._rule.check({"hospitalised": True, "incident_date": "2026-10-01"})
        assert flag == "Yes"
        assert deadline == "2026-10-11"

    # Lost Time Injuries Must be Reported
    def test_lost_time_injury_is_mom_reportable(self):
        flag, _ = self._rule.check({"lost_time_injury": True, "incident_date": "2026-10-01"})
        assert flag == "Yes"

    # Critical Severity Must be Reported, even with No Injury
    def test_critical_severity_is_mom_reportable(self):
        flag, _ = self._rule.check({"ai_severity": "Critical", "incident_date": "2026-10-01"})
        assert flag == "Yes"

    # Minor Incidents are Not Reported and Have No Deadline
    def test_minor_incident_is_not_reportable(self):
        flag, deadline = self._rule.check({"hospitalised": False, "lost_time_injury": False,
                                           "ai_severity": "Low", "incident_date": "2026-10-01"})
        assert (flag, deadline) == ("No", "N/A")

    # "true" as Text Must Still Trigger the Report
    def test_text_boolean_triggers_mom_report(self):
        flag, _ = self._rule.check({"hospitalised": "true", "incident_date": "2026-10-01"})
        assert flag == "Yes"

    # A Reportable Incident with a Bad Date is Still Flagged
    def test_bad_date_is_still_flagged(self):
        for date in (None, "", "yesterday", "01/10/2026"):
            flag, deadline = self._rule.check({"hospitalised": True, "incident_date": date})
            assert flag == "Yes", f"date={date!r}"
            assert deadline == "Check incident date", f"date={date!r}"

    # The Deadline Counts Across a Month End (e.g. 25 Oct + 10 Days = 4 Nov)
    def test_deadline_crosses_month_end(self):
        _, deadline = self._rule.check({"hospitalised": True, "incident_date": "2026-10-25"})
        assert deadline == "2026-11-04"
