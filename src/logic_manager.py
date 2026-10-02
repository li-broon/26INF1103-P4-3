# ------- #
# Imports
# ------- #

import json
from datetime import datetime
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
    True: 0,
    False: 10,
}
 
# Weight for "is_near_miss" (true/false) - a near miss still needs
# follow-up, but less urgently than an incident where something actually
# happened.
NEAR_MISS_WEIGHTS = {
    True: 2,
    False: 0,
}

INJURY_STATUS_WEIGHTS = {
    "no injury": 0,
}

IMMEDIATE_ACTION_WEIGHTS = {
    True: 2,
    False: 0,
}

RECENCY_MAX_WEIGHT = 10
RECENCY_WINDOW_DAYS = 30
 
# How much each field contributes to the final importance score. Numeric
# values from the weight tables or date/time calculations are multiplied
# by these values to rebalance each signal.
FIELD_IMPORTANCE = {
    "incident_date": 1.0,
    "incident_time": 1.0,
    "injury_status": 1.5,
    "immediate_action_taken": 1.0,
    "ai_severity": 2.0,
    "root_cause_category": 1.5,
    "hospitalised": 1.5,
    "is_near_miss": 1.0,
}

# ------------------------------ #
# logic_manager Private Functions
# ------------------------------ #

# Work Out How Important the Report is (TODO: add the team's weights for each field)
def _calculate_importance_score(report):
    score = 0

    try:
        incident_date = datetime.strptime(report.get("incident_date"), "%Y-%m-%d").date()
        age_days = max((datetime.now().date() - incident_date).days, 0)
        date_weight = max(0, RECENCY_MAX_WEIGHT * (1 - age_days / RECENCY_WINDOW_DAYS))
    except (TypeError, ValueError):
        date_weight = 0
    score += date_weight * FIELD_IMPORTANCE["incident_date"]

    try:
        incident_time = datetime.strptime(report.get("incident_time"), "%H:%M")
        time_weight = incident_time.hour * 60 / (24 * 60) + incident_time.minute / (24 * 60)
    except (TypeError, ValueError):
        time_weight = 0
    score += time_weight * FIELD_IMPORTANCE["incident_time"]

    injury_status = str(report.get("injury_status") or "").strip().casefold()
    injury_weight = INJURY_STATUS_WEIGHTS.get(
        injury_status,
        8 if injury_status else 0,
    )
    score += injury_weight * FIELD_IMPORTANCE["injury_status"]

    action_taken = bool(str(report.get("immediate_action_taken") or "").strip())
    score += IMMEDIATE_ACTION_WEIGHTS[action_taken] * FIELD_IMPORTANCE["immediate_action_taken"]

    score += SEVERITY_WEIGHTS.get(report.get("ai_severity"), 0) * FIELD_IMPORTANCE["ai_severity"]
    score += ROOT_CAUSE_WEIGHTS.get(report.get("root_cause_category"), 0) * FIELD_IMPORTANCE["root_cause_category"]
    score += HOSPITALISED_WEIGHTS.get(report.get("hospitalised"), 0) * FIELD_IMPORTANCE["hospitalised"]
    score += NEAR_MISS_WEIGHTS.get(report.get("is_near_miss"), 0) * FIELD_IMPORTANCE["is_near_miss"]
 
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
