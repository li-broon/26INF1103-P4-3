# ---------------- #
# Import and Setup
# ---------------- #
from datetime import date, timedelta

import pandas as pd
import pytest

# Tkinter is Part of Python, but Some Linux Installs Leave it Out: Skip Rather than Fail
pytest.importorskip("tkinter")
from src.gui_manager import constants as gui
from src.gui_manager.display.window_report_formatter import WindowReportFormatter
from src.io_manager.constants import TABLE_COLUMNS, FULL_REPORT_FIELDS

# Only the Formatter is Tested, so No Window is Opened (CI Has No Display)
formatter = WindowReportFormatter()


# score_colours Tests

# Test that each score band gets its own colour, most urgent in red
def test_score_colours_bands():
    assert formatter.score_colours(9.1) == (gui.DANGER, gui.DANGER_SOFT)
    assert formatter.score_colours(8) == (gui.DANGER, gui.DANGER_SOFT)
    assert formatter.score_colours("6.5") == (gui.ORANGE, gui.ORANGE_SOFT)
    assert formatter.score_colours(4) == (gui.WARNING, gui.WARNING_SOFT)
    assert formatter.score_colours(1.2) == (gui.SUCCESS, gui.SUCCESS_SOFT)

# Test that a missing or broken score gets a neutral colour instead of crashing
def test_score_colours_bad_values():
    assert formatter.score_colours(None) == (gui.MUTED, gui.SURFACE_ALT)
    assert formatter.score_colours("abc") == (gui.MUTED, gui.SURFACE_ALT)
    assert formatter.score_colours(-3) == (gui.SUCCESS, gui.SUCCESS_SOFT)


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
    assert formatter.report_stats(table) == {"total": 3, "mom": 2, "overdue": 1, "hospitalised": 1}

# Test that an empty table gives all zeros
def test_report_stats_empty():
    assert formatter.report_stats(pd.DataFrame()) == {"total": 0, "mom": 0, "overdue": 0, "hospitalised": 0}


# display_value Tests

# Test that blanks, None and NaN all show as "-"
def test_display_value_blanks():
    assert formatter.display_value(None) == "-"
    assert formatter.display_value("") == "-"
    assert formatter.display_value("   ") == "-"
    assert formatter.display_value(float("nan")) == "-"

# Test that real values are shown as text
def test_display_value_keeps_values():
    assert formatter.display_value(7.5) == "7.5"
    assert formatter.display_value(" Block A ") == "Block A"


# table_row_values Tests

# Test that a row is the row number then one value per table column, with YES/No for true/false
def test_table_row_values_order_and_yes_no():
    report = {"importance_score": 8.2, "ai_severity": "High", "hospitalised": True,
              "deadline": "2026-11-10", "root_cause_category": "Electrical",
              "location": "Plant 2", "incident_date": "2026-10-31"}
    values = formatter.table_row_values(3, report)
    assert values == [3, "8.2", "High", "YES", "2026-11-10", "Electrical", "Plant 2", "2026-10-31"]

# Test that missing columns show "-" instead of crashing
def test_table_row_values_missing_fields():
    values = formatter.table_row_values(1, {})
    assert values[1:] == ["-"] * len(TABLE_COLUMNS)


# needs_attention Tests

# Test that hospital cases and MOM cases are highlighted, others are not
def test_needs_attention():
    assert formatter.needs_attention({"hospitalised": "True", "mom_reportable": "No"})
    assert formatter.needs_attention({"hospitalised": False, "mom_reportable": "Yes"})
    assert not formatter.needs_attention({"hospitalised": False, "mom_reportable": "No"})


# full_report_lines Tests

# Test that every full report field is listed, with true/false shown as YES/No
def test_full_report_lines():
    lines = formatter.full_report_lines({"reporter_name": "Ali", "is_near_miss": False})
    assert len(lines) == len(FULL_REPORT_FIELDS)
    assert ("Reporter", "Ali") in lines
    assert ("Near miss", "No") in lines
    assert ("Location", "-") in lines


# mom_warning Tests

# Test that no warning is given when the incident does not go to MOM
def test_mom_warning_not_reportable():
    assert formatter.mom_warning({"mom_reportable": "No", "deadline": "N/A"}) is None

# Test that an upcoming deadline gives a normal warning
def test_mom_warning_upcoming():
    due = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    warning = formatter.mom_warning({"mom_reportable": "Yes", "deadline": due})
    assert warning == f"This incident must be reported to MOM by {due}."

# Test that a passed deadline is marked overdue
def test_mom_warning_overdue():
    due = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert formatter.mom_warning({"mom_reportable": "Yes", "deadline": due}).startswith("OVERDUE")


# transcript_turns Tests (shared with the terminal through ReportFormatter)

# Test that a saved transcript splits back into (speaker, text) turns, with a multi-line AI reply kept together
def test_transcript_turns_split_speakers_and_keep_continuation_lines():
    text = "Worker: saya jatuh\nAI: Maaf mendengarnya.\nDi mana tepatnya?\nWorker: di gudang"
    assert formatter.transcript_turns(text) == [
        ("Worker", "saya jatuh"), ("AI", "Maaf mendengarnya.\nDi mana tepatnya?"), ("Worker", "di gudang"),
    ]

# Test that a worker message containing "AI: " stays one worker turn, and that nothing or None gives no turns
def test_transcript_turns_edge_cases():
    assert formatter.transcript_turns("Worker: the sign said AI: keep out") == [("Worker", "the sign said AI: keep out")]
    assert formatter.transcript_turns("") == []
    assert formatter.transcript_turns(None) == []
