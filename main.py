# -------- #
# Import(s)
# -------- #

from src.io_manager import main

# TEMP: fake reports so the View Reports table has something to show -- delete before submitting
import random
from src.data_manager import save_record
from src.logic_manager import _calculate_importance_score
from scripts.show_fake_reports import fake_report

def _add_fake_reports(count=12):
    random.seed(42)  # Same reports every run, so duplicates are rejected instead of piling up
    for i in range(count):
        report = fake_report(i)
        report["importance_score"] = _calculate_importance_score(report)
        save_record(report)
# END TEMP

# --------- #
# Start App
# --------- #
if __name__ == "__main__":
    _add_fake_reports()  # TEMP
    main()
