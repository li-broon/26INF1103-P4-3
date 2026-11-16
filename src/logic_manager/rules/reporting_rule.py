from abc import ABC, abstractmethod


# Interface for a rule that decides if a report must be sent to an authority, and by when.
class ReportingRule(ABC):
    # Return (flag, deadline): flag is "Yes" or "No", deadline is a string.
    @abstractmethod
    def check(self, report):
        pass