# ------- #
# Imports
# ------- #

import json
from src.ai_manager.fields.field_set import FieldSet
from src.ai_manager.services.ai_service import AIService
from src.ai_manager.services.ai_service_error import AIServiceError

# ----- #
# Class
# ----- #

# Separate One-Off Request for the AI's Own Analysis (Used when the Chat Finished the Worker's Details but Left the Analysis Empty or Invalid)
class AnalysisTask:
    MAX_ATTEMPTS = 3

    PROMPT = """\
You are a workplace safety analyst. A worker has finished reporting an
incident. Using the report and the worker's own messages below, give your
own judgement of the incident. Write in English, except "detected_language",
which names the language(s) the worker wrote in.

Incident report:
{report}

Worker's messages:
{messages}

Fields to return:
{fields}

Respond ONLY with a JSON object containing exactly these fields.
"""

    def __init__(self, service: AIService, worker_fields: FieldSet, analysis_fields: FieldSet):
        self._service = service
        self._worker_fields = worker_fields
        self._analysis_fields = analysis_fields

    # Returns the Analysis Fields as a Dict, or None if the AI Could Not Give a Valid Analysis
    def run(self, report: dict, worker_messages: list[str]) -> dict | None:
        worker_details = {name: report.get(name) for name in self._worker_fields.names()}
        prompt = self.PROMPT.format(
            report=json.dumps(worker_details, indent=2, ensure_ascii=False),
            messages="\n".join([f"- {text}" for text in worker_messages]) or "- (not available)",
            fields=self._analysis_fields.describe(),
        )
        # Shape Gemini Must Follow (Forces the Allowed Values and Real true/false), Built from the Analysis Fields
        schema = self._analysis_fields.schema()
        for _ in range(self.MAX_ATTEMPTS):
            try:
                reply_text = self._service.generate_json(prompt, schema)
            except AIServiceError:
                return None
            analysis = self._parse(reply_text)
            if analysis is not None:
                return analysis
        return None

    # Turn the Reply into a Dict of the Analysis Fields (None if it is Not JSON or Any Field is Not Valid)
    def _parse(self, text: str) -> dict | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        analysis = {name: data.get(name) for name in self._analysis_fields.names()}
        if self._analysis_fields.invalid(analysis):
            return None
        return analysis
