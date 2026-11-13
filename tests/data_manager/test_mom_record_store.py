# Imports

import os
import tempfile
from datetime import date

import pandas as pd

from src.data_manager.constants import MOM_ID_FIELD, MOM_REPORTED_FIELD, MOM_REPORTED_ON_FIELD
from src.data_manager.storage.mom_record_store import MomRecordStore

# ------- #
# Helpers
# ------- #

# One Valid MOM Reportable Report (Change Anything with Keyword Arguments)
def make_report(name="Ann", score=8.0, deadline="2026-11-01", mom="Yes", **extra):
    report = {"reporter_name": name, "incident_date": "2026-10-22", "incident_time": "10:00", "location": "Dock",
              "description": f"{name} was hurt", "importance_score": score, "mom_reportable": mom,
              "deadline": deadline, "ai_severity": "High", "hospitalised": True}
    report.update(extra)
    return report

# Run 'action' with a Fresh MomRecordStore on a Temporary File, Deleted Afterwards
def with_store(action):
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "mom_data.csv")
        return action(MomRecordStore(path), path)

# --------- #
# Saving
# --------- #

# Only MOM Reportable Reports Get In, and they Start as Not Reported
def test_saves_only_mom_reportable_reports():
    def run(store, path):
        assert store.save_record(make_report("Ann"))[0] is True
        saved, message = store.save_record(make_report("Ben", mom="No"))
        assert saved is False and "not MOM Reportable" in message
        table = store.load_records()
        assert list(table["reporter_name"]) == ["Ann"]
        assert table.iloc[0][MOM_REPORTED_FIELD] == "No"
        assert pd.isna(table.iloc[0][MOM_REPORTED_ON_FIELD])
    with_store(run)

# Text and Boolean Versions of "Yes" Both Count
def test_yes_can_be_text_or_boolean():
    def run(store, path):
        assert store.save_record(make_report("Ann", mom="true"))[0] is True
        assert store.save_record(make_report("Ben", mom=True))[0] is True
    with_store(run)

# A Bad Report (Missing Name, Bad Date) is Rejected, and Nothing is Written
def test_bad_reports_are_rejected():
    def run(store, path):
        assert store.save_record(make_report(reporter_name=""))[0] is False
        assert store.save_record(make_report(incident_date="not a date"))[0] is False
        assert store.save_record("not a dict")[0] is False
        assert not os.path.exists(path)
    with_store(run)

# The Same Report Cannot be Added Twice, Even After the Register is Ticked
def test_duplicates_are_rejected():
    def run(store, path):
        assert store.save_record(make_report("Ann"))[0] is True
        mom_id = store.load_records().iloc[0][MOM_ID_FIELD]
        store.set_reported(mom_id, True)
        saved, message = store.save_record(make_report("Ann"))
        assert saved is False and "already" in message
        assert len(store.load_records()) == 1
        assert store.load_records().iloc[0][MOM_REPORTED_FIELD] == "Yes"  # Not Reset by the Rejected Duplicate
    with_store(run)

# The Id Ignores Case and Spaces, and Does Not Depend on the Score or Deadline
def test_id_is_stable():
    store = MomRecordStore(os.path.join(tempfile.gettempdir(), "unused_mom.csv"))
    assert store.make_id(make_report("Ann")) == store.make_id(make_report(" ANN ", description=" ann was hurt "))
    assert store.make_id(make_report("Ann")) == store.make_id(make_report("Ann", score=1, deadline="N/A"))
    assert store.make_id(make_report("Ann")) != store.make_id(make_report("Ben"))

# --------------- #
# Ticking Reports
# --------------- #

# Ticking Writes Straight to the File (a Brand New Store Reading the Same File Sees it), and Records the Date
def test_ticking_updates_the_file_directly():
    def run(store, path):
        store.save_record(make_report("Ann"))
        mom_id = store.load_records().iloc[0][MOM_ID_FIELD]
        assert store.set_reported(mom_id, True) == (True, "MOM register updated.")

        row = MomRecordStore(path).load_records().iloc[0]
        assert row[MOM_REPORTED_FIELD] == "Yes"
        assert row[MOM_REPORTED_ON_FIELD] == date.today().strftime("%Y-%m-%d")
    with_store(run)

# Unticking Puts it Back to "No" and Clears the Date
def test_unticking_clears_the_date():
    def run(store, path):
        store.save_record(make_report("Ann"))
        mom_id = store.load_records().iloc[0][MOM_ID_FIELD]
        store.set_reported(mom_id, True)
        store.set_reported(mom_id, False)
        row = store.load_records().iloc[0]
        assert row[MOM_REPORTED_FIELD] == "No"
        assert pd.isna(row[MOM_REPORTED_ON_FIELD])
    with_store(run)

# Ticking One Report Leaves the Others Alone
def test_ticking_only_changes_that_report():
    def run(store, path):
        store.save_record(make_report("Ann"))
        store.save_record(make_report("Ben"))
        table = store.load_records()
        ann = table[table["reporter_name"] == "Ann"].iloc[0][MOM_ID_FIELD]
        store.set_reported(ann, True)
        result = store.load_records().set_index("reporter_name")[MOM_REPORTED_FIELD].to_dict()
        assert result == {"Ann": "Yes", "Ben": "No"}
    with_store(run)

# An Unknown Id, or an Empty Register, Fails Politely
def test_ticking_an_unknown_report_fails_politely():
    def run(store, path):
        assert store.set_reported("nope", True)[0] is False   # No File Yet
        store.save_record(make_report("Ann"))
        saved, message = store.set_reported("nope", True)
        assert saved is False and "not in the MOM register" in message
    with_store(run)

# ------------ #
# Reading
# ------------ #

# Not Yet Reported Come First, Soonest Deadline First, Reported Last; Odd Deadlines Sort After Real Dates
def test_load_order_pending_by_deadline_then_reported():
    def run(store, path):
        store.save_record(make_report("Late", deadline="2026-12-01"))
        store.save_record(make_report("Soon", deadline="2026-11-01"))
        store.save_record(make_report("Odd", deadline="Check incident date"))
        store.save_record(make_report("Done", deadline="2026-10-01"))
        table = store.load_records()
        store.set_reported(table[table["reporter_name"] == "Done"].iloc[0][MOM_ID_FIELD], True)
        assert list(store.load_records()["reporter_name"]) == ["Soon", "Late", "Odd", "Done"]
    with_store(run)

# Scores Come Back as Numbers, and No Helper Columns Leak Out
def test_load_returns_numeric_scores_without_helper_columns():
    def run(store, path):
        store.save_record(make_report("Ann", score=7.4))
        table = store.load_records()
        assert table.iloc[0]["importance_score"] == 7.4
        assert not [column for column in table.columns if column.startswith("_")]
    with_store(run)

# Nothing Saved Yet Gives an Empty Table
def test_empty_register_gives_empty_table():
    def run(store, path):
        assert store.load_records().empty
    with_store(run)

# An Unreadable File is Backed Up, Not Destroyed, when the Next Report is Saved
def test_unreadable_file_is_backed_up():
    def run(store, path):
        with open(path, "w", encoding="utf-8") as file:
            file.write('a,b\n"unterminated,1,2\n3\n')
        assert store.save_record(make_report("Ann"))[0] is True
        assert os.path.exists(path.replace(".csv", "_backup.csv"))
        assert list(store.load_records()["reporter_name"]) == ["Ann"]
    with_store(run)

# -------- #
# Sync
# -------- #

# sync Copies Only the MOM Reportable Reports, Only Once
def test_sync_copies_missing_reportable_reports_once():
    def run(store, path):
        table = pd.DataFrame([make_report("Ann"), make_report("Ben", mom="No"), make_report("Cai")])
        assert store.sync(table) == 2
        assert store.sync(table) == 0
        assert sorted(store.load_records()["reporter_name"]) == ["Ann", "Cai"]
    with_store(run)

# sync Keeps Ticks Already Made, and Copes with Empty Input
def test_sync_keeps_existing_ticks():
    def run(store, path):
        store.save_record(make_report("Ann"))
        store.set_reported(store.load_records().iloc[0][MOM_ID_FIELD], True)
        store.sync(pd.DataFrame([make_report("Ann"), make_report("Ben")]))
        result = store.load_records().set_index("reporter_name")[MOM_REPORTED_FIELD].to_dict()
        assert result == {"Ann": "Yes", "Ben": "No"}
        assert store.sync(pd.DataFrame()) == 0
        assert store.sync(None) == 0
    with_store(run)

# ----------- #
# End to End
# ----------- #

# Real LogicManager + Real Stores: a Critical Report Lands in Both Files, a Minor One Only in data.csv, and Ticking Updates mom_data.csv
def test_logic_manager_fills_the_register_and_ticking_updates_it():
    import json
    from src.data_manager import CsvRecordStore, DataManager, TextTranscriptStore, create_default_filters
    from src.logic_manager import LogicManager

    samples = os.path.join(os.path.dirname(__file__), "..", "samples")
    def sample(name):
        with open(os.path.join(samples, name), encoding="utf-8") as file:
            return json.load(file)["report"]

    with tempfile.TemporaryDirectory() as folder:
        data_manager = DataManager(CsvRecordStore(os.path.join(folder, "data.csv")), create_default_filters(),
                                   TextTranscriptStore(os.path.join(folder, "transcripts")))
        mom_store = MomRecordStore(os.path.join(folder, "mom_data.csv"))
        manager = LogicManager(data_manager, mom_store=mom_store)

        assert manager.process(sample("critical_electrical.json")).saved is True
        assert manager.process(sample("near_miss_slip.json")).saved is True

        assert len(data_manager.load_records()) == 2
        register = mom_store.load_records()
        assert list(register["reporter_name"]) == ["Ahmad bin Ismail"]
        assert register.iloc[0]["mom_reportable"] == "Yes"

        mom_store.set_reported(register.iloc[0][MOM_ID_FIELD], True)
        assert MomRecordStore(os.path.join(folder, "mom_data.csv")).load_records().iloc[0][MOM_REPORTED_FIELD] == "Yes"
        assert "safety_officer_reported" not in data_manager.load_records().columns  # data.csv is untouched by ticking


# A Register File Edited by Hand into the Wrong Shape Must Not Stop the App Starting: it Reads as Empty, Ticking Says So,
# and the First Save Backs the Bad File Up and Starts a Fresh Register
def test_register_without_its_columns_is_treated_as_empty_and_backed_up():
    for content in ("not,a,register\n1,2\n", "reporter_name,deadline\nAnn,2026-11-20\n", "mom_id,reporter_name\nabc,Ann\n"):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "mom_data.csv")
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            store = MomRecordStore(path)
            assert store.load_records().empty
            assert store.set_reported("abc", True) == (False, "MOM register is empty.")
            assert store.save_record(make_report("Ann"))[0] is True
            assert os.path.exists(os.path.join(folder, "mom_data_backup.csv"))
            assert len(store.load_records()) == 1
