# Convert an AI generated value to a boolean
def to_bool(value):
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)
