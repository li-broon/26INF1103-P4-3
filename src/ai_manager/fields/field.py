# ------- #
# Imports
# ------- #

from abc import ABC, abstractmethod
from src.ai_manager.constants import UNKNOWN_VALUE

# ----- #
# Class
# ----- #

# One Field of the Incident Report: its Name, what it Means, and Whether a Value is Valid
class Field(ABC):
    SCHEMA_TYPE = "STRING"   # Gemini's Type for this Field (Subclasses that are Not Text Change it)

    def __init__(self, name: str, description: str, allows_unknown: bool = False):
        self._name = name
        self._description = description
        self._allows_unknown = allows_unknown

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    # Line Describing this Field in a Prompt (e.g. "- reporter_name: full name of the person reporting")
    def describe(self) -> str:
        return f"- {self._name}: {self._description}"

    # This Field's Part of the JSON Schema Gemini Must Follow
    def schema(self) -> dict:
        return {"type": self.SCHEMA_TYPE}

    # Shared Check for Every Field: "unknown" is Accepted Only if this Field Allows it, Everything Else is Checked by the Subclass
    def is_valid(self, value) -> bool:
        if self._allows_unknown and value == UNKNOWN_VALUE:
            return True
        return self._check(value)

    # Each Kind of Field Decides what a Valid Value Looks Like
    @abstractmethod
    def _check(self, value) -> bool:
        pass
