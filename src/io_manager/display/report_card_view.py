from datetime import date, datetime  # Checks Whether a MOM Deadline has Passed

from src.io_manager.constants import (
    BOLD,
    FULL_REPORT_FIELDS,
    GREEN,
    RED,
    RESET,
    UNDERLINE,
    YELLOW,
    YES_NO_COLUMNS,
)


#Prints One Report in Full: a Report Opened from the Table, or the Card a Worker Sees After Saving
class ReportCardView:
    def __init__(self, formatter):
        self._formatter = formatter   # The shared ReportFormatter, handed in (association)

    # Print every field of one report under a title (long text is wrapped, empty fields skipped)
    def show(self, report: dict, title: str) -> None:
        print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")
        for label, column in FULL_REPORT_FIELDS:
            value = report.get(column, "-")
            if column in YES_NO_COLUMNS:
                value = self._formatter.yes_no(value)
            for line in self._formatter.wrap_detail(label, value):
                print(line)
        print()

    # Open report number N from a table (table numbers start at 1, rows start at 0)
    def show_from_table(self, table, number: int) -> None:
        report = table.iloc[number - 1].fillna("-").to_dict()
        self.show(report, f"Report #{number}")

    # Tell the worker whether their report was really saved; if it was, show it back as a card
    # with the score and MOM details the Logic Manager added (outcome is a SaveOutcome object)
    def show_save_outcome(self, report: dict, outcome) -> None:
        # Only claim success when the Data Manager actually wrote the record
        if not outcome.saved:
            print(f"\n{RED}{BOLD} Your report was NOT saved.{RESET} {outcome.message}")
            print(f"{YELLOW}Please tell your supervisor about this incident directly.{RESET}\n")
            return

        print(f"\n{GREEN}{BOLD} Your report has been saved.{RESET}")

        # The card shows what was saved: the worker's details plus the Logic Manager's results
        card = dict(report)
        for column in ("importance_score", "mom_reportable", "deadline"):
            card[column] = getattr(outcome, column)
        self.show(card, "Your Saved Report")

        # A MOM-reportable incident has a legal deadline, so make it stand out
        if outcome.mom_reportable == "Yes":
            if self._is_overdue(outcome.deadline):
                print(f"{RED}{BOLD}  OVERDUE: this incident had to be reported to MOM by {outcome.deadline}. "
                      f"Tell your supervisor now.{RESET}\n")
            else:
                print(f"{RED}{BOLD}  This incident must be reported to MOM by {outcome.deadline}.{RESET}\n")

    # Check whether a MOM deadline has already passed (a deadline of today is not overdue yet)
    def _is_overdue(self, deadline, today=None) -> bool:
        try:
            due = datetime.strptime(str(deadline), "%Y-%m-%d").date()
        except ValueError:
            return False  # e.g. "Check incident date": no real date to compare
        return due < (today or date.today())