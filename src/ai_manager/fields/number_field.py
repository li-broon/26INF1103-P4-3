# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for a Number of 0 or More
class NumberField(Field):
    def _check(self, value) -> bool:
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        return is_number and 0 <= value < float("inf")
