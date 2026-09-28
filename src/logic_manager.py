# ------- #
# Imports
# ------- #

import json
from src.data_manager import save_record

# ------------------------------ #
# logic_manager Private Functions
# ------------------------------ #

# Work Out How Important the Report is (TODO: add the team's weights for each field)
def _calculate_importance_score(report):
    score = 0
    return score

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
