from abc import ABC, abstractmethod


class ReportingRule(ABC):
    """Interface for a rule that decides if a report must be sent to an authority, and by when."""

    @abstractmethod
    def check(self, report):
        """Return (flag, deadline): flag is "Yes" or "No", deadline is a string."""