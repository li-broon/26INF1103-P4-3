# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# One of a Fixed List of Choices (the Description is Built from the Choices)
class ChoiceField(Field):
    def __init__(self, name: str, choices: list[str]):
        super().__init__(name, "one of " + ", ".join(choices))
        self._choices = choices

    # Text Limited to the Choices
    def schema(self) -> dict:
        return {"type": self.SCHEMA_TYPE, "enum": self._choices}

    def _check(self, value) -> bool:
        return value in self._choices
