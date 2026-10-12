# Imports

import json
from datetime import datetime, timedelta
from src.data_manager import save_record

# Weight Configuration

# Weight for each possible value that the AI can return for ai_severity
SEVERITY_WEIGHTS = {
    "Low": 1,
    "Medium": 4,
    "High": 7,
    "Critical": 10,
}

# Weight for each possible value of that the AI can return for root_cause_category
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

# Weight for hospitalised (true/false)
HOSPITALISED_WEIGHTS = {
    True: 5,
    False: 10,
}

# Weight for is_near_miss (true/false) 
NEAR_MISS_WEIGHTS = {
    True: 2,
    False: 0,
}

# Weight for lost_time_injury (true/false)
LOST_TIME_INJURY_WEIGHTS = {
    True: 8,
    False: 2,
}

# The importance score is capped at this value
MAX_SCORE = 10

# Work stoppage hours above this number will not increase the importance score 
MAX_STOPPAGE_HOURS = 24

# How much each field contributes to the final importance score

FIELD_IMPORTANCE = {
    "ai_severity": 0.30,
    "root_cause_category": 0.20,
    "hospitalised": 0.20,
    "is_near_miss": 0.10,
    "lost_time_injury": 0.20,
    "work_stoppage_hours": 0.05,  # applied directly to the hours
}

# MOM Reporting Configuration

# A report is flagged for MOM if the severity is high or above
MOM_REPORTABLE_SEVERITIES = {"Critical", "High"}

# Days after the incident date which report must be submitted
MOM_DEADLINE_DAYS = 10

# Shown in the deadline column if no report needed
NO_DEADLINE = "N/A"

# logic_manager Private Functions

# Convert a AI generated value to a boolean
def _to_bool(value):
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)

# Work Out How Important the Report
def _calculate_importance_score(report):
    # An empty report has no data to score (missing fields would otherwise count as False)
    if not report:
        return 0

    score = 0

    score += SEVERITY_WEIGHTS.get(report.get("ai_severity"), 0) * FIELD_IMPORTANCE["ai_severity"]
    score += ROOT_CAUSE_WEIGHTS.get(report.get("root_cause_category"), 0) * FIELD_IMPORTANCE["root_cause_category"]
    score += HOSPITALISED_WEIGHTS.get(_to_bool(report.get("hospitalised")), 0) * FIELD_IMPORTANCE["hospitalised"]
    score += NEAR_MISS_WEIGHTS.get(_to_bool(report.get("is_near_miss")), 0) * FIELD_IMPORTANCE["is_near_miss"]
    score += LOST_TIME_INJURY_WEIGHTS.get(_to_bool(report.get("lost_time_injury")), 0) * FIELD_IMPORTANCE["lost_time_injury"]

    # work_stoppage_hours is scaled directly 
    try:
        hours = float(report.get("work_stoppage_hours") or 0)
    except (TypeError, ValueError):
        hours = 0

    hours = max(0, min(hours, MAX_STOPPAGE_HOURS))  # No negatives, and capped
    score += hours * FIELD_IMPORTANCE["work_stoppage_hours"]

    return round(min(score, MAX_SCORE), 2)

# Decides if the incident should be reported to mom and calculates the deadline if so
def _check_mom_reporting(report):
    reportable = (
        _to_bool(report.get("hospitalised"))
        or _to_bool(report.get("lost_time_injury"))
        or report.get("ai_severity") in MOM_REPORTABLE_SEVERITIES
    )
    if not reportable:
        return "No", NO_DEADLINE

    # Deadline counts from the incident date, if deadline is invalid or missing, return a default message
    try:
        incident_date = datetime.strptime(report.get("incident_date"), "%Y-%m-%d")
    except (TypeError, ValueError):
        return "Yes", "Check incident date"

    deadline = incident_date + timedelta(days=MOM_DEADLINE_DAYS)
    return "Yes", deadline.strftime("%Y-%m-%d")

# Add the Score and MOM Details to the Report and Send it to 'data_manager' to be Saved
def _save_with_score(report, score, mom_reportable, deadline):
    record = dict(report)  
    record["importance_score"] = score
    record["mom_reportable"] = mom_reportable
    record["deadline"] = deadline
    save_record(record)


# logic_manager Main Functions


def logic(json_result):
    print(json.dumps(json_result, indent=2, ensure_ascii=False))  
    score = _calculate_importance_score(json_result)
    mom_reportable, deadline = _check_mom_reporting(json_result)
    _save_with_score(json_result, score, mom_reportable, deadline)