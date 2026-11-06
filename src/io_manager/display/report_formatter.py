import textwrap  # Wraps Long Sentences onto Several Lines so Nothing is Cut Off

from src.io_manager.constants import (
    ALERT_COLUMNS, BOLD, CYAN, DETAIL_FIELDS, DETAIL_INDENT, DETAIL_LABEL_WIDTH,
    DETAIL_TEXT_WIDTH, EMPTY_VALUES, RED, RESET, TABLE_COLUMNS,
)

class ReportFormatter:
    #The layout of the table does not change 
    def __init__(self,columns=TABLE_COLUMNS, details= DETAIL_FIELDS):
        self._columns = columns
        self._details = details

    #cut the text to an exact column and width 
    def fit_text(self, text, width)-> str:
        text = str(text)
        if len(text) >= width:
            text = text[:width - 2] + "…"
        return text.ljust(width)
    
    def wrap_detail(self, label, text) -> list:
        text= str(text).strip()
        if text.lower() in EMPTY_VALUES:
            return []
        indent = " " * DETAIL_INDENT
        label_cell = f"{label}:".ljust(DETAIL_LABEL_WIDTH)
        lines = textwrap.wrap(text, width=DETAIL_TEXT_WIDTH) or [text]

        # First Line Carries the Label, the Rest Line Up Underneath the Text
        wrapped = [f"{indent}{CYAN}{label_cell}{RESET}{lines[0]}"]
        wrapped += [f"{indent}{' ' * DETAIL_LABEL_WIDTH}{line}" for line in lines[1:]]
        return wrapped

    def yes_no(self,value)->str:
        text = str(value).strip().lower()
        if text in("true", "yes", "1", "1.0"):
            return "YES"
        if text in ("false", "no", "0", "0.0"):
            return "No"
        return "-"

    #build one summary row higlighting hospital and MOM cases in red 
    def build_row(self, number, report):
        row= self.fit_text(number, 5)
        for heading, data_column, width, in self._columns:
            value = report.get(data_column, "-")

            #Yes/No columns: YES is worht shouting about 
            if data_column in ALERT_COLUMNS:
                value=self.yes_no(value)
                cell = self.fit_text(value,width )
                row += f"{RED}{BOLD}{cell}{RESET}" if value == "YES" else cell
                continue

            if data_column == "deadline":
                cell =self.fit_text(value,width)
                must_report = self.yes_no(report.get("mom_reportable")) == "YES"
                row += f"{RED}{BOLD}{cell}{RESET}" if must_report else cell
                continue

            row += self.fit_text(value, width)
        return row