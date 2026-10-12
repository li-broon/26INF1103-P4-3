"""
Fill a throwaway CSV with fake incident reports and open the "View Reports" screen,
so you can see how the output table looks without chatting to the AI.

Run from the project root:
    python scripts/show_fake_reports.py          # uses a temp file, data/data.csv is untouched
    python scripts/show_fake_reports.py --real   # writes the fake reports into data/data.csv
"""
import os
import random
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import data_manager
from src.logic_manager import _calculate_importance_score, _check_mom_reporting
from src.io_manager import view_reports

NAMES = ["Ahmad bin Ismail", "Tan Wei Ming", "Priya Raman", "Nguyen Van An", "John Lim", "Siti Nurhaliza"]
LOCATIONS = [
    "Tuas site, Level 3 electrical room",
    "Jurong warehouse, loading bay 2",
    "Changi depot, workshop",
    "Woodlands construction site, scaffolding",
    "Pasir Panjang terminal, crane area",
]
INCIDENTS = [
    ("Worker touched an exposed live wire while replacing a panel cover.", "Electrical", "Critical"),
    ("Worker slipped on an oily floor near the forklift charging area.", "Slip or Trip", "Medium"),
    ("Hand caught in conveyor belt roller during cleaning without isolating power.", "Machinery", "High"),
    ("Box fell from the top shelf and narrowly missed a worker.", "Struck by Object", "Low"),
    ("Worker fell from 2m scaffolding when a guardrail gave way.", "Fall from Height", "Critical"),
    ("Strong chemical smell after a container leaked in storage.", "Chemical", "Medium"),
]
LANGUAGES = ["English", "Malay", "Chinese", "Tamil", "Vietnamese"]


def fake_report(i):
    description, cause, severity = random.choice(INCIDENTS)
    near_miss = severity == "Low"
    hospitalised = severity in ("High", "Critical") and random.random() < 0.7
    return {
        "reporter_name": random.choice(NAMES),
        "location": random.choice(LOCATIONS),
        "incident_date": (date.today() - timedelta(days=random.randint(0, 300))).strftime("%Y-%m-%d"),
        "incident_time": f"{random.randint(7, 19):02d}:{random.choice([0, 15, 30, 45]):02d}",
        "description": description,
        "injury_status": "None" if near_miss else random.choice(["Minor cut", "Burns on right hand", "Sprained ankle", "Fractured wrist"]),
        "hospitalised": hospitalised,
        "immediate_action_taken": random.choice(["First aid given", "Area cordoned off", "Power isolated, ambulance called", "Supervisor informed"]),
        "work_stoppage_hours": 0 if near_miss else random.choice([0.5, 1, 2, 4, 8]),
        "detected_language": random.choice(LANGUAGES),
        "ai_severity": severity,
        "is_near_miss": near_miss,
        "root_cause_category": cause,
        "lost_time_injury": hospitalised or (not near_miss and random.random() < 0.3),
        "safety_recommendation": "Review the procedure with the team and inspect the area before work resumes.",
    }


def main():
    if "--real" not in sys.argv:
        temp_dir = tempfile.mkdtemp()
        data_manager.DATA_FOLDER = temp_dir
        data_manager.DATA_FILE = os.path.join(temp_dir, "data.csv")
        print(f"Using temp file: {data_manager.DATA_FILE}")

    random.seed(42)  # Same fake data every run
    for i in range(12):  # 12 reports -> more than one page
        report = fake_report(i)
        report["importance_score"] = _calculate_importance_score(report)
        report["mom_reportable"], report["deadline"] = _check_mom_reporting(report)
        ok, message = data_manager.save_record(report)
        if not ok:
            print(message)

    view_reports()


if __name__ == "__main__":
    main()
