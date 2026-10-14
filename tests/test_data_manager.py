# Imports
import os
import re
import shutil
import sys
import tempfile
import traceback
from contextlib import contextmanager

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import data_manager as dm  # noqa: E402


# Helpers

# Point data_manager at a temporary folder, then restore it afterwards.
@contextmanager
def temp_data_dir():
    tmp = tempfile.mkdtemp()
    old_folder, old_file = dm.DATA_FOLDER, dm.DATA_FILE
    dm.DATA_FOLDER = tmp
    dm.DATA_FILE = os.path.join(tmp, "data.csv")
    try:
        yield tmp
    finally:
        dm.DATA_FOLDER, dm.DATA_FILE = old_folder, old_file
        shutil.rmtree(tmp, ignore_errors=True)

def make_record(name="Alice", date="2026-10-09", score=8, **extra):
    record = {"reporter_name": name, "incident_date": date, "importance_score": score}
    record.update(extra)
    return record

def write_raw(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# Spec / Constraint Checks

# Test that data_manager.py does not contain any print() calls
def test_no_print_calls_in_data_manager():
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"(?<![\w.])print\s*\(", source), "print() found in data_manager.py"

# Test that data_manager.py does not contain any class definitions
def test_no_class_definitions_in_data_manager():
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"^\s*class\s+\w+", source, re.MULTILINE), "class definition found"


# File I/O & Error Handling

# Test if load_records() handles a missing data.csv by returning an empty DataFrame.
def test_load_records_missing_file_returns_empty():
    with temp_data_dir():
        assert dm.load_records().empty

# Test that a corrupted file is caught and returns empty DataFrame instead of crashing.
def test_load_records_binary_garbage_does_not_crash():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "data.csv")
        with open(path, "wb") as f:
            f.write(b"\xff\xfe\x00\x01garbage\x80\x81")
        assert dm.load_records().empty

# Test that saving a valid record creates the data.csv file.
def test_save_valid_record_creates_file():
    with temp_data_dir():
        ok, message = dm.save_record(make_record())
        assert ok is True
        assert os.path.exists(dm.DATA_FILE)
        assert len(pd.read_csv(dm.DATA_FILE)) == 1

# Test that saving a record with missing required fields is rejected and does not create a file.
def test_save_missing_required_fields_rejected():
    with temp_data_dir():
        # Missing name and score (REQUIRED FIELDS ["reporter_name", "importance_score", "incident_date"])
        ok, message = dm.save_record({"incident_date": "2026-10-09"}) 
        assert ok is False
        assert not os.path.exists(dm.DATA_FILE)

# Test that records are saved in the order of urgency (importance_score) descending, regardless of the order they were added.
def test_save_keeps_file_sorted_by_urgency_desc():
    with temp_data_dir():
        dm.save_record(make_record(name="Low", score=2))
        dm.save_record(make_record(name="High", score=9))
        dm.save_record(make_record(name="Mid", score=5))
        scores = list(pd.read_csv(dm.DATA_FILE)["importance_score"])
        assert scores == [9, 5, 2]

# Test that if the existing data.csv is corrupted, it is backed up before saving a new record.
def test_save_backs_up_unreadable_file_instead_of_overwriting():
    with temp_data_dir():
        os.makedirs(dm.DATA_FOLDER, exist_ok=True)
        write_raw(dm.DATA_FILE, "a,b,c\n1,2,3,4,5\n") # Corrupted structure
        ok, _ = dm.save_record(make_record())
        assert ok is True
        assert os.path.exists(dm.DATA_FILE.replace(".csv", "_backup.csv")) # Verifies backup was created
        assert len(pd.read_csv(dm.DATA_FILE)) == 1

# Test that a non-MOM report (deadline "N/A") is caught as a duplicate, and "N/A" survives a re-save.
def test_duplicate_with_na_deadline_rejected():
    with temp_data_dir():
        assert dm.save_record(make_record(deadline="N/A"))[0] is True
        ok, message = dm.save_record(make_record(deadline="N/A"))
        assert ok is False
        assert "identical" in message
        dm.save_record(make_record(name="Bob", deadline="N/A"))  # Rewrites the whole file
        assert list(dm.load_records()["deadline"]) == ["N/A", "N/A"]


# Filtering & UI Helpers

# Test that get_column_names() returns the correct list of columns after saving a record.
def test_get_column_names():
    with temp_data_dir():
        assert dm.get_column_names() == []
        dm.save_record(make_record(category="fire"))
        assert "category" in dm.get_column_names()

def test_get_unique_values():
    with temp_data_dir():
        """Test that get_unique_values() returns the correct column values for a given column."""
        dm.save_record(make_record(name="Bob", score=3))
        dm.save_record(make_record(name="Alice", score=4))
        assert dm.get_unique_values("reporter_name") == ["Alice", "Bob"]
        assert dm.get_unique_values("nope") == []

# Test that load_matching_records() finds records with exact matches, ignoring case.
def test_load_matching_records_exact_match_case_insensitive():
    with temp_data_dir():
        dm.save_record(make_record(name="Alice", score=3))
        dm.save_record(make_record(name="Bob", score=5))
        
        # Should find Alice even if search is lowercase
        matches = dm.load_matching_records("reporter_name", "alice")
        assert len(matches) == 1
        assert matches.iloc[0]["reporter_name"] == "Alice"

# Test that load_matching_records() returns an empty DataFrame when no matches are found.
def test_load_matching_records_no_match():
    with temp_data_dir():
        dm.save_record(make_record(name="Alice", score=3))
        matches = dm.load_matching_records("reporter_name", "Zed")
        assert matches.empty


# Mini runner
def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
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