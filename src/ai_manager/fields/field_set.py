# ------- #
# Imports
# ------- #

from src.ai_manager.fields.field import Field

# ----- #
# Class
# ----- #

# A Group of Fields Checked and Described Together (e.g. the Worker's Details, or the AI's Analysis)
class FieldSet:
    def __init__(self, fields: list[Field]):
        self._fields = fields

    def names(self) -> list[str]:
        return [field.name for field in self._fields]

    # All Field Lines for a Prompt
    def describe(self) -> str:
        return "\n".join([field.describe() for field in self._fields])

    # JSON Schema Requiring Every Field in this Set, Each with its Own Type
    def schema(self) -> dict:
        properties = {field.name: field.schema() for field in self._fields}
        return {"type": "OBJECT", "properties": properties, "required": self.names()}

    # Fields in the Report that are Missing or Not Valid
    def invalid(self, report: dict) -> list[Field]:
        return [field for field in self._fields if not field.is_valid(report.get(field.name))]
