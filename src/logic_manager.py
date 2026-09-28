# ------- #
# Imports
# ------- #

import json

# --------------------------- #
# logic_manager Main Functions
# --------------------------- # 

def logic(result):
    print(json.dumps(result["report"], indent=2, ensure_ascii=False))  # TEMP: check final JSON