import math


# Turns messy AI generated values into clean Python ones (never raises).
class FieldParser:
    # Text the AI may use for "true"
    TRUE_WORDS = frozenset({"true", "yes", "y", "1"})

    # Convert an AI generated value to a boolean
    @staticmethod
    def to_bool(value):
        if isinstance(value, str):
            return value.strip().lower() in FieldParser.TRUE_WORDS
        return bool(value)

    # Convert an AI generated value to a float, anything that is not a usable number becomes 0.0
    @staticmethod
    def to_float(value):
        try:
            number = float(value.strip() if isinstance(value, str) else value)
        except (TypeError, ValueError, OverflowError):
            return 0.0
        return number if math.isfinite(number) else 0.0