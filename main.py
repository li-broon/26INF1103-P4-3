# -------- #
# Import(s)
# -------- #
import sys

from src.ai_manager import AIManager, GeminiService
from src.data_manager import CsvRecordStore, DataManager, MomRecordStore, TextTranscriptStore, create_default_filters
from src.data_manager.charts.chart_manager import ChartManager
from src.data_manager.charts.default_charts import create_default_charts
from src.data_manager.constants import DATA_FILE, MOM_DATA_FILE, TRANSCRIPT_FOLDER
from src.io_manager import IOManager
from src.logic_manager import LogicManager

# --------- #
# Start App
# --------- #

# Create every manager once and hand them to the IO Manager or GUI Manager (UML Figure 1).
# A missing API key is only reported when the chatbot opens, so the menu, saved reports and charts work without one
def main():
    ai_manager = AIManager(GeminiService())
    data_manager = DataManager(CsvRecordStore(DATA_FILE), create_default_filters(), TextTranscriptStore(TRANSCRIPT_FOLDER))
    mom_store = MomRecordStore(MOM_DATA_FILE)
    mom_store.sync(data_manager.load_records())  # Picks up MOM reportable reports saved before the register existed
    logic_manager = LogicManager(data_manager, mom_store=mom_store)  # New ones go into the register as they are saved
    chart_manager = ChartManager(data_manager, create_default_charts())

    # "python main.py --gui" Opens the Tkinter Window, Otherwise the Terminal App Runs
    if "--gui" in sys.argv:
        # Imported Here so the Terminal App Still Runs on a Python Installed Without Tkinter
        from tkinter import TclError
        from src.gui_manager import GUIManager

        # No Screen Given to the Container (or No Display at All): Point to the README Instead of a Traceback
        try:
            GUIManager(ai_manager, logic_manager, data_manager, chart_manager, mom_store).mainloop()
        except TclError as error:
            print(f"Could not open the GUI window ({error}). See 'Running the GUI with Docker' in README.md.")
    else:
        IOManager(ai_manager, logic_manager, data_manager, chart_manager).run()

if __name__ == "__main__":
    main()
