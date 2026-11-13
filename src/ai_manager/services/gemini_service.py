# ------- #
# Imports
# ------- #

import os
import time
from google import genai
from google.genai import errors, types
from src.ai_manager.services.ai_service import AIService
from src.ai_manager.services.ai_service_error import AIServiceError

# The Project's .env File (Three Folders Up from src/ai_manager/services/)
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")

# ----- #
# Class
# ----- #

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

    # Finds the Key Now (GEMINI_API_KEY if Set, Otherwise the .env File's, so the App also Runs Outside Docker) but Only Connects on
    # the First Request, so a Missing Key is Reported when the Chatbot Opens and the Rest of the App Still Works Without One
    def __init__(self, env_file: str = ENV_FILE):
        self._api_key = os.environ.get("GEMINI_API_KEY", "") or self._read_key(env_file)
        self._client = None

    # The Gemini Client, Made on First Use. Raises AIServiceError if There is No Key
    def _connect(self):
        if self._client is None:
            if not self._api_key:
                raise AIServiceError(self.MISSING_KEY_MESSAGE)
            self._client = genai.Client(api_key=self._api_key, http_options=types.HttpOptions(timeout=self.TIMEOUT_MS))
        return self._client

    # The GEMINI_API_KEY Value in the .env File, Without Quotes ("" if There is No File or No Key)
    def _read_key(self, env_file: str) -> str:
        if not os.path.exists(env_file):
            return ""
        with open(env_file, encoding="utf-8") as file:
            for line in file:
                name, _, value = line.partition("=")
                if name.strip() == "GEMINI_API_KEY":
                    return value.strip().strip('"').strip("'")
        return ""

    def start_chat(self, system_prompt: str):
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0,  # Same Output across Runs
        )
        return self._connect().chats.create(model=self.MODEL, config=config)

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
                # Some Error Replies have No Message, so Give One (Otherwise 'io_manager' would Treat it as Success)
                message = error.message or f"Gemini returned an error with no details (code {error.code})."
                raise AIServiceError(message, error.code, error.status)

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
        one_off_chat = self._connect().chats.create(model=self.MODEL, config=config)
        return self.send_chat_message(one_off_chat, prompt)