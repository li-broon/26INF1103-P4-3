# ------- #
# Imports
# ------- #

import json

# --------------------------- #
# logic_manager Main Functions
# --------------------------- # 

def logic(json_result):
    print(json.dumps(json_result, indent=2, ensure_ascii=False))  # TEMP: check final JSON