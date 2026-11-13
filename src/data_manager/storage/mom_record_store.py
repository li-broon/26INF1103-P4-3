# ------- #
# Imports
# ------- #

import hashlib
import logging
import os
from datetime import date

import pandas as pd

from src.data_manager.constants import (
    DATE_FORMAT, MOM_DATA_FILE, MOM_ID_FIELD, MOM_IDENTITY_FIELDS, MOM_REPORTED_FIELD, MOM_REPORTED_ON_FIELD,
    URGENCY_COLUMN,
)
from src.data_manager.storage.record_cleaner import RecordCleaner

# Used for debugging to log warnings and errors instead of printing them to the console
logger = logging.getLogger(__name__)

# Text Values that Mean "Yes" in the mom_reportable Column
YES_WORDS = ("yes", "true", "1", "1.0")

# ----- #
# Class
# ----- #

# The MOM Register: a Second CSV File that Only Holds the MOM Reportable Reports, Plus Whether the Safety Officer Has Reported Each One
class MomRecordStore:

    # data_file is the CSV the register is kept in
    def __init__(self, data_file: str = MOM_DATA_FILE) -> None:
        self._data_file = data_file
        self._data_folder = os.path.dirname(data_file)
        self._cleaner = RecordCleaner()  # Created and owned by this store

    # Adds one report to the register as "not reported yet". Only MOM reportable reports are accepted. Returns (success, message)
    def save_record(self, record: dict) -> tuple[bool, str]:
        cleaned = self._cleaner.clean(record)
        if cleaned is None:
            return False, "MOM record rejected: missing or invalid required field."
        if str(cleaned.get("mom_reportable", "")).strip().lower() not in YES_WORDS:
            return False, "MOM record rejected: the report is not MOM reportable."

        cleaned[MOM_ID_FIELD] = self.make_id(cleaned)
        cleaned[MOM_REPORTED_FIELD] = "No"
        cleaned[MOM_REPORTED_ON_FIELD] = ""

        table = self._load_for_update()
        if not table.empty and cleaned[MOM_ID_FIELD] in set(table[MOM_ID_FIELD].dropna()):
            return False, "MOM record rejected: this report is already in the MOM register."

        new_row = pd.DataFrame([cleaned])
        table = new_row if table.empty else pd.concat([table, new_row], ignore_index=True)
        return self._write(table, "MOM record saved.")

    # Adds every MOM reportable report in 'table' that is not in the register yet (used once at start-up, so reports saved before the register existed show up too). Returns how many were added
    def sync(self, table: pd.DataFrame) -> int:
        if table is None or table.empty:
            return 0
        added = 0
        for record in table.to_dict("records"):
            if self.save_record(record)[0]:
                added += 1
        return added

    # Ticks (reported=True) or unticks (reported=False) one report, writing straight to the register file. Returns (success, message)
    def set_reported(self, mom_id: str, reported: bool) -> tuple[bool, str]:
        table = self._read()
        if table.empty or MOM_ID_FIELD not in table.columns:
            return False, "MOM register is empty."

        rows = table.index[table[MOM_ID_FIELD] == mom_id]
        if len(rows) == 0:
            return False, "That report is not in the MOM register."

        table.loc[rows, MOM_REPORTED_FIELD] = "Yes" if reported else "No"
        table.loc[rows, MOM_REPORTED_ON_FIELD] = date.today().strftime(DATE_FORMAT) if reported else ""
        return self._write(table, "MOM register updated.")

    # Every report in the register: still-to-report first (soonest deadline first, then most urgent), reported ones last. Empty if there are none
    def load_records(self) -> pd.DataFrame:
        table = self._read()
        if table.empty or MOM_ID_FIELD not in table.columns:
            return pd.DataFrame()

        table[URGENCY_COLUMN] = pd.to_numeric(table[URGENCY_COLUMN], errors="coerce")
        table["_reported"] = table[MOM_REPORTED_FIELD].fillna("No").str.strip().str.lower().isin(YES_WORDS)
        # "Check incident date" and other non-dates become NaT, which sorts last
        table["_due"] = pd.to_datetime(table["deadline"], format=DATE_FORMAT, errors="coerce")

        table = table.sort_values(by=["_reported", "_due", URGENCY_COLUMN], ascending=[True, True, False],
                                  na_position="last")
        return table.drop(columns=["_reported", "_due"]).reset_index(drop=True)

    # The same report always gets the same id, so a report can never be added twice
    def make_id(self, record: dict) -> str:
        parts = []
        for field in MOM_IDENTITY_FIELDS:
            value = record.get(field)
            parts.append("" if value is None or pd.isna(value) else str(value).strip().lower())
        return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]

    # Read the register as text (so an id like "12e45" is never turned into a number); blank cells are NaN, an unreadable file is empty
    def _read(self) -> pd.DataFrame:
        if not os.path.exists(self._data_file) or os.path.getsize(self._data_file) == 0:
            return pd.DataFrame()
        try:
            return pd.read_csv(self._data_file, dtype=str, keep_default_na=False, na_values=[""])
        except Exception as e:
            logger.error("Could not read '%s': %s", self._data_file, e)
            return pd.DataFrame()

    # Like _read, but an unreadable file is backed up first so saving never destroys it
    def _load_for_update(self) -> pd.DataFrame:
        table = self._read()
        if table.empty and os.path.exists(self._data_file) and os.path.getsize(self._data_file) > 0:
            backup = self._data_file.replace(".csv", "_backup.csv")
            os.replace(self._data_file, backup)
            logger.warning("Unreadable MOM file backed up to '%s'.", backup)
        return table

    # Write to a temporary file first, then replace the real one, so a failed write loses nothing
    def _write(self, table: pd.DataFrame, success_message: str) -> tuple[bool, str]:
        os.makedirs(self._data_folder, exist_ok=True)
        temp_file = self._data_file + ".tmp"
        try:
            table.to_csv(temp_file, index=False)
            os.replace(temp_file, self._data_file)
        except OSError as e:
            logger.error("Could not write '%s': %s", self._data_file, e)
            return False, "MOM register could not be saved (file write error)."
        return True, success_message
