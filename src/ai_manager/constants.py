# --Shared Report Settings Used by the Field Definitions, the Analysis Schema and the Prompts-- #

# Allowed Values for the AI's Severity and Root Cause
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

ROOT_CAUSES = [
    "Electrical", "Chemical", "Fall from Height", "Struck by Object", "Machinery",
    "Slip or Trip", "Fire", "Water", "Safety Procedure Breach", "Other",
]

# Date Format for the Incident Date and for "Today" in the Prompt (Must Match so Relative Dates Work)
DATE_FORMAT = "%Y-%m-%d"

# Value the AI Stores when the Worker Really Does Not Know a Detail
UNKNOWN_VALUE = "unknown (worker could not say)"
