# ------- #
# Imports
# ------- #

from datetime import datetime
from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for a Time in 24h HH:MM
class TimeField(Field):
    def _check(self, value) -> bool:
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except (TypeError, ValueError):
            return False