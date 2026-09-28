# ------- #
# Imports
# ------- #
import json
import os
from datetime import datetime
from google import genai
from google.genai import types

#----------------------- #
# Gemini AI Configuration
#----------------------- #

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.8-flash"

# Details the AI Collect from User
USER_FIELDS = {
    "reporter_name": "full name of the person reporting",
    "reporter_role": "job title or trade, e.g. electrician",
    "location": "site and exact area where it happened",
    "incident_date": "date in YYYY-MM-DD",
    "incident_time": "time in 24h HH:MM",
    "description": "what happened, in clear English",
    "injury_status": "who was hurt and how, or 'no injury'",
    "body_part_injured": "body part(s) injured, or 'none'",
    "hospitalised": "true or false",
    "ppe_worn": "safety equipment worn at the time, or 'none'",
    "witnesses": "names of witnesses, or 'none'",
    "immediate_action_taken": "what was done straight after",
    "work_stoppage_hours": "hours work was stopped, 0 if none",
    "urgency_rating": "worker's own urgency rating, whole number 1-10",
}

# Details the AI Creates once Report is Complete
AI_FIELDS = {
    "detected_language": "language(s) the worker wrote in",
    "ai_severity": "one of Low, Medium, High, Critical",
    "is_near_miss": "true if nobody was hurt and nothing was damaged",
    "root_cause_category": "one of Electrical, Chemical, Fall from Height, Struck by Object, "
                           "Machinery, Slip or Trip, Fire, Water, Safety Procedure Breach, Other",
    "lost_time_injury": "true if the injured person cannot work their next shift",
    "safety_recommendation": "practical actions the safety officer should take",
}

# Gemini Prompt Template
SYSTEM_PROMPT = """\
You are a friendly workplace safety assistant helping a worker report an
incident. The worker may write in any language or a mix of languages.

Each turn:
- Always reply to the worker in the language they are using. Keep it short
  and simple, and ask for at most two missing details at a time.
- Keep track of every detail the worker has given so far. Store all values
  in English. Use null for anything not given yet. Never make things up.
- Work out relative dates like "yesterday" using today's date: {today}.
- If someone is still in danger, first tell them to call 995 and their supervisor.

Details to collect from the worker:
{user_fields}

When ALL details above are filled, set "is_complete" to true, thank the
worker, and also fill in your own analysis:
{ai_fields}
Until then, keep "is_complete" false and leave the analysis fields null.

Respond ONLY with JSON in this exact format:
{{
  "reply": "your message to the worker, in their language",
  "is_complete": false,
  "report": {{ every field listed above as a key }}
}}
"""

# How many Times to Ask AI to Fix a Invalid JSON Reply
MAX_JSON_RETRIES = 2

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

# Send One Message to AI and Return JSON Reply as a Dict (If the reply is bad JSON, push it back to the AI to fix, up to MAX_JSON_RETRIES times)
def _ask_ai(chat, text):
    message = text
    for _ in range(1 + MAX_JSON_RETRIES):
        try:
            response = chat.send_message(message)

        # Ensure it Never Crash on API/ Connection Problem
        except Exception as error:
            return _error_result(f"Could not reach the AI: {error}")

        result = _parse_reply(response.text)
        if result is not None:
            return result
        message = BAD_JSON_MESSAGE

    return _error_result("The AI kept replying in the wrong format.")

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

    # Double-check the AI (if it says it is done but fields are missing, tell it which ones so it asks the worker for them.)
    missing = find_missing_fields(result.get("report", {}))
    if result.get("is_complete") and missing:
        result = _ask_ai(chat, "Not complete yet. These fields are still missing: " + ", ".join(missing) + ". Set is_complete to false and ask the worker for them.")
        result["is_complete"] = False

    return result
