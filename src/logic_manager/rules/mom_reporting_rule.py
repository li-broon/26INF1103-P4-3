from datetime import datetime, timedelta

from .config import MOM_DEADLINE_DAYS, MOM_REPORTABLE_SEVERITIES, NO_DEADLINE
from .helpers import to_bool


class MomReportingRule:
    """Decides if an incident must be reported to MOM and works out the deadline."""

    def __init__(self, severities=MOM_REPORTABLE_SEVERITIES, deadline_days=MOM_DEADLINE_DAYS):
        self._severities = severities
        self._deadline_days = deadline_days

    # Returns (mom_reportable, deadline)
    def check(self, report):
        if not self._is_reportable(report):
            return "No", NO_DEADLINE

        # Deadline counts from the incident date, if invalid or missing, return a default message
        try:
            incident_date = datetime.strptime(report.get("incident_date"), "%Y-%m-%d")
        except (TypeError, ValueError):
            return "Yes", "Check incident date"

        deadline = incident_date + timedelta(days=self._deadline_days)
        return "Yes", deadline.strftime("%Y-%m-%d")

    def _is_reportable(self, report):
        return (
            to_bool(report.get("hospitalised"))
            or to_bool(report.get("lost_time_injury"))
            or report.get("ai_severity") in self._severities
        )
