# Weight Configuration

# Weight for each possible value that the AI can return for ai_severity
SEVERITY_WEIGHTS = {"Low": 1, "Medium": 4, "High": 7, "Critical": 10}

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

# Weights for the true/false fields: (weight if True, weight if False)
HOSPITALISED_WEIGHTS = (5, 10)
NEAR_MISS_WEIGHTS = (2, 0)
LOST_TIME_INJURY_WEIGHTS = (8, 1)

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
