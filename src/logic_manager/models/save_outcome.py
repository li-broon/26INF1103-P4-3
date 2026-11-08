from dataclasses import dataclass


@dataclass
class SaveOutcome:
    saved: bool
    message: str
    importance_score: float
    mom_reportable: str
    deadline: str
