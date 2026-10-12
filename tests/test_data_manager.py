"""
Tests for the simplified data_manager.py

Procedural on purpose (no classes, so no unittest.TestCase).
Works two ways:
    python test_data_manager.py     -> built-in mini runner
    pytest test_data_manager.py     -> pytest picks up the test_* functions

Every test runs against a throwaway temp folder, so your real data/data.csv is never touched.
"""
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


# ------------------ #
# Helpers
# ------------------ #
@contextmanager
def temp_data_dir():
    """Point data_manager at a temporary folder, then restore it afterwards."""
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


# ------------------ #
# Spec / Constraint Checks
# ------------------ #
def test_no_print_calls_in_data_manager():
    """ Test that data_manager.py does not contain any print() calls"""
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"(?<![\w.])print\s*\(", source), "print() found in data_manager.py"

def test_no_class_definitions_in_data_manager():
    """ Test that data_manager.py does not contain any class definitions"""
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"^\s*class\s+\w+", source, re.MULTILINE), "class definition found"


# ------------------ #
# File I/O & Error Handling
# ------------------ #
def test_load_records_missing_file_returns_empty():
    """Test if load_records() handles a missing data.csv by returning an empty DataFrame."""
    with temp_data_dir():
        assert dm.load_records().empty

def test_load_records_binary_garbage_does_not_crash():
    """Test that a corrupted file is caught and returns empty DataFrame instead of crashing."""
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "data.csv")
        with open(path, "wb") as f:
            f.write(b"\xff\xfe\x00\x01garbage\x80\x81")
        assert dm.load_records().empty

def test_save_valid_record_creates_file():
    """Test that saving a valid record creates the data.csv file."""
    with temp_data_dir():
        ok, message = dm.save_record(make_record())
        assert ok is True
        assert os.path.exists(dm.DATA_FILE)
        assert len(pd.read_csv(dm.DATA_FILE)) == 1

def test_save_missing_required_fields_rejected():
    """Test that saving a record with missing required fields is rejected and does not create a file."""
    with temp_data_dir():
        # Missing name and score (REQUIRED FIELDS ["reporter_name", "importance_score", "incident_date"])
        ok, message = dm.save_record({"incident_date": "2026-10-09"}) 
        assert ok is False
        assert not os.path.exists(dm.DATA_FILE)

def test_save_keeps_file_sorted_by_urgency_desc():
    """Test that records are saved in the order of urgency (importance_score) descending, regardless of the order they were added."""
    with temp_data_dir():
        dm.save_record(make_record(name="Low", score=2))
        dm.save_record(make_record(name="High", score=9))
        dm.save_record(make_record(name="Mid", score=5))
        scores = list(pd.read_csv(dm.DATA_FILE)["importance_score"])
        assert scores == [9, 5, 2]

def test_save_backs_up_unreadable_file_instead_of_overwriting():
    """Test that if the existing data.csv is corrupted, it is backed up before saving a new record."""
    with temp_data_dir():
        os.makedirs(dm.DATA_FOLDER, exist_ok=True)
        write_raw(dm.DATA_FILE, "a,b,c\n1,2,3,4,5\n") # Corrupted structure
        ok, _ = dm.save_record(make_record())
        assert ok is True
        assert os.path.exists(dm.DATA_FILE.replace(".csv", "_backup.csv")) # Verifies backup was created
        assert len(pd.read_csv(dm.DATA_FILE)) == 1


# ------------------ #
# Filtering & UI Helpers
# ------------------ #
def test_get_column_names():
    """Test that get_column_names() returns the correct list of columns after saving a record."""
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

def test_load_matching_records_exact_match_case_insensitive():
    """Test that load_matching_records() finds records with exact matches, ignoring case."""
    with temp_data_dir():
        dm.save_record(make_record(name="Alice", score=3))
        dm.save_record(make_record(name="Bob", score=5))
        
        # Should find Alice even if search is lowercase
        matches = dm.load_matching_records("reporter_name", "alice")
        assert len(matches) == 1
        assert matches.iloc[0]["reporter_name"] == "Alice"

def test_load_matching_records_no_match():
    """Test that load_matching_records() returns an empty DataFrame when no matches are found."""
    with temp_data_dir():
        dm.save_record(make_record(name="Alice", score=3))
        matches = dm.load_matching_records("reporter_name", "Zed")
        assert matches.empty


# ------------------ #
# Mini runner
# ------------------ #
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