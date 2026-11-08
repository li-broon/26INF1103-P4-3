# ------- #
# Imports
# ------- #

import contextlib
import re
from io import StringIO


# Runs Something that Prints, and Returns What it Printed with the Colour Codes Removed
class PrintCapture:
    COLOUR_CODES = r"\x1b\[[0-9;]*m"

    def text_of(self, action, *arguments) -> str:
        with contextlib.redirect_stdout(StringIO()) as output:
            action(*arguments)
        return re.sub(self.COLOUR_CODES, "", output.getvalue())
