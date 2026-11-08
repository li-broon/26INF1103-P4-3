# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# Check for a Real True/ False
class BooleanField(Field):
    SCHEMA_TYPE = "BOOLEAN"

    def _check(self, value) -> bool:
        return isinstance(value, bool)
