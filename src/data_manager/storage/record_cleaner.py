# ------- #
# Imports
# ------- #

from typing import Any

import pandas as pd

from src.data_manager.constants import DATE_FIELD, DATE_FORMAT, REQUIRED_FIELDS, URGENCY_COLUMN

# ----- #
# Class
# ----- #


# Checks and tidies one report before it is saved or shown
# Rejects a report that is missing a required field or has an invalid date or score
class RecordCleaner:

    # required_fields are the fields every report must have (defaults to REQUIRED_FIELDS)
    def __init__(self, required_fields: list[str] = REQUIRED_FIELDS) -> None:
        self._required_fields = list(required_fields)

    # Returns a cleaned copy of the report, or None if it must be rejected
    def clean(self, record: dict) -> dict | None:
        # If input is not a dictionary, rejects it
        if not isinstance(record, dict):
            return None

        # Makes a copy so that the original is not affected
        cleaned = record.copy()

        # Strip whitespace from every text value
        for k, v in cleaned.items():
            if isinstance(v, str):
                cleaned[k] = v.strip()
            else:
                cleaned[k] = v

        # Required fields must exist and be non-empty
        for field in self._required_fields:
            value = cleaned.get(field)
            if value is None or (isinstance(value, str) and value == "") or pd.isna(value):
                return None

        try:
            # Converts date to exact YYYY-MM-DD format
            cleaned[DATE_FIELD] = pd.to_datetime(
                cleaned[DATE_FIELD], format=DATE_FORMAT
            ).strftime(DATE_FORMAT)
            # Converts score to decimal number
            cleaned[URGENCY_COLUMN] = float(cleaned[URGENCY_COLUMN])
        # If conversion fails, reject the input
        except (ValueError, TypeError):
            return None

        # Returns cleaned copy
        return cleaned

    # Function purpose : converts value into a standardised format for fair comparison
    # Example : "5" and 5.0 count as equal, or lowercase and trims such that "Fire" and "fire" are equal
    def comparable(self, value: Any) -> float | str:
        try:
            return float(value)
        except (ValueError, TypeError):
            return str(value).strip().lower()