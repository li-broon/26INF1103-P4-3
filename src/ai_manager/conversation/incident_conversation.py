# ------- #
# Imports
# ------- #

import json
from datetime import datetime
from src.ai_manager.constants import UNKNOWN_VALUE
from src.ai_manager.fields.field import Field
from src.ai_manager.fields.field_set import FieldSet
from src.ai_manager.services.ai_service import AIService
from src.ai_manager.services.ai_service_error import AIServiceError
from src.ai_manager.conversation.ai_reply import AIReply
from src.ai_manager.conversation.analysis_task import AnalysisTask

# ----- #
# Class
# ----- #

# Class that Manages the Conversation with the Worker, Collects Their Details, and Gets the AI's Analysis
class IncidentConversation:
    MAX_FORMAT_RETRIES = 2   # Times the AI is Asked to Resend a Reply that is Not in Our JSON Format
    MAX_FIX_ATTEMPTS = 2     # Times the AI is Told to Fix a Report it Marked Complete Too Early

    SYSTEM_PROMPT = """\
You are a friendly workplace safety assistant helping a worker report an
incident. The worker may write in any language or a mix of languages.

Each turn:
- Always reply to the worker in the language they are using. Keep it short
  and simple, and ask for at most two missing details at a time.
- Keep track of every detail the worker has given so far. Store all values
  in English. Use null for anything not given yet. Never make things up.
  Only use 'none' or 'no injury' when the worker actually says so.
- Never guess from a vague answer. If an answer is unclear or not specific
  (e.g. "a while", "not long", "7 or 8", "my friends", "maybe"), keep that
  field null and politely ask again for an exact answer (a number, a single
  rating, names). If the worker still cannot be exact after you ask again,
  store their best estimate and add "(estimate)" to text answers.
- If the worker says they do not know a text detail at all (e.g. "idk",
  "not sure") and still does not know after you ask again, store
  "{unknown}" for it. Never leave a field null just because the
  worker does not know, or the report can never be finished.
- Work out relative dates like "yesterday" using today's date: {today}.
- If someone is still in danger, first tell them to call 995 and their supervisor.

Details to collect from the worker:
{worker_fields}

When ALL details above are filled, set "is_complete" to true, thank the
worker, and in that SAME reply fill in every one of these analysis fields.
They are your own judgement of the incident, so never ask the worker for
them and never leave them null:
{analysis_fields}
Until then, keep "is_complete" false and leave the analysis fields null.

Respond ONLY with JSON in this exact format:
{{
  "reply": "your message to the worker, in their language",
  "is_complete": false,
  "report": {{ every field listed above as a key }}
}}
"""

    BAD_JSON_MESSAGE = (
        "Your last reply was not valid JSON in the required format. "
        "Send the same reply again using ONLY the JSON format with the "
        "keys \"reply\", \"is_complete\" and \"report\"."
    )

    INCOMPLETE_MESSAGE = (
        "The report is not finished yet. Still missing or unclear: {fields}. "
        "Please give these details (or say you do not know) in your next message."
    )

    ANALYSIS_FAILED_MESSAGE = (
        "All your details are recorded, but the AI could not finish analysing the incident. "
        "Please send any message (for example 'ok') to try again."
    )

    def __init__(self, service: AIService, worker_fields: FieldSet, analysis_fields: FieldSet,
                 analysis_task: AnalysisTask):
        self._service = service
        self._worker_fields = worker_fields
        self._analysis_fields = analysis_fields
        self._analysis_task = analysis_task
        self._worker_messages = []
        system_prompt = self.SYSTEM_PROMPT.format(
            unknown=UNKNOWN_VALUE,
            today=datetime.now().strftime("%Y-%m-%d"),
            worker_fields=worker_fields.describe(),
            analysis_fields=analysis_fields.describe(),
        )
        self._chat = service.start_chat(system_prompt)

    # Send One Worker Message and Return an AIReply (is_complete is Only True when Every Field is Valid)
    def send(self, user_text: str) -> AIReply:
        reply = self._ask(user_text)
        if reply.error:
            return reply
        self._worker_messages.append(user_text)

        # If AI Says "complete" but Worker Details are Missing or Wrongly Formatted,  Tell it to Fix Them, up to MAX_FIX_ATTEMPTS Times
        for _ in range(self.MAX_FIX_ATTEMPTS):
            invalid = self._worker_fields.invalid(reply.report)
            if not (reply.is_complete and invalid):
                break
            reply = self._ask(self._build_fix_message(invalid))

        # Still Collecting Details (or an Error): Show the AI's Reply as Normal
        if not reply.is_complete:
            return reply

        # If AI Still Says "complete" with Worker Details Missing, Don't Show its "all done" Reply, Tell the Worker what is Missing
        invalid = self._worker_fields.invalid(reply.report)
        if invalid:
            names = ", ".join([field.name.replace("_", " ") for field in invalid])
            return AIReply(error=self.INCOMPLETE_MESSAGE.format(fields=names))

        # If Worker Details Done, but the Analysis is Empty or Not Valid, Ask for it in a Separate Request
        if self._analysis_fields.invalid(reply.report):
            analysis = self._analysis_task.run(reply.report, self._worker_messages)
            if analysis is None:
                return AIReply(error=self.ANALYSIS_FAILED_MESSAGE)
            reply.report.update(analysis)

        return reply

    # Send One Message and Return the Parsed Reply (If it is Not in Our JSON Format, Ask the AI to Resend, up to MAX_FORMAT_RETRIES Times)
    def _ask(self, message: str) -> AIReply:
        for _ in range(1 + self.MAX_FORMAT_RETRIES):
            try:
                reply_text = self._service.send_chat_message(self._chat, message)
            except AIServiceError as error:
                return AIReply(error=error.message, error_code=error.code, error_status=error.status)
            reply = self._parse(reply_text)
            if reply is not None:
                return reply
            message = self.BAD_JSON_MESSAGE
        return AIReply(error="The AI kept replying in the wrong format.")

    # Turn the Reply Text into an AIReply
    def _parse(self, text: str) -> AIReply | None:
        try:
            data = json.loads(text)
            
        # If the Reply is Not JSON or Not a Dict with the Right Keys, Return None so the AI is Asked to Resend
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict) or not isinstance(data.get("report"), dict):
            return None

        # The Reply is Shown to the Worker and is_complete Decides if the Report is Saved, so Both Must be the Right Type
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            return None
        if not isinstance(data.get("is_complete"), bool):
            return None

        # Keep Only Our Fields (Extra Keys from the AI would Otherwise become New Columns in data.csv)
        names = self._worker_fields.names() + self._analysis_fields.names()
        report = {name: data["report"].get(name) for name in names}
        return AIReply(reply, data["is_complete"], report)

    # Message Telling the AI which Worker Details to Correct or Ask For (Shows the Required Format of Each)
    def _build_fix_message(self, invalid_fields: list[Field]) -> str:
        details = "; ".join([f"{field.name} ({field.description})" for field in invalid_fields])
        return (
            "Not complete yet. These details are missing or not in the required format. "
            "Correct them from what the worker already said if you can, otherwise set "
            f"is_complete to false and ask the worker for: {details}. If the worker already said "
            f"twice that they do not know one of these, store \"{UNKNOWN_VALUE}\" for it instead "
            "(the incident date must still be a real date). Keep your reply to the worker in their language."
        )
