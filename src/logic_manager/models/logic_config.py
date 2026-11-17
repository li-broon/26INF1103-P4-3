import json
from dataclasses import dataclass, field, fields


# all the weight, threshold and deadline values the Logic Manager uses
@dataclass(frozen=True)
class LogicConfig:
    # Weight for each value the AI can return for ai_severity / root_cause_category
    severity_weights: dict = field(default_factory=lambda: {
        "Low": 1, "Medium": 4, "High": 7, "Critical": 10,
    })
    root_cause_weights: dict = field(default_factory=lambda: {
        "Electrical": 8, "Chemical": 9, "Fall from Height": 8, "Struck by Object": 6,
        "Machinery": 7, "Slip or Trip": 3, "Fire": 9, "Water": 4,
        "Safety Procedure Breach": 6, "Other": 2,
    })

    # (weight if True, weight if False) for the true/false fields
    hospitalised_weights: tuple = (5, 10)
    near_miss_weights: tuple = (2, 0)
    lost_time_injury_weights: tuple = (8, 1)

    # how much each field contributes to the final importance score
    field_importance: dict = field(default_factory=lambda: {
        "ai_severity": 0.30,
        "root_cause_category": 0.20,
        "hospitalised": 0.20,
        "is_near_miss": 0.10,
        "lost_time_injury": 0.20,
        "work_stoppage_hours": 0.05,  
    })

    # the importance score is capped at this value
    max_score: float = 10
    # work stoppage hours above this number will not increase the importance score
    max_stoppage_hours: float = 24

    # minimum importance score for each priority band 
    priority_bands: dict = field(default_factory=lambda: {
        "Urgent": 7.0, "Elevated": 4.0, "Routine": 0.0,
    })

    # a report is flagged for MOM if the severity is in this set
    mom_severities: frozenset = frozenset({"Critical", "High"})
    # days after the incident date which the MOM report must be submitted
    mom_deadline_days: int = 10

    # function to load overrides from a JSON file. A missing or corrupt file, or a bad value,
    # falls back to the defaults instead of crashing.
    @classmethod
    def from_json(cls, path):
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()

        defaults = cls()
        overrides = {}
        for item in fields(cls):
            if item.name not in data:
                continue
            ok, value = cls._coerce(getattr(defaults, item.name), data[item.name])
            if ok:
                overrides[item.name] = value
        return cls(**overrides)

    # check a JSON value has the same shape as the default
    @staticmethod
    def _coerce(default, value):
        def is_number(item):
            return isinstance(item, (int, float)) and not isinstance(item, bool)

        if isinstance(default, dict):
            ok = isinstance(value, dict) and all(is_number(v) for v in value.values())
            return ok, value
        if isinstance(default, tuple):
            ok = isinstance(value, (list, tuple)) and len(value) == len(default) and all(is_number(v) for v in value)
            return ok, tuple(value) if ok else None
        if isinstance(default, frozenset):
            ok = isinstance(value, (list, tuple, set)) and all(isinstance(v, str) for v in value)
            return ok, frozenset(value) if ok else None
        return is_number(value), value

