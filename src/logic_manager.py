# ------- #
# Imports
# ------- #

import json
from src.data_manager import save_record


# ------------------- #
# Weight Configuration
# ------------------- #
 
# Weight for each possible value of "ai_severity" - how severe the AI judged
# the incident to be overall.
SEVERITY_WEIGHTS = {
    "Low": 1,
    "Medium": 4,
    "High": 7,
    "Critical": 10,
}
 
# Weight for each possible value of "root_cause_category" - reflects how
# inherently dangerous that TYPE of cause tends to be in general, regardless
# of what actually happened this time.
ROOT_CAUSE_WEIGHTS = {
    "Electrical": 8,
    "Chemical": 9,
    "Fall from Height": 8,
    "Struck by Object": 6,
    "Machinery": 7,
    "Slip or Trip": 3,
    "Fire": 9,
    "Water": 4,
    "Safety Procedure Breach": 6,
    "Other": 2,
}
 
# Weight for "hospitalised" (true/false).
HOSPITALISED_WEIGHTS = {
    True: 10,
    False: 0,
}
 
# Weight for "is_near_miss" (true/false) - a near miss still needs
# follow-up, but less urgently than an incident where something actually
# happened.
NEAR_MISS_WEIGHTS = {
    True: 2,
    False: 0,
}
 
# Weight for "lost_time_injury" (true/false) - whether the injured person
# cannot work their next shift.
LOST_TIME_INJURY_WEIGHTS = {
    True: 8,
    False: 0,
}
 
# How much each field contributes to the final importance score. Every
# field below is looked up in its *_WEIGHTS dict above and then multiplied
# by its importance here - tweak these to rebalance which signals matter
# most, without touching the weight tables themselves.
FIELD_IMPORTANCE = {
    "ai_severity": 2.0,
    "root_cause_category": 1.5,
    "hospitalised": 1.5,
    "is_near_miss": 1.0,
    "lost_time_injury": 1.5,
    "work_stoppage_hours": 0.2,  # applied directly to the hours, not via a *_WEIGHTS dict
}

# ------------------------------ #
# logic_manager Private Functions
# ------------------------------ #

# Work Out How Important the Report is (TODO: add the team's weights for each field)
def _calculate_importance_score(report):
    score = 0
 
    score += SEVERITY_WEIGHTS.get(report.get("ai_severity"), 0) * FIELD_IMPORTANCE["ai_severity"]
    score += ROOT_CAUSE_WEIGHTS.get(report.get("root_cause_category"), 0) * FIELD_IMPORTANCE["root_cause_category"]
    score += HOSPITALISED_WEIGHTS.get(report.get("hospitalised"), 0) * FIELD_IMPORTANCE["hospitalised"]
    score += NEAR_MISS_WEIGHTS.get(report.get("is_near_miss"), 0) * FIELD_IMPORTANCE["is_near_miss"]
    score += LOST_TIME_INJURY_WEIGHTS.get(report.get("lost_time_injury"), 0) * FIELD_IMPORTANCE["lost_time_injury"]
 
    # work_stoppage_hours is already numeric, so it's scaled directly instead
    # of looked up in a dict (a dict can't cover every possible hour value).
    try:
        hours = float(report.get("work_stoppage_hours") or 0)
    except (TypeError, ValueError):
        hours = 0
 
    score += hours * FIELD_IMPORTANCE["work_stoppage_hours"]
 
    return round(score, 2)

# Add the Score to the Report and Send it to 'data_manager' to be Saved
def _save_with_score(report, score):
    record = dict(report)  # Copied, so the Original Report is not Changed
    record["importance_score"] = score
    save_record(record)

# --------------------------- #
# logic_manager Main Functions
# --------------------------- #

def logic(json_result):
    print(json.dumps(json_result, indent=2, ensure_ascii=False))  # TEMP: check final JSON
    score = _calculate_importance_score(json_result)
    _save_with_score(json_result, score)
