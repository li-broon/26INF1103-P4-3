# ------- #
# Imports
# ------- #

import json
import os
import time
from datetime import datetime
from google import genai
from google.genai import errors, types

#----------------------- #
# Gemini AI Configuration
#----------------------- #

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Details the AI Collect from User
USER_FIELDS = {
    "reporter_name": "full name of the person reporting",
    "location": "site and exact area where it happened",
    "incident_date": "date in YYYY-MM-DD",
    "incident_time": "time in 24h HH:MM",
    "description": "what happened, in clear English",
    "injury_status": "who was hurt and how, or 'no injury'",
    "hospitalised": "true if the injured person was sent to hospital, otherwise false",
    "immediate_action_taken": "what was done straight after",
    "work_stoppage_hours": "hours work was stopped, 0 if none",
}

# Allowed Values for the AI's Severity and Root Cause (Must Match the Weights in 'logic_manager')
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]
ROOT_CAUSES = [
    "Electrical", "Chemical", "Fall from Height", "Struck by Object", "Machinery",
    "Slip or Trip", "Fire", "Water", "Safety Procedure Breach", "Other",
]

# Details the AI Creates once Report is Complete
AI_FIELDS = {
    "detected_language": "language(s) the worker wrote in",
    "ai_severity": "one of " + ", ".join(SEVERITY_LEVELS),
    "is_near_miss": "true if nobody was hurt and nothing was damaged",
    "root_cause_category": "one of " + ", ".join(ROOT_CAUSES),
    "lost_time_injury": "true if the injured person cannot work their next shift",
    "safety_recommendation": "practical actions the safety officer should take",
}

# Value the AI Stores when the Worker Really Does Not Know a Detail (Counts as Filled)
UNKNOWN_VALUE = "unknown (worker could not say)"

# Gemini Prompt Template
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
{user_fields}

When ALL details above are filled, set "is_complete" to true, thank the
worker, and in that SAME reply fill in every one of these analysis fields.
They are your own judgement of the incident, so never ask the worker for
them and never leave them null:
{ai_fields}
Until then, keep "is_complete" false and leave the analysis fields null.

Respond ONLY with JSON in this exact format:
{{
  "reply": "your message to the worker, in their language",
  "is_complete": false,
  "report": {{ every field listed above as a key }}
}}
"""

# Prompt for the Separate Analysis Request (Used when the Chat Finished the Report but Left the Analysis Empty)
ANALYSIS_PROMPT = """\
You are a workplace safety analyst. A worker has finished reporting an
incident. Using the report and the worker's own messages below, give your
own judgement of the incident. Write in English, except "detected_language",
which names the language(s) the worker wrote in.

Incident report:
{report}

Worker's messages:
{messages}

Fields to return:
{ai_fields}

Respond ONLY with a JSON object containing exactly these fields.
"""

# Shape Gemini Must Follow for the Analysis (Forces the Allowed Values and Real true/false)
ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "detected_language": {"type": "STRING"},
        "ai_severity": {"type": "STRING", "enum": SEVERITY_LEVELS},
        "is_near_miss": {"type": "BOOLEAN"},
        "root_cause_category": {"type": "STRING", "enum": ROOT_CAUSES},
        "lost_time_injury": {"type": "BOOLEAN"},
        "safety_recommendation": {"type": "STRING"},
    },
    "required": list(AI_FIELDS),
}

# How many Times to Ask AI to Fix a Invalid JSON Reply
MAX_JSON_RETRIES = 2

# How many Times to Try when Gemini is Busy (503), and Seconds to Wait between Tries (waits 3s, 6s, 9s, 12s)
MAX_BUSY_ATTEMPTS = 5
BUSY_WAIT_SECONDS = 3

# How many Times to Tell the AI to Fix a Report it Marked Complete while Fields are Missing
MAX_FIX_ATTEMPTS = 2

# Error Messages
MISSING_KEY_MESSAGE = """\
GEMINI_API_KEY is missing.
Create a file called '.env' in the project folder containing:
    GEMINI_API_KEY=your-key
Then run the program again. With Docker, pass the file in:
    docker run -it --rm --env-file .env -v "$(pwd)/data:/app/data" inf1103-p4"""

BAD_JSON_MESSAGE = (
    "Your last reply was not valid JSON in the required format. "
    "Send the same reply again using ONLY the JSON format with the "
    "keys \"reply\", \"is_complete\" and \"report\"."
)

INCOMPLETE_MESSAGE = (
    "The report is not finished yet. Still missing: {fields}. "
    "Please give these details (or say you do not know) in your next message."
)

ANALYSIS_FAILED_MESSAGE = (
    "All your details are recorded, but the AI could not finish analysing the incident. "
    "Please send any message (for example 'ok') to try again."
)

# Start of the Messages this File Sends to the AI Itself (Left Out when Collecting the Worker's Own Messages)
OWN_MESSAGE_STARTS = ("Not complete yet.", "You set is_complete", BAD_JSON_MESSAGE)

# ---------------------------- #
# ai_manager Private Functions
# ---------------------------- # 

# Create Single Gemini Client for Whole App (so we don't have to re-authenticate every time)
_client = None
def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

# Format Fields for the AI Prompt (e.g. "- name: meaning")
def _format_fields(fields):
    return "\n".join(f"- {name}: {meaning}" for name, meaning in fields.items())

# Build Error Reply Dict (same shape as a normal reply, plus "error")
def _error_result(message):
    return {"reply": "", "is_complete": False, "report": {}, "error": message}

# Turn AI Reply Text into a Dict (Returns None if it is not in our JSON format)
def _parse_reply(text):
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):  # TypeError: AI reply was empty
        return None
    if not isinstance(data, dict) or not isinstance(data.get("report"), dict):
        return None
    if "reply" not in data or "is_complete" not in data:
        return None
    return data

# Run a Gemini Call, Waiting and Trying Again while it is Busy (503)
def _call_with_busy_retry(call):
    attempt = 1
    while True:
        try:
            return call()
        except errors.APIError as error:

            # Not a busy error, or out of tries (the caller handles all other errors)
            if error.code != 503 or attempt >= MAX_BUSY_ATTEMPTS:
                raise
            time.sleep(BUSY_WAIT_SECONDS * attempt)
            attempt += 1

# Send Message to Gemini Chat with Busy Retries (A failed call is not saved in the chat history, so the conversation is not affected)
def _send_with_retry(chat, message):
    return _call_with_busy_retry(lambda: chat.send_message(message))

# Send One Message to AI and Return JSON Reply as a Dict (If the reply is bad JSON, push it back to the AI to fix, up to MAX_JSON_RETRIES times)
def _ask_ai(chat, text):
    message = text
    for _ in range(1 + MAX_JSON_RETRIES):
        try:
            response = _send_with_retry(chat, message)

        # If API Replied with an Error, Return its Code and Status
        except errors.APIError as error:
            result = _error_result(error.message)
            result["error_code"] = error.code
            result["error_status"] = error.status
            return result

        # Ensure it Never Crash on Any Other Problem (e.g. no internet, no code/status)
        except Exception as error:
            return _error_result(f"Could not reach the AI: {error}")

        result = _parse_reply(response.text)
        if result is not None:
            return result
        message = BAD_JSON_MESSAGE

    return _error_result("The AI kept replying in the wrong format.")

# Build the Message Telling the AI What to Fix when it Says "Complete" but Fields are Missing
def _build_fix_message(missing):
    missing_user = [name for name in missing if name in USER_FIELDS]
    missing_ai = [name for name in missing if name in AI_FIELDS]

    # User Details Missing, AI asks the User (or stores UNKNOWN_VALUE if they already said they don't know)
    if missing_user:
        fix = (
            "Not complete yet. Set is_complete to false and ask the worker for: "
            + ", ".join(missing_user) + ". If the worker already said twice that "
            f"they do not know one of these, store \"{UNKNOWN_VALUE}\" for it instead."
        )

    # Only Analysis Missing, AI Fills it in Itself.
    else:
        fix = (
            "You set is_complete to true but left your analysis fields empty. "
            "Fill these in yourself now and keep is_complete true: " + ", ".join(missing_ai) + "."
        )
    return fix + " Keep your reply to the worker in their language."

# Check One AI Analysis Value is Usable (Allowed Severity/Root Cause, Real true/false, Non-Empty Text)
def _is_valid_ai_value(name, value):
    if name == "ai_severity":
        return value in SEVERITY_LEVELS
    if name == "root_cause_category":
        return value in ROOT_CAUSES
    if name in ("is_near_miss", "lost_time_injury"):
        return isinstance(value, bool)
    return isinstance(value, str) and value.strip() != ""

# List the AI Analysis Fields that are Missing or Not Valid
def _invalid_ai_fields(report):
    return [name for name in AI_FIELDS if not _is_valid_ai_value(name, report.get(name))]

# Turn the Analysis Reply into a Dict of the AI Fields (Returns None if Anything is Missing or Not Valid)
def _parse_analysis(text):
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    analysis = {name: data.get(name) for name in AI_FIELDS}
    if _invalid_ai_fields(analysis):
        return None
    return analysis

# Get What the Worker Typed in this Chat (So the Analysis can Tell which Language they Used)
def _worker_messages(chat):
    try:
        history = chat.get_history()
    except Exception:
        return []
    messages = []
    for content in history:
        if content.role != "user":
            continue
        for part in content.parts or []:
            if part.text and not part.text.startswith(OWN_MESSAGE_STARTS):
                messages.append(part.text)
    return messages

# Ask Gemini for Only the Analysis Fields, in a Separate Request Outside the Chat (Returns None if it Fails)
def _request_analysis(chat, report):
    prompt = ANALYSIS_PROMPT.format(
        report=json.dumps({name: report.get(name) for name in USER_FIELDS}, indent=2, ensure_ascii=False),
        messages="\n".join(f"- {text}" for text in _worker_messages(chat)) or "- (not available)",
        ai_fields=_format_fields(AI_FIELDS),
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ANALYSIS_SCHEMA,
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # No tools used, also stops a library warning printing in the chat
    )
    for _ in range(1 + MAX_JSON_RETRIES):
        try:
            response = _call_with_busy_retry(
                lambda: _get_client().models.generate_content(model=GEMINI_MODEL, contents=prompt, config=config)
            )
        except Exception:  # API error or no connection: send_message tells the user to try again
            return None
        analysis = _parse_analysis(response.text)
        if analysis is not None:
            return analysis
    return None

# ------------------------- #
# ai_manager Main Functions
# ------------------------- # 

# Check API Key is Set (Call this before start_chat, it will fail without a key)
def check_api_key():
    if not GEMINI_API_KEY:
        return MISSING_KEY_MESSAGE
    return None

# Start a New Conversation. Returns Gemini Chat Session.
def start_chat():
    prompt = SYSTEM_PROMPT.format(
        today=datetime.now().strftime("%Y-%m-%d"),
        unknown=UNKNOWN_VALUE,
        user_fields=_format_fields(USER_FIELDS),
        ai_fields=_format_fields(AI_FIELDS),
    )
    config = types.GenerateContentConfig(
        system_instruction=prompt,
        response_mime_type="application/json",
        temperature=0,  # Same Output across Runs
    )
    return _get_client().chats.create(model=GEMINI_MODEL, config=config)

# Check for Missing Fields in Report
def find_missing_fields(report):
    all_fields = list(USER_FIELDS) + list(AI_FIELDS)
    return [name for name in all_fields if report.get(name) in (None, "")]

# Send User Message to AI and Return AI Reply Dict
def send_message(chat, user_text):
    result = _ask_ai(chat, user_text)

    # AI says "complete" but Worker Details are Missing: tell it to ask the worker, up to MAX_FIX_ATTEMPTS times
    for _ in range(MAX_FIX_ATTEMPTS):
        missing_user = [name for name in find_missing_fields(result.get("report", {})) if name in USER_FIELDS]
        if not (result.get("is_complete") and missing_user):
            break
        result = _ask_ai(chat, _build_fix_message(missing_user))

    # Still Collecting Details (or an Error): show the AI's reply as normal
    if not result.get("is_complete"):
        return result

    # AI still says "complete" with worker details missing: don't show its "all done" reply, tell the user what is missing
    report = result["report"]
    missing_user = [name for name in find_missing_fields(report) if name in USER_FIELDS]
    if missing_user:
        return _error_result(INCOMPLETE_MESSAGE.format(fields=", ".join(missing_user).replace("_", " ")))

    # Worker Details Done, but the Analysis is Empty or Not Valid: ask for it in a separate request
    # (Asking again inside the chat tends to repeat the same empty fields)
    if _invalid_ai_fields(report):
        analysis = _request_analysis(chat, report)
        if analysis is None:
            return _error_result(ANALYSIS_FAILED_MESSAGE)
        report.update(analysis)

    return result
