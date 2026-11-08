# ------- #
# Imports
# ------- #

from src.ai_manager.constants import SEVERITY_LEVELS, UNKNOWN_VALUE
from src.ai_manager.fields.boolean_field import BooleanField
from src.ai_manager.fields.choice_field import ChoiceField
from src.ai_manager.fields.date_field import DateField
from src.ai_manager.fields.field_set import FieldSet
from src.ai_manager.fields.number_field import NumberField
from src.ai_manager.fields.text_field import TextField
from src.ai_manager.fields.time_field import TimeField


# Tests for the Report Fields: Each Field Type Checks its Own Kind of Value
class TestReportFields:

    # Text Must be Non-Empty Text (Lists, Numbers and Blank Strings are Rejected)
    def test_text_field(self):
        field = TextField("location", "where it happened")
        assert field.is_valid("Tuas site")
        for bad in ["", "   ", None, 5, ["Tuas"]]:
            assert not field.is_valid(bad), bad

    # Dates Must be Real YYYY-MM-DD Dates and Not in the Future; "unknown" is Not Allowed
    def test_date_field(self):
        field = DateField("incident_date", "date in YYYY-MM-DD")
        assert field.is_valid("2026-10-13")
        for bad in ["13/10/2026", "2026-13-45", "yesterday", "2999-01-01", UNKNOWN_VALUE, None]:
            assert not field.is_valid(bad), bad

    # "unknown" is Accepted Only by Fields Created with allows_unknown=True
    def test_unknown_only_where_allowed(self):
        allows = TimeField("incident_time", "time", allows_unknown=True)
        strict = TimeField("incident_time", "time")
        assert allows.is_valid(UNKNOWN_VALUE)
        assert not strict.is_valid(UNKNOWN_VALUE)
        assert allows.is_valid("00:00") and not allows.is_valid("25:99")

    # true/false Must be Real Booleans, Not Text
    def test_boolean_field(self):
        field = BooleanField("hospitalised", "sent to hospital")
        assert field.is_valid(True) and field.is_valid(False)
        for bad in ["true", "yes", "no", 1, None]:
            assert not field.is_valid(bad), bad

    # Numbers Must be 0 or More (True/False and Text are Not Numbers)
    def test_number_field(self):
        field = NumberField("work_stoppage_hours", "hours")
        assert field.is_valid(0) and field.is_valid(2.5)
        for bad in [-1, "2", True, None, float("inf")]:
            assert not field.is_valid(bad), bad

    # Choice Fields Only Accept their Exact Choices, and Describe Them for the Prompt
    def test_choice_field(self):
        field = ChoiceField("ai_severity", SEVERITY_LEVELS)
        assert field.is_valid("Critical")
        assert not field.is_valid("critical")  # Wrong Casing would Score 0 in 'logic_manager'
        assert field.describe() == "- ai_severity: one of Low, Medium, High, Critical"

    # A FieldSet Checks Different Field Types Through the Same is_valid() Call (Polymorphism)
    def test_field_set_lists_invalid_fields(self):
        fields = FieldSet([
            TextField("reporter_name", "name"),
            DateField("incident_date", "date"),
            BooleanField("hospitalised", "hospital"),
        ])
        invalid = fields.invalid({"reporter_name": "Ravi", "incident_date": "13/10/2026", "hospitalised": "no"})
        assert [field.name for field in invalid] == ["incident_date", "hospitalised"]
        assert fields.names() == ["reporter_name", "incident_date", "hospitalised"]
