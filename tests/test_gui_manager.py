# Imports
import sys
import os
from datetime import date, timedelta

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Tkinter is Part of Python, but Some Linux Installs Leave it Out: Skip Rather than Fail
pytest.importorskip("tkinter")
from src import gui_manager as gui
from src.io_manager import TABLE_COLUMNS, FULL_REPORT_FIELDS

# These Tests Only Use the Helpers, so No Window is Opened (CI Has No Display)


# score_colours Tests

# Test that each score band gets its own colour, most urgent in red
def test_score_colours_bands():
    assert gui.score_colours(9.1) == (gui.DANGER, gui.DANGER_SOFT)
    assert gui.score_colours(8) == (gui.DANGER, gui.DANGER_SOFT)
    assert gui.score_colours("6.5") == (gui.ORANGE, gui.ORANGE_SOFT)
    assert gui.score_colours(4) == (gui.WARNING, gui.WARNING_SOFT)
    assert gui.score_colours(1.2) == (gui.SUCCESS, gui.SUCCESS_SOFT)

# Test that a missing or broken score gets a neutral colour instead of crashing
def test_score_colours_bad_values():
    assert gui.score_colours(None) == (gui.MUTED, gui.SURFACE_ALT)
    assert gui.score_colours("abc") == (gui.MUTED, gui.SURFACE_ALT)
    assert gui.score_colours(-3) == (gui.SUCCESS, gui.SUCCESS_SOFT)


# report_stats Tests

# Test that the summary cards count hospital cases, MOM cases and overdue MOM cases
def test_report_stats_counts():
    past = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    future = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    table = pd.DataFrame([
        {"hospitalised": True, "mom_reportable": "Yes", "deadline": past},
        {"hospitalised": False, "mom_reportable": "Yes", "deadline": future},
        {"hospitalised": False, "mom_reportable": "No", "deadline": "N/A"},
    ])
    assert gui.report_stats(table) == {"total": 3, "mom": 2, "overdue": 1, "hospitalised": 1}

# Test that an empty table gives all zeros
def test_report_stats_empty():
    assert gui.report_stats(pd.DataFrame()) == {"total": 0, "mom": 0, "overdue": 0, "hospitalised": 0}


# display_value Tests

# Test that blanks, None and NaN all show as "-"
def test_display_value_blanks():
    assert gui.display_value(None) == "-"
    assert gui.display_value("") == "-"
    assert gui.display_value("   ") == "-"
    assert gui.display_value(float("nan")) == "-"

# Test that real values are shown as text
def test_display_value_keeps_values():
    assert gui.display_value(7.5) == "7.5"
    assert gui.display_value(" Block A ") == "Block A"


# table_row_values Tests

# Test that a row has one value per table column plus the row number, with YES/No for true/false
def test_table_row_values_order_and_yes_no():
    report = {"importance_score": 8.2, "ai_severity": "High", "hospitalised": True,
              "deadline": "2026-11-10", "root_cause_category": "Electrical",
              "location": "Plant 2", "incident_date": "2026-10-31"}
    values = gui.table_row_values(3, report)
    assert len(values) == len(TABLE_COLUMNS) + 1
    assert values[0] == 3
    assert values == [3, "8.2", "High", "YES", "2026-11-10", "Electrical", "Plant 2", "2026-10-31"]

# Test that missing columns show "-" instead of crashing
def test_table_row_values_missing_fields():
    values = gui.table_row_values(1, {})
    assert values[1:] == ["-"] * len(TABLE_COLUMNS)


# needs_attention Tests

# Test that hospital cases and MOM cases are highlighted, others are not
def test_needs_attention():
    assert gui.needs_attention({"hospitalised": "True", "mom_reportable": "No"})
    assert gui.needs_attention({"hospitalised": False, "mom_reportable": "Yes"})
    assert not gui.needs_attention({"hospitalised": False, "mom_reportable": "No"})


# full_report_lines Tests

# Test that every full report field is listed, with true/false shown as YES/No
def test_full_report_lines():
    lines = gui.full_report_lines({"reporter_name": "Ali", "is_near_miss": False})
    assert len(lines) == len(FULL_REPORT_FIELDS)
    assert ("Reporter", "Ali") in lines
    assert ("Near miss", "No") in lines
    assert ("Location", "-") in lines


# mom_warning Tests

# Test that no warning is given when the incident does not go to MOM
def test_mom_warning_not_reportable():
    assert gui.mom_warning({"mom_reportable": "No", "deadline": "N/A"}) is None

# Test that an upcoming deadline gives a normal warning
def test_mom_warning_upcoming():
    due = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    warning = gui.mom_warning({"mom_reportable": "Yes", "deadline": due})
    assert warning == f"This incident must be reported to MOM by {due}."

# Test that a passed deadline is marked overdue
def test_mom_warning_overdue():
    due = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert gui.mom_warning({"mom_reportable": "Yes", "deadline": due}).startswith("OVERDUE")


# load_env_file Tests

# Test that a key is read from the file, quotes and comments are handled, and a key already set is kept
def test_load_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nGUI_TEST_KEY='abc123'\nGUI_TEST_SET=from_file\n", encoding="utf-8")
    monkeypatch.delenv("GUI_TEST_KEY", raising=False)
    monkeypatch.setenv("GUI_TEST_SET", "already_set")

    gui.load_env_file(str(env_file))

    assert os.environ["GUI_TEST_KEY"] == "abc123"
    assert os.environ["GUI_TEST_SET"] == "already_set"
    monkeypatch.delenv("GUI_TEST_KEY", raising=False)

# Test that a missing .env file is ignored
def test_load_env_file_missing(tmp_path):
    gui.load_env_file(str(tmp_path / "nope.env"))
