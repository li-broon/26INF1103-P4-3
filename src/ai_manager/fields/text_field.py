# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for a Non-Empty String
class TextField(Field):
    def _check(self, value) -> bool:
        return isinstance(value, str) and value.strip() != ""
