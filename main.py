# -------- #
# Import(s)
# -------- #
from types import SimpleNamespace

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.io_manager import IOManager
from src.logic_manager import logic
from src.data_manager import CsvRecordStore, DataManager, create_default_filters
from src.data_manager.constants import DATA_FILE

# TEMPORARY (task 18 replaces this): wraps the old logic() function so it has the process() method IOManager calls
class OldLogicAdapter:
    def process(self, report):
        return SimpleNamespace(**logic(report))

# TEMPORARY (task 18 replaces this): reports a missing API key only when the chatbot opens, so the menu and saved reports still work without one
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

    data_manager = DataManager(CsvRecordStore(DATA_FILE), create_default_filters())
    IOManager(ai_manager, OldLogicAdapter(), data_manager).run()


if __name__ == "__main__":
    main()