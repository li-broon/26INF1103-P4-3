# ------- #
# Imports
# ------- #

import os
import shutil
import tempfile
from datetime import timedelta

import pandas as pd

from src.data_manager.filters.default_filters import create_default_filters
from src.data_manager.manager import DataManager
from src.data_manager.storage.csv_record_store import CsvRecordStore
from tests.fakes.recording_filter import RecordingFilter


# Tests for DataManager: Saving, Reading, Menu Choices and Filtering, on Temporary CSV Files (data/data.csv is Never Touched)
class TestDataManager:

    # Every Test Gets its Own Temporary Folder, Deleted Afterwards, so Tests Cannot Affect Each Other
    def setup_method(self):
        self._folder = tempfile.mkdtemp()
        self._files_made = 0

    def teardown_method(self):
        shutil.rmtree(self._folder, ignore_errors=True)

    # ---------------- Helpers ---------------- #

    # A Date String (YYYY-MM-DD) that is 'days' Days From Today (Negative = in the Past)
    def _day(self, days: int) -> str:
        return (pd.Timestamp.today().normalize() + timedelta(days=days)).strftime("%Y-%m-%d")

    # One Valid Report (Change Anything with Keyword Arguments)
    def _report(self, name: str, score: float, location: str = "Office", severity: str = "Low", cause: str = "Other",
                date_offset: int = -1, deadline: str = "N/A") -> dict:
        return {"reporter_name": name, "incident_date": self._day(date_offset), "importance_score": score,
                "location": location, "ai_severity": severity, "root_cause_category": cause, "deadline": deadline}

    # Six Reports with Different Scores, Dates, Deadlines and Locations (Highest Score First: Eli, Ann, Fay, Ben, Cai, Dee)
    def _sample_reports(self) -> list[dict]:
        return [
            self._report("Ann", 9.5, "Warehouse (Level 2)", "High", "Fire", date_offset=-1, deadline=self._day(2)),
            self._report("Ben", 5, "Head Office", "Low", "Slip or Trip", date_offset=-20),
            self._report("Cai", 3.2, "Office", "Medium", "Machinery", date_offset=-100, deadline=self._day(-3)),
            self._report("Dee", 0.5, "Ubi Industrial Park, Block 1", "Low", "Other", date_offset=-300, deadline=self._day(6)),
            self._report("Eli", 12, "Dock [North]", "Critical", "Electrical", date_offset=-6, deadline=self._day(30)),
            self._report("Fay", 7, "Office", "High", "Water", date_offset=-1),
        ]

    # A CsvRecordStore on a New, Empty CSV File
    def _store(self) -> CsvRecordStore:
        self._files_made += 1
        return CsvRecordStore(os.path.join(self._folder, f"data_{self._files_made}.csv"))

    # A DataManager on a Temporary CSV File, Holding the Six Sample Reports Unless Told Otherwise (filters=None Means the App's Default Filters)
    def _manager(self, reports: list[dict] | None = None, filters: dict | None = None) -> DataManager:
        manager = DataManager(self._store(), create_default_filters() if filters is None else filters)
        for report in (self._sample_reports() if reports is None else reports):
            assert manager.save_record(report)[0], report
        return manager

    def _names(self, table: pd.DataFrame) -> list[str]:
        return list(table.get("reporter_name", []))

    # ---------------- Save and Read ---------------- #

    # Saving, Loading and the Column Names All Go Through the Store the DataManager Was Given
    def test_saving_and_reading_go_through_the_store(self):
        store = self._store()
        manager = DataManager(store, create_default_filters())
        assert manager.save_record(self._report("Ann", 5)) == (True, "Record saved.")
        assert list(store.load_records()["reporter_name"]) == ["Ann"]
        assert manager.load_records().equals(store.load_records())
        assert manager.get_column_names() == store.get_column_names()
        assert manager.save_record(self._report("Ann", 5))[0] is False  # the store's duplicate check is what answers

    def test_reports_are_most_urgent_first_unless_ascending(self):
        manager = self._manager()
        assert self._names(manager.load_records()) == ["Eli", "Ann", "Fay", "Ben", "Cai", "Dee"]
        assert self._names(manager.load_records(ascending=True)) == ["Dee", "Cai", "Ben", "Fay", "Ann", "Eli"]

    def test_an_empty_manager_gives_empty_results_everywhere(self):
        manager = self._manager(reports=[])
        assert manager.load_records().empty
        assert manager.get_column_names() == []
        assert manager.load_matching_records("ai_severity", "High").empty
        for column in ("ai_severity", "importance_score", "incident_date", "deadline", "location", "no_such_column"):
            assert manager.get_unique_values(column) == [], column

    # ---------------- Menu Choices ---------------- #

    def test_score_date_and_deadline_offer_their_fixed_choices(self):
        manager = self._manager()
        assert manager.get_unique_values("importance_score") == ["0 to under 2", "2 to under 4", "4 to under 6", "6 to under 8", "8+"]
        assert manager.get_unique_values("incident_date") == ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 180 Days", "Last 365 Days"]
        assert manager.get_unique_values("deadline") == ["Overdue", "Due within 3 days", "Due within 7 days", "All upcoming"]

    def test_other_columns_offer_the_saved_values_once_in_alphabetical_order(self):
        manager = self._manager()
        assert manager.get_unique_values("ai_severity") == ["Critical", "High", "Low", "Medium"]
        assert manager.get_unique_values("reporter_name") == ["Ann", "Ben", "Cai", "Dee", "Eli", "Fay"]
        assert manager.get_unique_values("location") == ["Dock [North]", "Head Office", "Office", "Ubi Industrial Park, Block 1", "Warehouse (Level 2)"]

    def test_a_column_that_does_not_exist_offers_nothing(self):
        assert self._manager().get_unique_values("no_such_column") == []

    # ---------------- Filtering ---------------- #

    # Text Columns Match the Whole Text, Ignoring Case and Spaces
    def test_text_columns_match_the_exact_text(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("ai_severity", "high")) == ["Ann", "Fay"]
        assert self._names(manager.load_matching_records("ai_severity", "  HIGH ")) == ["Ann", "Fay"]
        assert self._names(manager.load_matching_records("root_cause_category", "fire")) == ["Ann"]
        assert manager.load_matching_records("ai_severity", "Hig").empty      # part of the text is not enough
        assert manager.load_matching_records("root_cause_category", "Fir").empty

    # Location is a Keyword Search: Part of the Text is Enough, and Typed Symbols are Plain Text
    def test_location_is_a_keyword_search(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("location", "office")) == ["Fay", "Ben", "Cai"]
        assert self._names(manager.load_matching_records("location", "(level 2)")) == ["Ann"]
        assert self._names(manager.load_matching_records("location", "[north")) == ["Eli"]
        assert self._names(manager.load_matching_records("location", "block 1")) == ["Dee"]
        assert manager.load_matching_records("location", "").empty
        assert manager.load_matching_records("location", "canteen").empty

    def test_score_bands(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("importance_score", "8+")) == ["Eli", "Ann"]
        assert self._names(manager.load_matching_records("importance_score", "6 to under 8")) == ["Fay"]
        assert self._names(manager.load_matching_records("importance_score", "4 to under 6")) == ["Ben"]
        assert self._names(manager.load_matching_records("importance_score", "2 to under 4")) == ["Cai"]
        assert self._names(manager.load_matching_records("importance_score", "0 to under 2")) == ["Dee"]
        assert manager.load_matching_records("importance_score", "").empty      # used to crash

    def test_date_ranges(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("incident_date", "Last 7 Days")) == ["Eli", "Ann", "Fay"]
        assert self._names(manager.load_matching_records("incident_date", "Last 30 Days")) == ["Eli", "Ann", "Fay", "Ben"]
        assert self._names(manager.load_matching_records("incident_date", "Last 365 Days")) == ["Eli", "Ann", "Fay", "Ben", "Cai", "Dee"]
        assert manager.load_matching_records("incident_date", "Last 12 Years").empty

    # Reports Without a MOM Deadline ("N/A") Never Match a Deadline Window
    def test_deadline_windows(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("deadline", "Overdue")) == ["Cai"]
        assert self._names(manager.load_matching_records("deadline", "Due within 3 days")) == ["Ann"]
        assert self._names(manager.load_matching_records("deadline", "Due within 7 days")) == ["Ann", "Dee"]
        assert self._names(manager.load_matching_records("deadline", "All upcoming")) == ["Eli", "Ann", "Dee"]
        assert manager.load_matching_records("deadline", "N/A").empty

    def test_filtered_results_follow_the_ascending_flag(self):
        manager = self._manager()
        assert self._names(manager.load_matching_records("location", "office", ascending=True)) == ["Cai", "Ben", "Fay"]
        assert self._names(manager.load_matching_records("location", "office", ascending=False)) == ["Fay", "Ben", "Cai"]

    def test_nothing_found_or_no_such_column_gives_an_empty_table(self):
        manager = self._manager()
        assert manager.load_matching_records("ai_severity", "Nope").empty
        assert manager.load_matching_records("no_such_column", "x").empty

    def test_matching_reports_keep_all_columns_and_are_numbered_from_zero(self):
        manager = self._manager()
        result = manager.load_matching_records("ai_severity", "high")
        assert list(result.columns) == list(manager.load_records().columns)
        assert list(result.index) == [0, 1]

    # A Report Saved Now is Found by the Very Next Filter
    def test_new_reports_are_found_straight_away(self):
        manager = self._manager()
        assert len(manager.load_matching_records("ai_severity", "High")) == 2
        manager.save_record(self._report("Gus", 6.5, severity="High"))
        assert self._names(manager.load_matching_records("ai_severity", "High")) == ["Ann", "Fay", "Gus"]
        assert "Gus" in manager.get_unique_values("reporter_name")

    # ---------------- The Filters it is Given ---------------- #

    # The Filters are Passed in, so Without Any the Special Columns Fall Back to Exact Text Too
    def test_columns_without_a_filter_in_the_dictionary_match_exact_text(self):
        manager = self._manager(filters={})
        assert self._names(manager.load_matching_records("importance_score", "9.5")) == ["Ann"]    # the exact text "9.5", not a band
        assert manager.load_matching_records("importance_score", "8+").empty
        assert self._names(manager.load_matching_records("location", "office")) == ["Fay", "Cai"]  # exactly "Office", not "Head Office"
        assert manager.load_matching_records("location", "offic").empty                           # part of the text is not enough
        assert manager.get_unique_values("importance_score")[0] == "0.5"                          # the saved values, not the bands

    # A New Kind of Filter Works Without Changing the DataManager (Open/Closed Principle)
    def test_a_filter_it_is_given_is_the_one_used(self):
        location_filter = RecordingFilter("location")
        manager = self._manager(filters={"location": location_filter})
        assert self._names(manager.load_matching_records("location", "anything")) == ["Eli"]
        assert location_filter.asked_for == ["anything"]
        assert manager.get_unique_values("location") == ["only choice"]
        assert self._names(manager.load_matching_records("ai_severity", "high")) == ["Ann", "Fay"]  # other columns are unaffected

    # The Dictionary is Copied, so Changing it Afterwards Does Not Change the DataManager
    def test_the_filters_given_are_copied(self):
        filters = create_default_filters()
        manager = self._manager(filters=filters)
        filters.clear()
        assert self._names(manager.load_matching_records("location", "office")) == ["Fay", "Ben", "Cai"]

    # The Filters Must be Given, There is No Hidden Default That Would Quietly Change the Results
    def test_the_filters_are_required(self):
        for arguments in ((self._store(),), (self._store(), None)):
            try:
                DataManager(*arguments)
            except TypeError:
                continue
            raise AssertionError(f"DataManager{arguments} should raise TypeError")

    # The Public Interface is the Five Methods in the UML (Everything Else is Private)
    def test_the_public_methods_are_the_five_in_the_uml(self):
        public = sorted(name for name in dir(DataManager) if not name.startswith("_"))
        assert public == ["get_column_names", "get_unique_values", "load_matching_records", "load_records", "save_record"]
