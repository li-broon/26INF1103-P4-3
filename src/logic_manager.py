# ------- #
# Imports
# ------- #

import json
from datetime import datetime, timedelta
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

# The importance score is capped at this value.
MAX_SCORE = 10

# Work stoppage hours above this number stop adding to the score, so one very
# long stoppage cannot push the total past the cap on its own.
MAX_STOPPAGE_HOURS = 24

# How much each field contributes to the final importance score. Every
# field below is looked up in its *_WEIGHTS dict above and then multiplied
# by its importance here - tweak these to rebalance which signals matter
# most, without touching the weight tables themselves.
#
# Worst case for each field (highest weight x importance):
#   ai_severity          10 x 0.30 = 3.0
#   root_cause_category   9 x 0.20 = 1.8
#   hospitalised         10 x 0.20 = 2.0
#   is_near_miss          2 x 0.10 = 0.2
#   lost_time_injury      8 x 0.20 = 1.6
#   work_stoppage_hours  24 x 0.05 = 1.2
#   Total                            9.8  (under the cap of 10)
FIELD_IMPORTANCE = {
    "ai_severity": 0.30,
    "root_cause_category": 0.20,
    "hospitalised": 0.20,
    "is_near_miss": 0.10,
    "lost_time_injury": 0.20,
    "work_stoppage_hours": 0.05,  # applied directly to the hours, not via a *_WEIGHTS dict
}

# ------------------------ #
# MOM Reporting Configuration
# ------------------------ #

# A report is flagged for MOM if the injured person was hospitalised, or
# cannot work their next shift, or the AI judged the severity to be one of
# these. Add "High" to the set to flag High severity incidents too.
MOM_REPORTABLE_SEVERITIES = {"Critical"}

# Days after the incident date by which the safety officer must report to MOM.
MOM_DEADLINE_DAYS = 10

# Shown in the deadline column when the incident does not need reporting.
NO_DEADLINE = "N/A"

# ------------------------------ #
# logic_manager Private Functions
# ------------------------------ #

# The AI sometimes sends booleans as the text "true"/"false", so convert them
# before looking them up in the weight tables.
def _to_bool(value):
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)

# Work Out How Important the Report is (0 to MAX_SCORE)
def _calculate_importance_score(report):
    score = 0

    score += SEVERITY_WEIGHTS.get(report.get("ai_severity"), 0) * FIELD_IMPORTANCE["ai_severity"]
    score += ROOT_CAUSE_WEIGHTS.get(report.get("root_cause_category"), 0) * FIELD_IMPORTANCE["root_cause_category"]
    score += HOSPITALISED_WEIGHTS.get(_to_bool(report.get("hospitalised")), 0) * FIELD_IMPORTANCE["hospitalised"]
    score += NEAR_MISS_WEIGHTS.get(_to_bool(report.get("is_near_miss")), 0) * FIELD_IMPORTANCE["is_near_miss"]
    score += LOST_TIME_INJURY_WEIGHTS.get(_to_bool(report.get("lost_time_injury")), 0) * FIELD_IMPORTANCE["lost_time_injury"]

    # work_stoppage_hours is already numeric, so it's scaled directly instead
    # of looked up in a dict (a dict can't cover every possible hour value).
    try:
        hours = float(report.get("work_stoppage_hours") or 0)
    except (TypeError, ValueError):
        hours = 0

    hours = max(0, min(hours, MAX_STOPPAGE_HOURS))  # No negatives, and capped
    score += hours * FIELD_IMPORTANCE["work_stoppage_hours"]

    return round(min(score, MAX_SCORE), 2)

# Decide if the Incident Must be Reported to MOM, and by When
# Returns (mom_reportable, deadline) e.g. ("Yes", "2026-10-22") or ("No", "N/A")
def _check_mom_reporting(report):
    reportable = (
        _to_bool(report.get("hospitalised"))
        or _to_bool(report.get("lost_time_injury"))
        or report.get("ai_severity") in MOM_REPORTABLE_SEVERITIES
    )
    if not reportable:
        return "No", NO_DEADLINE

    # Deadline counts from the incident date. If the date is missing or
    # invalid, still flag it, but ask the officer to work the deadline out.
    try:
        incident_date = datetime.strptime(report.get("incident_date"), "%Y-%m-%d")
    except (TypeError, ValueError):
        return "Yes", "Check incident date"

    deadline = incident_date + timedelta(days=MOM_DEADLINE_DAYS)
    return "Yes", deadline.strftime("%Y-%m-%d")

# Add the Score and MOM Details to the Report and Send it to 'data_manager' to be Saved
def _save_with_score(report, score, mom_reportable, deadline):
    record = dict(report)  # Copied, so the Original Report is not Changed
    record["importance_score"] = score
    record["mom_reportable"] = mom_reportable
    record["deadline"] = deadline
    save_record(record)

# --------------------------- #
# logic_manager Main Functions
# --------------------------- #

def logic(json_result):
    print(json.dumps(json_result, indent=2, ensure_ascii=False))  # TEMP: check final JSON
    score = _calculate_importance_score(json_result)
    mom_reportable, deadline = _check_mom_reporting(json_result)
    _save_with_score(json_result, score, mom_reportable, deadline)