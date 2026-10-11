"""
Tests for data_manager.py

Procedural on purpose (no classes, so no unittest.TestCase).
Works two ways:
    python test_data_manager.py     -> built-in mini runner
    pytest test_data_manager.py     -> pytest picks up the test_* functions

Every test runs against a throwaway temp folder, so your real data/data.csv is never touched.
Place this file in the same folder as data_manager.py (or adjust the sys.path line below).
"""
import os
import re
import shutil
import sys
import tempfile
import traceback
from contextlib import contextmanager

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_manager as dm  # noqa: E402


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
# Spec / constraint checks
# ------------------ #
def test_no_print_calls_in_data_manager():
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"(?<![\w.])print\s*\(", source), "print() found in data_manager.py"


def test_no_class_definitions_in_data_manager():
    with open(dm.__file__, encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"^\s*class\s+\w+", source, re.MULTILINE), "class definition found"


# ------------------ #
# clean_record
# ------------------ #
def test_clean_record_valid():
    result = dm.clean_record(make_record(score=8))
    assert result["importance_score"] == 8.0
    assert isinstance(result["importance_score"], float)
    assert result["incident_date"] == "2026-10-09"


def test_clean_record_strips_whitespace():
    result = dm.clean_record(make_record(name="  Alice  ", note="  hello "))
    assert result["reporter_name"] == "Alice"
    assert result["note"] == "hello"


def test_clean_record_does_not_mutate_input():
    original = make_record(name="  Bob ")
    dm.clean_record(original)
    assert original["reporter_name"] == "  Bob "


def test_clean_record_missing_required_field():
    for field in dm.REQUIRED_FIELDS:
        record = make_record()
        del record[field]
        assert dm.clean_record(record) is None, f"missing {field} should be rejected"


def test_clean_record_empty_or_none_required_field():
    assert dm.clean_record(make_record(name="")) is None
    assert dm.clean_record(make_record(name="   ")) is None
    assert dm.clean_record(make_record(name=None)) is None
    assert dm.clean_record(make_record(score=float("nan"))) is None


def test_clean_record_bad_date():
    assert dm.clean_record(make_record(date="09/10/2026")) is None
    assert dm.clean_record(make_record(date="not a date")) is None
    assert dm.clean_record(make_record(date="2026-13-45")) is None


def test_clean_record_bad_score():
    assert dm.clean_record(make_record(score="high")) is None


def test_clean_record_numeric_string_score_ok():
    assert dm.clean_record(make_record(score="7.5"))["importance_score"] == 7.5


def test_clean_record_non_dict():
    assert dm.clean_record(None) is None
    assert dm.clean_record("a string") is None
    assert dm.clean_record([1, 2, 3]) is None


# ------------------ #
# is_duplicate
# ------------------ #
def test_is_duplicate_empty_table():
    assert dm.is_duplicate(pd.DataFrame(), make_record()) is False


def test_is_duplicate_exact_match():
    table = pd.DataFrame([make_record()])
    assert dm.is_duplicate(table, make_record()) is True


def test_is_duplicate_ignores_case_and_numeric_type():
    table = pd.DataFrame([make_record(name="Alice", score=8)])
    assert dm.is_duplicate(table, make_record(name="ALICE", score=8.0)) is True


def test_is_duplicate_different_record():
    table = pd.DataFrame([make_record()])
    assert dm.is_duplicate(table, make_record(score=9)) is False
    assert dm.is_duplicate(table, make_record(name="Bob")) is False


# ------------------ #
# load_data_from_csv
# ------------------ #
def test_load_missing_file_returns_empty():
    with temp_data_dir() as tmp:
        assert dm.load_data_from_csv(os.path.join(tmp, "nope.csv")).empty


def test_load_empty_file_returns_empty():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "empty.csv")
        write_raw(path, "")
        assert dm.load_data_from_csv(path).empty


def test_load_header_only_file_returns_empty():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "header.csv")
        write_raw(path, "reporter_name,incident_date,importance_score\n")
        assert dm.load_data_from_csv(path).empty


def test_load_missing_required_columns_returns_empty():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "cols.csv")
        write_raw(path, "foo,bar\n1,2\n")
        assert dm.load_data_from_csv(path).empty


def test_load_malformed_rows_does_not_crash():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "bad.csv")
        write_raw(path, "reporter_name,incident_date,importance_score\nAlice,2026-10-09,8,extra,extra\n")
        result = dm.load_data_from_csv(path)
        assert isinstance(result, pd.DataFrame)


def test_load_binary_garbage_does_not_crash():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "garbage.csv")
        with open(path, "wb") as f:
            f.write(b"\xff\xfe\x00\x01garbage\x80\x81")
        assert dm.load_data_from_csv(path).empty


def test_load_does_not_delete_or_modify_rows():
    with temp_data_dir() as tmp:
        path = os.path.join(tmp, "raw.csv")
        write_raw(
            path,
            "reporter_name,incident_date,importance_score\n"
            "Alice,2026-10-09,8\n"
            "Alice,2026-10-09,8\n"
            ",2026-10-09,5\n",
        )
        assert len(dm.load_data_from_csv(path)) == 3


# ------------------ #
# sorting
# ------------------ #
def test_sort_by_column_ascending_and_descending():
    table = pd.DataFrame({"x": [3, 1, 2]})
    assert list(dm.sort_by_column(table, "x", ascending=True)["x"]) == [1, 2, 3]
    assert list(dm.sort_by_column(table, "x", ascending=False)["x"]) == [3, 2, 1]


def test_sort_by_column_missing_column_returns_unchanged():
    table = pd.DataFrame({"x": [3, 1, 2]})
    assert list(dm.sort_by_column(table, "nope")["x"]) == [3, 1, 2]


def test_sort_by_urgency_default_is_most_urgent_first():
    table = pd.DataFrame({dm.URGENCY_COLUMN: [2, 9, 5]})
    assert list(dm.sort_by_urgency(table)[dm.URGENCY_COLUMN]) == [9, 5, 2]


def test_sort_by_urgency_non_numeric_goes_last():
    table = pd.DataFrame({dm.URGENCY_COLUMN: ["5", "abc", "9"]})
    scores = list(dm.sort_by_urgency(table)[dm.URGENCY_COLUMN])
    assert scores[:2] == [9, 5]
    assert pd.isna(scores[2])


# ------------------ #
# filter_by_value
# ------------------ #
def test_filter_text_ignores_case_and_spaces():
    table = pd.DataFrame({"name": ["Alice", "bob", "ALICE"]})
    assert len(dm.filter_by_value(table, "name", "  alice ")) == 2


def test_filter_numeric_column():
    table = pd.DataFrame({"score": [8, 5, 8]})
    assert len(dm.filter_by_value(table, "score", "8")) == 2


def test_filter_invalid_number_returns_empty():
    table = pd.DataFrame({"score": [8, 5]})
    assert dm.filter_by_value(table, "score", "abc").empty


def test_filter_missing_column_returns_empty():
    table = pd.DataFrame({"name": ["Alice"]})
    assert dm.filter_by_value(table, "nope", "x").empty


def test_filter_no_match_returns_empty():
    table = pd.DataFrame({"name": ["Alice"]})
    assert dm.filter_by_value(table, "name", "Zed").empty


# ------------------ #
# save_record
# ------------------ #
def test_save_valid_record_creates_file():
    with temp_data_dir():
        ok, message = dm.save_record(make_record())
        assert ok is True and isinstance(message, str)
        assert os.path.exists(dm.DATA_FILE)
        assert len(pd.read_csv(dm.DATA_FILE)) == 1


def test_save_invalid_record_rejected_and_nothing_written():
    with temp_data_dir():
        ok, message = dm.save_record(make_record(date="garbage"))
        assert ok is False and message
        assert not os.path.exists(dm.DATA_FILE)


def test_save_duplicate_rejected():
    with temp_data_dir():
        assert dm.save_record(make_record())[0] is True
        ok, message = dm.save_record(make_record())
        assert ok is False and "already exists" in message
        assert len(pd.read_csv(dm.DATA_FILE)) == 1


def test_save_keeps_file_sorted_by_urgency_desc():
    with temp_data_dir():
        dm.save_record(make_record(name="Low", score=2))
        dm.save_record(make_record(name="High", score=9))
        dm.save_record(make_record(name="Mid", score=5))
        scores = list(pd.read_csv(dm.DATA_FILE)[dm.URGENCY_COLUMN])
        assert scores == [9, 5, 2]


def test_save_leaves_no_temp_file_behind():
    with temp_data_dir() as tmp:
        dm.save_record(make_record())
        assert not os.path.exists(os.path.join(tmp, "data.csv.tmp"))


def test_save_backs_up_unreadable_file_instead_of_overwriting():
    with temp_data_dir():
        os.makedirs(dm.DATA_FOLDER, exist_ok=True)
        write_raw(dm.DATA_FILE, "a,b,c\n1,2,3,4,5\n")
        ok, _ = dm.save_record(make_record())
        assert ok is True
        assert os.path.exists(dm.DATA_FILE + ".bak")
        with open(dm.DATA_FILE + ".bak", encoding="utf-8") as f:
            assert "1,2,3,4,5" in f.read()
        assert len(pd.read_csv(dm.DATA_FILE)) == 1


def test_save_creates_missing_data_folder():
    with temp_data_dir() as tmp:
        dm.DATA_FOLDER = os.path.join(tmp, "nested", "data")
        dm.DATA_FILE = os.path.join(dm.DATA_FOLDER, "data.csv")
        assert dm.save_record(make_record())[0] is True
        assert os.path.exists(dm.DATA_FILE)


# ------------------ #
# load_records / persistence
# ------------------ #
def test_load_records_empty_when_no_file():
    with temp_data_dir():
        assert dm.load_records().empty


def test_load_records_sorted_and_ascending_flag():
    with temp_data_dir():
        dm.save_record(make_record(name="A", score=3))
        dm.save_record(make_record(name="B", score=7))
        assert list(dm.load_records()[dm.URGENCY_COLUMN]) == [7, 3]
        assert list(dm.load_records(ascending=True)[dm.URGENCY_COLUMN]) == [3, 7]


def test_records_persist_across_loads_with_same_output():
    with temp_data_dir():
        dm.save_record(make_record(name="A", score=3))
        dm.save_record(make_record(name="B", score=7))
        first = dm.load_records()
        second = dm.load_records()
        assert first.equals(second)


def test_load_records_does_not_modify_file():
    with temp_data_dir():
        dm.save_record(make_record())
        with open(dm.DATA_FILE, encoding="utf-8") as f:
            before = f.read()
        dm.load_records()
        with open(dm.DATA_FILE, encoding="utf-8") as f:
            assert f.read() == before


# ------------------ #
# column / value helpers
# ------------------ #
def test_get_column_names():
    with temp_data_dir():
        assert dm.get_column_names() == []
        dm.save_record(make_record(category="fire"))
        assert set(dm.REQUIRED_FIELDS + ["category"]) <= set(dm.get_column_names())


def test_get_unique_values():
    with temp_data_dir():
        dm.save_record(make_record(name="Bob", score=3))
        dm.save_record(make_record(name="Alice", score=4))
        assert dm.get_unique_values("reporter_name") == ["Alice", "Bob"]
        assert dm.get_unique_values("nope") == []


def test_load_matching_records():
    with temp_data_dir():
        dm.save_record(make_record(name="Alice", score=3))
        dm.save_record(make_record(name="Alice", score=9, date="2026-10-08"))
        dm.save_record(make_record(name="Bob", score=5))
        matches = dm.load_matching_records("reporter_name", "alice")
        assert len(matches) == 2
        assert list(matches[dm.URGENCY_COLUMN]) == [9, 3]
        assert dm.load_matching_records("reporter_name", "Zed").empty


def test_load_matching_records_when_no_file():
    with temp_data_dir():
        assert dm.load_matching_records("reporter_name", "Alice").empty


# ------------------ #
# Mini runner (used when not running under pytest)
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
