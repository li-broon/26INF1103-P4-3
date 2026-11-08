# Shared Sample Data for the io_manager Tests (Values Only, No Classes)

# A Saved Report as the Data Manager Would Return it
REPORT = {
    "reporter_name": "Ahmad bin Ismail",
    "incident_date": "2026-10-08",
    "hospitalised": True,
    "is_near_miss": False,
    "injury_status": "",
}

# The Logic Manager's Result for a Saved, MOM-Reportable Report (Change Fields with dict(SAVED_FIELDS, ...))
SAVED_FIELDS = {
    "saved": True,
    "message": "Record saved.",
    "importance_score": 7.4,
    "mom_reportable": "Yes",
    "deadline": "2099-12-31",
}
