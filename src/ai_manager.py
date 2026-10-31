# ------- #
# Imports
# ------- #

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from google import genai
from google.genai import errors, types

# ---------------------- #
# Shared Report Settings
# ---------------------- #

# Allowed Values for the AI's Severity and Root Cause
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
ROOT_CAUSES = [
    "Electrical", "Chemical", "Fall from Height", "Struck by Object", "Machinery",
    "Slip or Trip", "Fire", "Water", "Safety Procedure Breach", "Other",
]

# Value the AI Stores when the Worker Really Does Not Know a Detail
UNKNOWN_VALUE = "unknown (worker could not say)"

# ------ #
# Errors
# ------ #

# Raised by an AIService when the AI Cannot be Reached or Replies with Error
class AIServiceError(Exception):
    def __init__(self, message: str, code: int = None, status: str = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

# ------------- #
# Report Fields
# ------------- #

# One Field of the Incident Report: its Name, what it Means, and Whether a Value is Valid
class Field(ABC):
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

    # Line Describing this Field in a Prompt (e.g. "- location: site and exact area")
    def describe(self) -> str:
        return f"- {self._name}: {self._description}"

    # Shared Check for Every Field: "unknown" is Accepted Only if this Field Allows it, Everything Else is Checked by the Subclass
    def is_valid(self, value) -> bool:
        if self._allows_unknown and value == UNKNOWN_VALUE:
            return True
        return self._check(value)

    # Each Kind of Field Decides what a Valid Value Looks Like
    @abstractmethod
    def _check(self, value) -> bool:
        pass

# Check for a Non-Empty String
class TextField(Field):
    def _check(self, value) -> bool:
        return isinstance(value, str) and value.strip() != ""

# Check for a Real Date in YYYY-MM-DD that is Not in the Future
class DateField(Field):
    def _check(self, value) -> bool:
        try:
            return datetime.strptime(value, "%Y-%m-%d") <= datetime.now()
        except (TypeError, ValueError):
            return False

# Check for a Time in 24h HH:MM
class TimeField(Field):
    def _check(self, value) -> bool:
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except (TypeError, ValueError):
            return False

# Check for a Real True/ False
class BooleanField(Field):
    def _check(self, value) -> bool:
        return isinstance(value, bool)

# Check for a Number of 0 or More
class NumberField(Field):
    def _check(self, value) -> bool:
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        return is_number and 0 <= value < float("inf")

# One of a Fixed List of Choices (the Description is Built from the Choices)
class ChoiceField(Field):
    def __init__(self, name: str, choices: list):
        super().__init__(name, "one of " + ", ".join(choices))
        self._choices = choices

    def _check(self, value) -> bool:
        return value in self._choices

# A Group of Fields Checked and Described Together (e.g. the Worker's Details, or the AI's Analysis)
class FieldSet:
    def __init__(self, fields: list):
        self._fields = fields

    def names(self) -> list:
        return [field.name for field in self._fields]

    # All Field Lines for a Prompt
    def describe(self) -> str:
        return "\n".join([field.describe() for field in self._fields])

    # Fields in the Report that are Missing or Not Valid
    def invalid(self, report: dict) -> list:
        return [field for field in self._fields if not field.is_valid(report.get(field.name))]

# ---------- #
# AI Replies
# ---------- #

# What the Conversation Returns to 'io_manager' after Each Worker Message
# (On Failure, 'error' Holds the Message, and error_code/error_status are Set for API Errors)
class AIReply:
    def __init__(self, reply: str = "", is_complete: bool = False, report: dict = None,
                 error: str = None, error_code: int = None, error_status: str = None):
        self.reply = reply
        self.is_complete = is_complete
        self.report = report if report is not None else {}
        self.error = error
        self.error_code = error_code
        self.error_status = error_status

# ----------- #
# AI Services
# ----------- #

# Contract Every AI Provider Must Follow (Gemini in the App, a Fake in the Tests)
class AIService(ABC):

    # Start a Conversation that Follows the System Prompt and Replies in JSON. Returns the Chat Session.
    @abstractmethod
    def start_chat(self, system_prompt: str):
        pass

    # Send One Message in a Chat and Return the Reply Text. Raises AIServiceError on Failure.
    @abstractmethod
    def send_chat_message(self, chat, message: str) -> str:
        pass

    # One-Off Request that Must Return JSON Matching the Schema. Returns the Reply Text. Raises AIServiceError on Failure.
    @abstractmethod
    def generate_json(self, prompt: str, schema: dict) -> str:
        pass

# Talks to Google Gemini: Handles the API Key, Timeout, and Retries when Gemini is Busy or Rate Limited
class GeminiService(AIService):
    MODEL = "gemini-3.5-flash-lite"
    TIMEOUT_MS = 60000          # Give Up on a Request after 60 Seconds (e.g. Stalled Connection)
    RETRY_CODES = (429, 503)    # Rate Limited / Busy: Waiting Can Fix These
    MAX_ATTEMPTS = 5            # Waits 3s, 6s, 9s, 12s between Attempts
    WAIT_SECONDS = 3

    MISSING_KEY_MESSAGE = """\
GEMINI_API_KEY is missing.
Create a file called '.env' in the project folder containing:
    GEMINI_API_KEY=your-key
Then run the program again. With Docker, pass the file in:
    docker run -it --rm --env-file .env -v "$(pwd)/data:/app/data" inf1103-p4"""

    # Raise AIServiceError if API Key is Not Set
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise AIServiceError(self.MISSING_KEY_MESSAGE)
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=self.TIMEOUT_MS))

    def start_chat(self, system_prompt: str):
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0,  # Same Output across Runs
        )
        return self._client.chats.create(model=self.MODEL, config=config)

    # A Failed Call is Not Saved in the Chat History, so Retrying Does Not Affect the Conversation
    def send_chat_message(self, chat, message: str) -> str:
        attempt = 1
        while True:
            try:
                return chat.send_message(message).text

            # Busy or Rate Limited: Wait Longer Each Time and Try Again
            except errors.APIError as error:
                if error.code in self.RETRY_CODES and attempt < self.MAX_ATTEMPTS:
                    time.sleep(self.WAIT_SECONDS * attempt)
                    attempt += 1
                    continue
                raise AIServiceError(error.message, error.code, error.status)

            # No Internet, Timeout, or Any Other Problem
            except Exception as error:
                raise AIServiceError(f"Could not reach the AI: {error}")

    # Uses a Short-Lived Chat so it Shares the Same Retry and Error Handling as Chat Messages
    def generate_json(self, prompt: str, schema: dict) -> str:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        )
        one_off_chat = self._client.chats.create(model=self.MODEL, config=config)
        return self.send_chat_message(one_off_chat, prompt)

# ----------- #
# AI Analysis
# ----------- #

# Separate One-Off Request for the AI's Own Analysis
# (Used when the Chat Finished the Worker's Details but Left the Analysis Empty or Invalid)
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

    # Shape Gemini Must Follow (Forces the Allowed Values and Real true/false)
    SCHEMA = {
        "type": "OBJECT",
        "properties": {
            "detected_language": {"type": "STRING"},
            "ai_severity": {"type": "STRING", "enum": SEVERITY_LEVELS},
            "is_near_miss": {"type": "BOOLEAN"},
            "root_cause_category": {"type": "STRING", "enum": ROOT_CAUSES},
            "lost_time_injury": {"type": "BOOLEAN"},
            "safety_recommendation": {"type": "STRING"},
        },
        "required": [
            "detected_language", "ai_severity", "is_near_miss",
            "root_cause_category", "lost_time_injury", "safety_recommendation",
        ],
    }

    def __init__(self, service: AIService, worker_fields: FieldSet, analysis_fields: FieldSet):
        self._service = service
        self._worker_fields = worker_fields
        self._analysis_fields = analysis_fields

    # Returns the Analysis Fields as a Dict, or None if the AI Could Not Give a Valid Analysis
    def run(self, report: dict, worker_messages: list):
        worker_details = {name: report.get(name) for name in self._worker_fields.names()}
        prompt = self.PROMPT.format(
            report=json.dumps(worker_details, indent=2, ensure_ascii=False),
            messages="\n".join([f"- {text}" for text in worker_messages]) or "- (not available)",
            fields=self._analysis_fields.describe(),
        )
        for _ in range(self.MAX_ATTEMPTS):
            try:
                reply_text = self._service.generate_json(prompt, self.SCHEMA)
            except AIServiceError:
                return None
            analysis = self._parse(reply_text)
            if analysis is not None:
                return analysis
        return None

    # Turn the Reply into a Dict of the Analysis Fields (None if it is Not JSON or Any Field is Not Valid)
    def _parse(self, text: str):
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

# --------------- #
# Incident Report
# --------------- #

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
    def _parse(self, text: str):
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
    def _build_fix_message(self, invalid_fields: list) -> str:
        details = "; ".join([f"{field.name} ({field.description})" for field in invalid_fields])
        return (
            "Not complete yet. These details are missing or not in the required format. "
            "Correct them from what the worker already said if you can, otherwise set "
            f"is_complete to false and ask the worker for: {details}. If the worker already said "
            f"twice that they do not know one of these, store \"{UNKNOWN_VALUE}\" for it instead "
            "(the incident date must still be a real date). Keep your reply to the worker in their language."
        )

# --------------- #
# AI Manager Main
# --------------- #

# Class that Creates a New IncidentConversation for Each Worker, and Holds the AIService and Field Definitions
class AIManager:
    def __init__(self, service: AIService):
        self._service = service

        # Details the AI Collects from the Worker
        self._worker_fields = FieldSet([
            TextField("reporter_name", "full name of the person reporting"),
            TextField("location", "site and exact area where it happened"),
            DateField("incident_date", "date in YYYY-MM-DD"),
            TimeField("incident_time", "time in 24h HH:MM", allows_unknown=True),
            TextField("description", "what happened, in clear English"),
            TextField("injury_status", "who was hurt and how, or 'no injury'"),
            BooleanField("hospitalised", "true if the injured person was sent to hospital, otherwise false"),
            TextField("immediate_action_taken", "what was done straight after"),
            NumberField("work_stoppage_hours", "hours work was stopped, 0 if none", allows_unknown=True),
        ])

        # Details the AI Works Out Itself once the Report is Complete
        self._analysis_fields = FieldSet([
            TextField("detected_language", "language(s) the worker wrote in"),
            ChoiceField("ai_severity", SEVERITY_LEVELS),
            BooleanField("is_near_miss", "true if nobody was hurt and nothing was damaged"),
            ChoiceField("root_cause_category", ROOT_CAUSES),
            BooleanField("lost_time_injury", "true if the injured person cannot work their next shift"),
            TextField("safety_recommendation", "practical actions the safety officer should take"),
        ])

        self._analysis_task = AnalysisTask(service, self._worker_fields, self._analysis_fields)

    # Start a New Report Conversation
    def start_conversation(self) -> IncidentConversation:
        return IncidentConversation(self._service, self._worker_fields, self._analysis_fields, self._analysis_task)