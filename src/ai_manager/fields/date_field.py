# ------- #
# Imports
# ------- #

from datetime import datetime
from src.ai_manager.constants import DATE_FORMAT
from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for a Real Date in YYYY-MM-DD that is Not in the Future
class DateField(Field):
    def _check(self, value) -> bool:
        try:
            return datetime.strptime(value, DATE_FORMAT) <= datetime.now()
        except (TypeError, ValueError):
            return False
