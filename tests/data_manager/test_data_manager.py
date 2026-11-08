# Imports

import atexit
import itertools
import os
import shutil
import tempfile
from datetime import timedelta

import pandas as pd

# Import the Module Under Test
from src.data_manager.filters.default_filters import create_default_filters
from src.data_manager.manager import DataManager
from src.data_manager.storage.csv_record_store import CsvRecordStore
from tests.data_manager.class_shout_filter import ShoutFilter

# ------- #
# Helpers
# ------- #

# A Date String (YYYY-MM-DD) that is 'days' Days From Today (Negative = in the Past)
def day(days):
    return (pd.Timestamp.today().normalize() + timedelta(days=days)).strftime("%Y-%m-%d")


# One Valid Report (Change Anything with Keyword Arguments)
def make_report(name, score, location="Office", severity="Low", cause="Other", date_offset=-1, deadline="N/A"):
    return {"reporter_name": name, "incident_date": day(date_offset), "importance_score": score, "location": location,
            "ai_severity": severity, "root_cause_category": cause, "deadline": deadline}


# Six Reports with Different Scores, Dates, Deadlines and Locations (Highest Score First: Eli, Ann, Fay, Ben, Cai, Dee)
def sample_reports():
    return [
        make_report("Ann", 9.5, "Warehouse (Level 2)", "High", "Fire", date_offset=-1, deadline=day(2)),
        make_report("Ben", 5, "Head Office", "Low", "Slip or Trip", date_offset=-20),
        make_report("Cai", 3.2, "Office", "Medium", "Machinery", date_offset=-100, deadline=day(-3)),
        make_report("Dee", 0.5, "Ubi Industrial Park, Block 1", "Low", "Other", date_offset=-300, deadline=day(6)),
        make_report("Eli", 12, "Dock [North]", "Critical", "Electrical", date_offset=-6, deadline=day(30)),
        make_report("Fay", 7, "Office", "High", "Water", date_offset=-1),
    ]


# A Temporary Folder for the Test Reports. It is Deleted When the Tests End, and the Real data/data.csv is Never Touched
TEMP_FOLDER = tempfile.mkdtemp()
atexit.register(shutil.rmtree, TEMP_FOLDER, ignore_errors=True)
file_numbers = itertools.count(1)


# A CsvRecordStore on a New, Empty CSV File (Every Test Gets Its Own File, so Tests Cannot Affect Each Other)
def make_store():
    return CsvRecordStore(os.path.join(TEMP_FOLDER, f"data_{next(file_numbers)}.csv"))


# A DataManager that Keeps its Reports in a Temporary CSV File. filters=None Means the App's Default Filters
def make_manager(reports=None, filters=None):
    store = make_store()
    manager = DataManager(store, create_default_filters() if filters is None else filters)
    for report in (sample_reports() if reports is None else reports):
        assert manager.save_record(report)[0], report
    return manager


def names(table):
    return list(table.get("reporter_name", []))

# ----------------- #
# Save and Read
# ----------------- #

# Saving, Loading and the Column Names All Go Through the Store the DataManager Was Given
def test_saving_and_reading_go_through_the_store():
    store = make_store()
    manager = DataManager(store, create_default_filters())
    assert manager.save_record(make_report("Ann", 5)) == (True, "Record saved.")
    assert list(store.load_records()["reporter_name"]) == ["Ann"]
    assert manager.load_records().equals(store.load_records())
    assert manager.get_column_names() == store.get_column_names()
    assert manager.save_record(make_report("Ann", 5))[0] is False  # the store's duplicate check is what answers


def test_reports_are_most_urgent_first_unless_ascending():
    manager = make_manager()
    assert names(manager.load_records()) == ["Eli", "Ann", "Fay", "Ben", "Cai", "Dee"]
    assert names(manager.load_records(ascending=True)) == ["Dee", "Cai", "Ben", "Fay", "Ann", "Eli"]


def test_an_empty_manager_gives_empty_results_everywhere():
    manager = make_manager(reports=[])
    assert manager.load_records().empty
    assert manager.get_column_names() == []
    assert manager.load_matching_records("ai_severity", "High").empty
    for column in ("ai_severity", "importance_score", "incident_date", "deadline", "location", "no_such_column"):
        assert manager.get_unique_values(column) == [], column

# ------------------ #
# Menu Choices
# ------------------ #

def test_score_date_and_deadline_offer_their_fixed_choices():
    manager = make_manager()
    assert manager.get_unique_values("importance_score") == ["0 to under 2", "2 to under 4", "4 to under 6", "6 to under 8", "8+"]
    assert manager.get_unique_values("incident_date") == ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last 365 Days"]
    assert manager.get_unique_values("deadline") == ["Overdue", "Due within 3 days", "Due within 7 days", "All upcoming"]


def test_other_columns_offer_the_saved_values_once_in_alphabetical_order():
    manager = make_manager()
    assert manager.get_unique_values("ai_severity") == ["Critical", "High", "Low", "Medium"]
    assert manager.get_unique_values("reporter_name") == ["Ann", "Ben", "Cai", "Dee", "Eli", "Fay"]
    assert manager.get_unique_values("location") == ["Dock [North]", "Head Office", "Office", "Ubi Industrial Park, Block 1", "Warehouse (Level 2)"]


def test_a_column_that_does_not_exist_offers_nothing():
    assert make_manager().get_unique_values("no_such_column") == []

# ------------------ #
# Filtering
# ------------------ #

# Text Columns Match the Whole Text, Ignoring Case and Spaces
def test_text_columns_match_the_exact_text():
    manager = make_manager()
    assert names(manager.load_matching_records("ai_severity", "high")) == ["Ann", "Fay"]
    assert names(manager.load_matching_records("ai_severity", "  HIGH ")) == ["Ann", "Fay"]
    assert names(manager.load_matching_records("root_cause_category", "fire")) == ["Ann"]
    assert manager.load_matching_records("ai_severity", "Hig").empty      # part of the text is not enough
    assert manager.load_matching_records("root_cause_category", "Fir").empty


# Location is a Keyword Search: Part of the Text is Enough, and Typed Symbols are Plain Text
def test_location_is_a_keyword_search():
    manager = make_manager()
    assert names(manager.load_matching_records("location", "office")) == ["Fay", "Ben", "Cai"]
    assert names(manager.load_matching_records("location", "(level 2)")) == ["Ann"]
    assert names(manager.load_matching_records("location", "[north")) == ["Eli"]
    assert names(manager.load_matching_records("location", "block 1")) == ["Dee"]
    assert manager.load_matching_records("location", "").empty
    assert manager.load_matching_records("location", "canteen").empty


def test_score_bands():
    manager = make_manager()
    assert names(manager.load_matching_records("importance_score", "8+")) == ["Eli", "Ann"]
    assert names(manager.load_matching_records("importance_score", "6 to under 8")) == ["Fay"]
    assert names(manager.load_matching_records("importance_score", "4 to under 6")) == ["Ben"]
    assert names(manager.load_matching_records("importance_score", "2 to under 4")) == ["Cai"]
    assert names(manager.load_matching_records("importance_score", "0 to under 2")) == ["Dee"]
    assert manager.load_matching_records("importance_score", "").empty      # used to crash


def test_date_ranges():
    manager = make_manager()
    assert names(manager.load_matching_records("incident_date", "Last 7 Days")) == ["Eli", "Ann", "Fay"]
    assert names(manager.load_matching_records("incident_date", "Last 30 Days")) == ["Eli", "Ann", "Fay", "Ben"]
    assert names(manager.load_matching_records("incident_date", "Last 365 Days")) == ["Eli", "Ann", "Fay", "Ben", "Cai", "Dee"]
    assert manager.load_matching_records("incident_date", "Last 12 Years").empty


# Reports Without a MOM Deadline ("N/A") Never Match a Deadline Window
def test_deadline_windows():
    manager = make_manager()
    assert names(manager.load_matching_records("deadline", "Overdue")) == ["Cai"]
    assert names(manager.load_matching_records("deadline", "Due within 3 days")) == ["Ann"]
    assert names(manager.load_matching_records("deadline", "Due within 7 days")) == ["Ann", "Dee"]
    assert names(manager.load_matching_records("deadline", "All upcoming")) == ["Eli", "Ann", "Dee"]
    assert manager.load_matching_records("deadline", "N/A").empty


def test_filtered_results_follow_the_ascending_flag():
    manager = make_manager()
    assert names(manager.load_matching_records("location", "office", ascending=True)) == ["Cai", "Ben", "Fay"]
    assert names(manager.load_matching_records("location", "office", ascending=False)) == ["Fay", "Ben", "Cai"]


def test_nothing_found_or_no_such_column_gives_an_empty_table():
    manager = make_manager()
    assert manager.load_matching_records("ai_severity", "Nope").empty
    assert manager.load_matching_records("no_such_column", "x").empty


def test_matching_reports_keep_all_columns_and_are_numbered_from_zero():
    manager = make_manager()
    result = manager.load_matching_records("ai_severity", "high")
    assert list(result.columns) == list(manager.load_records().columns)
    assert list(result.index) == [0, 1]


# A Report Saved Now is Found by the Very Next Filter
def test_new_reports_are_found_straight_away():
    manager = make_manager()
    assert len(manager.load_matching_records("ai_severity", "High")) == 2
    manager.save_record(make_report("Gus", 6.5, severity="High"))
    assert names(manager.load_matching_records("ai_severity", "High")) == ["Ann", "Fay", "Gus"]
    assert "Gus" in manager.get_unique_values("reporter_name")

# ------------------------------- #
# The Filters it is Given
# ------------------------------- #

# The Filters are Passed in, so Without Any the Special Columns Fall Back to Exact Text Too
def test_columns_without_a_filter_in_the_dictionary_match_exact_text():
    manager = make_manager(filters={})
    assert names(manager.load_matching_records("importance_score", "9.5")) == ["Ann"]    # the exact text "9.5", not a band
    assert manager.load_matching_records("importance_score", "8+").empty
    assert names(manager.load_matching_records("location", "office")) == ["Fay", "Cai"]  # exactly "Office", not "Head Office"
    assert manager.load_matching_records("location", "offic").empty                     # part of the text is not enough
    assert manager.get_unique_values("importance_score")[0] == "0.5"                    # the saved values, not the bands


# A New Kind of Filter Works Without Changing the DataManager (Open/Closed Principle)
def test_a_filter_it_is_given_is_the_one_used():
    shout = ShoutFilter("location")
    manager = make_manager(filters={"location": shout})
    assert names(manager.load_matching_records("location", "anything")) == ["Eli"]
    assert shout.calls == ["anything"]
    assert manager.get_unique_values("location") == ["only choice"]
    assert names(manager.load_matching_records("ai_severity", "high")) == ["Ann", "Fay"]  # other columns are unaffected


# The Dictionary is Copied, so Changing it Afterwards Does Not Change the DataManager
def test_the_filters_given_are_copied():
    filters = create_default_filters()
    manager = make_manager(filters=filters)
    filters.clear()
    assert names(manager.load_matching_records("location", "office")) == ["Fay", "Ben", "Cai"]


# The Filters Must be Given, There is No Hidden Default That Would Quietly Change the Results
def test_the_filters_are_required():
    for arguments in ((make_store(),), (make_store(), None)):
        try:
            DataManager(*arguments)
        except TypeError:
            continue
        raise AssertionError(f"DataManager{arguments} should raise TypeError")


# The Public Interface is the Five Methods in the UML (Everything Else is Private)
def test_the_public_methods_are_the_five_in_the_uml():
    public = sorted(name for name in dir(DataManager) if not name.startswith("_"))
    assert public == ["get_column_names", "get_unique_values", "load_matching_records", "load_records", "save_record"]
