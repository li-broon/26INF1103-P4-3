from datetime import datetime, timedelta

from ..field_parser import FieldParser
from .reporting_rule import ReportingRule
from ..models.logic_config import LogicConfig

class MomReportingRule(ReportingRule):
    """Decides if an incident must be reported to MOM and works out the deadline."""

    # Shown in the deadline column if no report needed
    NO_DEADLINE = "N/A"

    def __init__(self, severities, deadline_days):
        self._severities = severities
        self._deadline_days = deadline_days

    @classmethod
    def from_config(cls, LogicConfig):
        return cls(LogicConfig.mom_severities, LogicConfig.mom_deadline_days)

    # Returns (mom_reportable, deadline)
    def check(self, report):
        if not self._is_reportable(report):
            return "No", self.NO_DEADLINE

        # Deadline counts from the incident date, if invalid or missing, return a default message
        try:
            incident_date = datetime.strptime(report.get("incident_date"), "%Y-%m-%d")
        except (TypeError, ValueError):
            return "Yes", "Check incident date"

        deadline = incident_date + timedelta(days=self._deadline_days)
        return "Yes", deadline.strftime("%Y-%m-%d")

    # Multi-condition rule: hospitalised OR lost time injury OR high/critical severity
    def _is_reportable(self, report):
        severity = report.get("ai_severity")
        return (
            FieldParser.to_bool(report.get("hospitalised"))
            or FieldParser.to_bool(report.get("lost_time_injury"))
            or (isinstance(severity, str) and severity in self._severities)
        )