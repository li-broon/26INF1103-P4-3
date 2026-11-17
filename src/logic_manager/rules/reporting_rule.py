from abc import ABC, abstractmethod


# interface for a rule that decides if a report must be sent to an authority and by when
class ReportingRule(ABC):
    @abstractmethod
    def check(self, report):
        pass