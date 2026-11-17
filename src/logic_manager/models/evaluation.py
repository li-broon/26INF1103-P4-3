from dataclasses import dataclass, field


# business rules decision for one report
@dataclass
class Evaluation:
    importance_score: float
    mom_reportable: str
    deadline: str
    priority: str
    score_breakdown: dict = field(default_factory=dict)

    # fields added to the report before it is saved
    def record_fields(self):
        return {
            "importance_score": self.importance_score,
            "mom_reportable": self.mom_reportable,
            "deadline": self.deadline,
            "priority": self.priority,
        }