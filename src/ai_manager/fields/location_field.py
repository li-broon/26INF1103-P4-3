# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for "Main Site, Exact Area" or "Main Site, Exact Area, Even More Exact Spot": 2 or 3 Non-Empty Parts Split by Commas
class LocationField(Field):
    MIN_PARTS = 2
    MAX_PARTS = 3

    def _check(self, value) -> bool:
        if not isinstance(value, str):
            return False
        parts = [part.strip() for part in value.split(",")]
        return self.MIN_PARTS <= len(parts) <= self.MAX_PARTS and "" not in parts
