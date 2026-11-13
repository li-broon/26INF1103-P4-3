# -------- #
# Import(s)
# -------- #
import sys

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.data_manager import CsvRecordStore, DataManager, MomRecordStore, create_default_filters
from src.data_manager.charts.chart_manager import ChartManager
from src.data_manager.charts.default_charts import create_default_charts
from src.data_manager.constants import DATA_FILE, MOM_DATA_FILE
from src.io_manager import IOManager
from src.logic_manager import LogicManager


# TEMPORARY (task 18 replaces this): reports a missing API key only when the chatbot opens, so the menu and saved reports still work without one
class NoKeyAI:
    def __init__(self, error):
        self._error = error

    def start_conversation(self):
        raise self._error

# --------- #
# Start App
# --------- #

# Create every manager once and hand them to the IO Manager or GUI Manager (UML Figure 1)
def main():
    try:
        ai_manager = AIManager(GeminiService())

    except AIServiceError as error:
        ai_manager = NoKeyAI(error)

    data_manager = DataManager(CsvRecordStore(DATA_FILE), create_default_filters())

    # The MOM register only holds MOM reportable reports; reports saved before it existed are copied in once here
    mom_store = MomRecordStore(MOM_DATA_FILE)
    mom_store.sync(data_manager.load_records())

    logic_manager = LogicManager(data_manager, mom_store=mom_store)
    chart_manager = ChartManager(data_manager, create_default_charts())
    

    # "python main.py --gui" Opens the Tkinter Window, Otherwise the Terminal App Runs
    if "--gui" in sys.argv:
        
        # Imported Here so the Terminal App Still Runs on a Python Installed Without Tkinter
        from tkinter import TclError
        from src.gui_manager import GUIManager

        # No Screen Given to the Container (or No Display at All): Point to the README Instead of a Traceback
        try:
            GUIManager(ai_manager, logic_manager, data_manager, mom_store).mainloop()
        except TclError as error:
            print(f"Could not open the GUI window ({error}). See 'Running the GUI with Docker' in README.md.")
    else:
        IOManager(ai_manager, logic_manager, data_manager, chart_manager).run()

if __name__ == "__main__":
    main()
