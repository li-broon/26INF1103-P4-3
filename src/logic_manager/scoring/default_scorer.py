from src.logic_manager.scoring.factors.boolean_factor import BooleanFactor
from src.logic_manager.scoring.factors.choice_factor import ChoiceFactor
from src.logic_manager.config import (
    FIELD_IMPORTANCE,
    HOSPITALISED_WEIGHTS,
    LOST_TIME_INJURY_WEIGHTS,
    MAX_SCORE,
    MAX_STOPPAGE_HOURS,
    NEAR_MISS_WEIGHTS,
    ROOT_CAUSE_WEIGHTS,
    SEVERITY_WEIGHTS,
)
from src.logic_manager.scoring.factors.hours_factor import HoursFactor
from src.logic_manager.scoring.importance_scorer import ImportanceScorer


# Builds the scorer with the weights configured in config.py
def build_default_scorer():
    return ImportanceScorer(
        factors=[
            ChoiceFactor("ai_severity", FIELD_IMPORTANCE["ai_severity"], SEVERITY_WEIGHTS),
            ChoiceFactor("root_cause_category", FIELD_IMPORTANCE["root_cause_category"], ROOT_CAUSE_WEIGHTS),
            BooleanFactor("hospitalised", FIELD_IMPORTANCE["hospitalised"], *HOSPITALISED_WEIGHTS),
            BooleanFactor("is_near_miss", FIELD_IMPORTANCE["is_near_miss"], *NEAR_MISS_WEIGHTS),
            BooleanFactor("lost_time_injury", FIELD_IMPORTANCE["lost_time_injury"], *LOST_TIME_INJURY_WEIGHTS),
            HoursFactor("work_stoppage_hours", FIELD_IMPORTANCE["work_stoppage_hours"], MAX_STOPPAGE_HOURS),
        ],
        max_score=MAX_SCORE,
    )
