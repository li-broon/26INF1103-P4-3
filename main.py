# -------- #
# Import(s)
# -------- #

import sys

# --------- #
# Start App
# --------- #
# "python main.py" Runs the Terminal App, "python main.py --gui" Opens the Tkinter Window
if __name__ == "__main__":
    if "--gui" in sys.argv:
        from src.gui_manager import main
    else:
        from src.io_manager import main
    main()
