# Imports

import ast
import glob
import os
import re
import sys
import tempfile
import traceback

# Import the Module Under Test
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)  # Let 'src' be Imported
from src import data_manager
from src.data_manager import DataManager, RecordStore
from src.data_manager import data_manager as manager
from src.data_manager.storage.record_cleaner import RecordCleaner

PACKAGE_FOLDER = os.path.join(PROJECT_ROOT, "src", "data_manager")


# All the .py Files in src/data_manager and its Subfolders
def package_files():
    return sorted(glob.glob(os.path.join(PACKAGE_FOLDER, "**", "*.py"), recursive=True))

# ----- #
# Tests
# ----- #

# Project Rule: Every Class has its Own File
def test_each_file_has_at_most_one_class():
    for path in package_files():
        with open(path, encoding="utf-8") as f:
            classes = [n.name for n in ast.walk(ast.parse(f.read())) if isinstance(n, ast.ClassDef)]
        assert len(classes) <= 1, f"{os.path.relpath(path, PROJECT_ROOT)} has {len(classes)} classes: {classes}"


# Project Rule: All print() Calls Live in io_manager
def test_no_print_calls_in_the_data_manager():
    for path in package_files():
        with open(path, encoding="utf-8") as f:
            assert not re.search(r"(?<![\w.])print\s*\(", f.read()), f"print() found in {path}"


# The Names the Other Managers Import Still Work
def test_public_names_are_exported():
    for name in ("DataManager", "RecordStore", "save_record", "load_records",
                 "get_unique_values", "load_matching_records"):
        assert hasattr(data_manager, name), f"src.data_manager has no '{name}'"


# Moving the File One Folder Deeper Must Not Change Where the Reports are Stored
def test_default_data_file_is_in_the_project_data_folder():
    expected = os.path.join(PROJECT_ROOT, "data", "data.csv")
    assert os.path.abspath(manager.DATA_FILE) == expected
    assert os.path.abspath(manager.DATA_FOLDER) == os.path.join(PROJECT_ROOT, "data")


# Every DataManager Creates and Owns its Own RecordCleaner (Composition)
def test_each_data_manager_owns_its_own_record_cleaner():
    with tempfile.TemporaryDirectory() as folder:
        first = DataManager(os.path.join(folder, "a.csv"))
        second = DataManager(os.path.join(folder, "b.csv"))
        assert isinstance(first._cleaner, RecordCleaner)
        assert first._cleaner is not second._cleaner


# A DataManager Saves to the File it is Given and Reads the Same Reports Back
def test_data_manager_saves_and_loads_through_its_own_file():
    with tempfile.TemporaryDirectory() as folder:
        data_file = os.path.join(folder, "data.csv")
        dm = DataManager(data_file)
        report = {"reporter_name": "Ann", "incident_date": "2026-10-01", "importance_score": 7}
        assert dm.save_record(report) == (True, "Record saved.")
        assert dm.save_record(report)[0] is False  # Identical report is rejected
        loaded = dm.load_records()
        assert len(loaded) == 1 and loaded.iloc[0]["reporter_name"] == "Ann"
        assert os.path.exists(data_file)

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