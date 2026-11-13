from dataclasses import dataclass


# What process() hands back to the interface: whether the report was saved, why not if it was not, and what the rules decided.
@dataclass
class SaveOutcome:
    saved: bool
    message: str
    importance_score: float
    mom_reportable: str
    deadline: str
    priority: str = ""