# Imports

import os
import sys
import tempfile
import traceback
from abc import ABC
from contextlib import contextmanager

import pandas as pd

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.storage.csv_record_store import CsvRecordStore
from src.data_manager.storage.record_store import RecordStore

# ------- #
# Helpers
# ------- #

# A CsvRecordStore that Writes to a Temporary Folder (Yields the Store and its File Path)
@contextmanager
def temp_store():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "data.csv")
        yield CsvRecordStore(path), path


# One Valid Report (Change Anything with Keyword Arguments)
def make_report(name="Alice", date="2026-10-09", score=8, **extra):
    report = {"reporter_name": name, "incident_date": date, "importance_score": score}
    report.update(extra)
    return report


def write_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# The File Exactly as Saved (No Cleaning, "N/A" Stays Text)
def read_raw(path):
    return pd.read_csv(path, keep_default_na=False, na_values=[""])

# ------------------ #
# The Interface
# ------------------ #

# CsvRecordStore Implements the RecordStore Contract with Every Method Filled In
def test_csv_record_store_implements_record_store():
    assert issubclass(CsvRecordStore, RecordStore)
    assert issubclass(CsvRecordStore, ABC)
    assert not CsvRecordStore.__abstractmethods__  # Nothing left abstract, so it can be created
    with temp_store() as (store, path):
        assert isinstance(store, RecordStore)

# --------------------- #
# Reading Bad Files
# --------------------- #

def test_load_missing_file_returns_empty_table():
    with temp_store() as (store, path):
        assert store.load_records().empty
        assert store.get_column_names() == []


def test_load_empty_file_returns_empty_table():
    with temp_store() as (store, path):
        write_file(path, "")
        assert store.load_records().empty


def test_load_header_only_file_returns_empty_table():
    with temp_store() as (store, path):
        write_file(path, "reporter_name,incident_date,importance_score\n")
        assert store.load_records().empty


def test_load_file_missing_required_columns_returns_empty_table():
    with temp_store() as (store, path):
        write_file(path, "foo,bar\n1,2\n")
        assert store.load_records().empty
        assert store.get_column_names() == []


def test_load_badly_formatted_file_does_not_crash():
    with temp_store() as (store, path):
        write_file(path, "reporter_name,incident_date,importance_score\nAnn,2026-10-01,5,extra,extra\n")
        assert isinstance(store.load_records(), pd.DataFrame)


def test_load_binary_garbage_does_not_crash():
    with temp_store() as (store, path):
        with open(path, "wb") as f:
            f.write(b"\xff\xfe\x00\x01garbage\x80\x81")
        assert store.load_records().empty

# ---------------- #
# Saving
# ---------------- #

def test_save_valid_report_creates_file_and_reports_success():
    with temp_store() as (store, path):
        assert store.save_record(make_report()) == (True, "Record saved.")
        assert len(read_raw(path)) == 1


def test_save_rejects_invalid_reports_and_writes_nothing():
    with temp_store() as (store, path):
        bad_reports = [make_report(name=""), make_report(date="09/10/2026"), make_report(score="high"),
                       {"incident_date": "2026-10-09", "importance_score": 5}, "not a dict", None]
        for report in bad_reports:
            success, message = store.save_record(report)
            assert success is False and message.startswith("Record rejected"), report
        assert not os.path.exists(path)


def test_save_rejects_exact_duplicate():
    with temp_store() as (store, path):
        assert store.save_record(make_report())[0] is True
        assert store.save_record(make_report()) == (False, "Record rejected: an identical record already exists.")
        assert len(read_raw(path)) == 1


def test_save_rejects_duplicate_that_differs_only_in_case_and_spaces():
    with temp_store() as (store, path):
        assert store.save_record(make_report(name="Alice", location="Office"))[0] is True
        assert store.save_record(make_report(name="  ALICE ", score="8.0", location="office"))[0] is False


def test_save_rejects_duplicate_with_na_deadline():
    with temp_store() as (store, path):
        assert store.save_record(make_report(deadline="N/A"))[0] is True
        assert store.save_record(make_report(deadline="N/A"))[0] is False


def test_save_accepts_a_report_that_differs_in_one_field():
    with temp_store() as (store, path):
        assert store.save_record(make_report(location="Office"))[0] is True
        assert store.save_record(make_report(location="Warehouse"))[0] is True
        assert len(read_raw(path)) == 2


def test_na_deadline_survives_save_and_load():
    with temp_store() as (store, path):
        store.save_record(make_report(deadline="N/A"))
        store.save_record(make_report(name="Bob", deadline="2026-11-01"))
        loaded = store.load_records().set_index("reporter_name")
        assert loaded.loc["Alice", "deadline"] == "N/A"
        assert loaded.loc["Bob", "deadline"] == "2026-11-01"


def test_file_is_kept_sorted_by_urgency_highest_first():
    with temp_store() as (store, path):
        for name, score in (("Low", 2), ("High", 9), ("Mid", 5)):
            store.save_record(make_report(name=name, score=score))
        assert list(read_raw(path)["importance_score"]) == [9, 5, 2]


def test_save_leaves_no_temporary_file_behind():
    with temp_store() as (store, path):
        store.save_record(make_report())
        assert os.listdir(os.path.dirname(path)) == ["data.csv"]


def test_save_creates_the_data_folder_if_missing():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nested", "data", "data.csv")
        assert CsvRecordStore(path).save_record(make_report())[0] is True
        assert os.path.exists(path)


def test_unreadable_file_is_backed_up_not_overwritten():
    with temp_store() as (store, path):
        original = "a,b,c\n1,2,3,4,5\n"
        write_file(path, original)
        assert store.save_record(make_report())[0] is True
        backup = path.replace(".csv", "_backup.csv")
        assert read_file(backup) == original          # the old content is kept
        assert len(read_raw(path)) == 1               # and the new report is saved

# ---------------- #
# Reading
# ---------------- #

def test_load_records_orders_by_urgency_and_respects_ascending():
    with temp_store() as (store, path):
        for name, score in (("A", 3), ("B", 7), ("C", 5)):
            store.save_record(make_report(name=name, score=score))
        assert list(store.load_records()["importance_score"]) == [7, 5, 3]
        assert list(store.load_records(ascending=True)["importance_score"]) == [3, 5, 7]


def test_load_records_skips_invalid_and_duplicate_rows_without_changing_the_file():
    with temp_store() as (store, path):
        write_file(path, "reporter_name,incident_date,importance_score,location\n"
                         "Ann,2026-10-01,5,Office\n"
                         "Bob,not-a-date,5,Office\n"
                         ",2026-10-01,5,Office\n"
                         "Ann,2026-10-01,5,Office\n")
        before = read_file(path)
        loaded = store.load_records()
        assert list(loaded["reporter_name"]) == ["Ann"]
        assert read_file(path) == before


def test_get_column_names_lists_the_saved_columns():
    with temp_store() as (store, path):
        store.save_record(make_report(location="Office"))
        assert {"reporter_name", "incident_date", "importance_score", "location"} <= set(store.get_column_names())


def test_reports_persist_across_separate_store_objects():
    with temp_store() as (first, path):
        first.save_record(make_report(name="Ann", score=5))
        first.save_record(make_report(name="Bob", score=9))
        second = CsvRecordStore(path)  # a new object on the same file, like a new run of the app
        assert list(second.load_records()["reporter_name"]) == ["Bob", "Ann"]
        assert second.load_records().equals(first.load_records())

# ------------ #
# Test Runner
# ------------ #

def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
