# -------- #
# Import(s)
# -------- #
from types import SimpleNamespace

import src.data_manager as data_manager
from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.io_manager import IOManager
from src.logic_manager import logic


# TEMPORARY (task 18 replaces this): until Akira's LogicManager is merged, wrap the old
# logic() function so it has the process() method IOManager calls
class OldLogicAdapter:
    def process(self, report):
        return SimpleNamespace(**logic(report))


# TEMPORARY (task 18 replaces this): GeminiService checks the API key as soon as it is
# created, so without a key the app could not even show the menu. This stand-in only
# reports the missing key when the chatbot is opened, so viewing reports still works
class NoKeyAI:
    def __init__(self, error):
        self._error = error

    def start_conversation(self):
        raise self._error


# --------- #
# Start App
# --------- #
# Create every manager once and hand them to the IO Manager (UML Figure 1)
def main():
    try:
        ai_manager = AIManager(GeminiService())
    except AIServiceError as error:
        ai_manager = NoKeyAI(error)
    IOManager(ai_manager, OldLogicAdapter(), data_manager).run()


if __name__ == "__main__":
    main()