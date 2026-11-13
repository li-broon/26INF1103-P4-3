from src.io_manager.constants import (
    BOLD, CYAN, FULL_REPORT_FIELDS, GREEN, RED, RESET, SPEAKER_DISPLAY_NAMES, UNDERLINE, YELLOW, YES_NO_COLUMNS,
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

    # Print a report's conversation exactly as the worker and the AI wrote it, untranslated (text=None means none was saved)
    def show_transcript(self, text, title: str) -> None:
        print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")
        if not text:
            print(f"{YELLOW}No transcript is saved for this report.{RESET}\n")
            return
        for speaker, message in self._formatter.transcript_turns(text):
            print(f"{CYAN}{BOLD}{SPEAKER_DISPLAY_NAMES.get(speaker, speaker)}:{RESET} {message}")
        print()

    # Tells the worker whether the report was really saved; if so, shows it back as a card with the score and MOM details (outcome is a SaveOutcome)
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
            if self._formatter.is_overdue(outcome.deadline):
                print(f"{RED}{BOLD}  OVERDUE: this incident had to be reported to MOM by {outcome.deadline}. "
                      f"Tell your supervisor now.{RESET}\n")
            else:
                print(f"{RED}{BOLD}  This incident must be reported to MOM by {outcome.deadline}.{RESET}\n")