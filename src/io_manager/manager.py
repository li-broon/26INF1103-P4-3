from src.ai_manager import AIServiceError
from src.io_manager.constants import (
    BOLD, FILTER_BACK_OPTION, FILTER_COLUMNS, GOODBYE, GREEN, RED, RESET, TRANSCRIPT_COLUMN, WELCOME, YELLOW,
)
from src.io_manager.display.pager import Pager
from src.io_manager.display.report_card_view import ReportCardView
from src.io_manager.display.report_formatter import ReportFormatter
from src.io_manager.display.report_table_view import ReportTableView
from src.io_manager.menus.filter_menu import FilterMenu
from src.io_manager.menus.main_menu import MainMenu
from src.io_manager.menus.page_menu import PageMenu
from src.io_manager.menus.view_menu import ViewMenu
from src.io_manager.prompts.prompter import Prompter


#User interface manager, handling all input and output, prompts, menu, pager
class IOManager:
    def __init__(self, ai_manager, logic_manager, data_manager, chart_manager, read=input, ):
        #handed in by main() and used, but not created or ownned by here (association)
        self._ai_manager = ai_manager
        self._logic_manager = logic_manager
        self._data_manager = data_manager 
        self._chart_manager = chart_manager

        #create her and owned by this IOManager (Composition)
        self._prompter = Prompter(read)
        self._formatter = ReportFormatter()
        self._table_view = ReportTableView(self._formatter)
        self._card_view = ReportCardView(self._formatter)
        self._menus = {"main" : MainMenu(self._prompter),
                       "view" : ViewMenu(self._prompter),
                       "page": PageMenu(self._prompter),
                       "filter": FilterMenu(self._prompter),}

    def _turn_page(self, pager, forward: bool) -> bool:
        moved = pager.next() if forward else pager.previous()
        if not moved:
            end = "last" if forward else "first"
            print(f"{YELLOW}You are already on the {end} page.{RESET}")
        return moved

    #page through a filtered table: next, previous, open a report, or go back
    def _browse_pages(self, table, title: str) -> None:
        pager = Pager(len(table))
        show_page = True

        while True:
            if show_page:
                self._table_view.show(table, title, pager)

            choice = self._menus["page"].show()
            if choice == 1:
                show_page = self._turn_page(pager, forward=True)
            elif choice == 2:
                show_page = self._turn_page(pager, forward=False)
            elif choice == 3:
                number = self._prompter.ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
                self._card_view.show_from_table(table, number)
                # Keep the full report on screen instead of printing the table over it
                show_page = False
            elif choice == 4:
                self._show_transcript(table)
                show_page = False
            else:
                return

        # Show every saved report, most urgent first, with paging, filtering and full-report options
    def _view_reports(self) -> None:
        table = self._data_manager.load_records()

        # Nothing saved yet: say so instead of showing an empty table
        if table.empty:
            print(f"{YELLOW}No incident reports have been saved yet.{RESET}")
            return

        title = f"Saved Incident Reports ({len(table)} total, most urgent first)"
        pager = Pager(len(table))
        show_page = True

        while True:
            # Only print the table if the page has changed or it's the first display
            if show_page:
                self._table_view.show(table, title, pager)

            choice = self._menus["view"].show()
            if choice == 1:
                show_page = self._turn_page(pager, forward=True)
            elif choice == 2:
                show_page = self._turn_page(pager, forward=False)
            elif choice == 3:
                self._filter_reports()
                # Don't reprint the full table straight after the filtered results
                show_page = False
            elif choice == 4:
                number = self._prompter.ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
                self._card_view.show_from_table(table, number)
                # Keep the full report on screen instead of printing the table over it
                show_page = False
            elif choice == 5:
                self._show_transcript(table)
                show_page = False
            else:
                return

    # Ask which report, then print the worker's conversation for it exactly as typed (untranslated)
    def _show_transcript(self, table) -> None:
        number = self._prompter.ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
        transcript_id = table.iloc[number - 1].to_dict().get(TRANSCRIPT_COLUMN)
        text = self._data_manager.load_transcript(transcript_id)
        self._card_view.show_transcript(text, f"Conversation for Report #{number}")

    #Ask which column and value to filter by, then page through the matching reports
    def _filter_reports(self) -> None:
        choice = self._menus["filter"].show()
        if choice == FILTER_BACK_OPTION:
            return

        heading, column = FILTER_COLUMNS[choice - 1]

        #Location is a free-text keyword search so users don't pick from a huge list (task 16 replaces this check once KeywordFilter offers no options)
        if column in ["location"]:
            value = self._prompter.ask_text(f"\n{BOLD}Enter a keyword to search in {heading}:{RESET} ")
        else:
            value = self._prompter.choose_from(f"Values saved under {heading}", self._data_manager.get_unique_values(column))
        if not value:
            return

        matches = self._data_manager.load_matching_records(column, value)
        if matches.empty:
            print(f"{YELLOW}No reports found where {heading} is '{value}'.{RESET}")
            return

        self._browse_pages(matches, f"Reports where {heading} matches '{value}' ({len(matches)} found, most urgent first)")


    #Chat with the worker until the AI has a complete report, then score it, save it and show the result
    def _run_chatbot(self) -> None:
        # Start the conversation (fails here if the API key is missing)
        try:
            conversation = self._ai_manager.start_conversation()
        except AIServiceError as error:
            print(f"{RED}{error.message}{RESET}")
            return

        print(WELCOME)

        while True:
            user_text = self._prompter.ask_text("> ")

            # Reject blank input and ask again, instead of spending an API call on nothing
            if user_text == "":
                print(f"{YELLOW}Please type something, or 'quit' to go back to the menu.{RESET}")
                continue

            # Let the worker leave without finishing, after checking they meant it
            if self._prompter.is_cancel(user_text):
                if self._prompter.ask_yes_no("Leave without finishing this report?"):
                    print(f"{YELLOW}Report cancelled. Nothing was saved.{RESET}\n")
                    return
                continue

            # Let the worker know the AI is working, since a reply can take a few seconds
            print("Thinking...\n")
            result = conversation.send(user_text)

            if result.error:
                self._show_ai_error(result)
                continue

            # Print the AI's reply, in the worker's own language
            print(result.reply)

            # All required fields collected: the Logic Manager scores and saves it
            if result.is_complete:
                outcome = self._logic_manager.process(result.report)
                self._card_view.show_save_outcome(result.report, outcome)

                # Keep the conversation next to the saved report (the report is already safe if only this part fails)
                if outcome.saved:
                    transcript = conversation.transcript
                    saved, message = self._data_manager.save_transcript(transcript.transcript_id, transcript.as_text())
                    if not saved:
                        print(f"{YELLOW}{message}{RESET}")

                if self._prompter.ask_yes_no("Would you like to view all saved reports now?"):
                    self._view_reports()
                return

    #Show an AI error, with advice that fits the kind of error
    def _show_ai_error(self, result) -> None:
        print(f"{RED}{BOLD}  Error Occurred:{RESET}")

        # A real API error (it has a code, e.g. a rate limit): sending again can work
        if result.error_code is not None:
            print(f"   {BOLD}{RED}Code:{RESET}    {result.error_code}")
            print(f"   {BOLD}{RED}Status:{RESET}  {result.error_status}")
            print(f"   {BOLD}{RED}Message:{RESET} {result.error}")
            print(f"{BOLD}{RED}Please resend your last message to try again!{RESET}\n")

        # Any other problem (no code): sending the same message again won't help
        else:
            print(f"   {BOLD}{RED}Message:{RESET} {result.error}")
            print(f"{YELLOW}This report couldn't be finished. Type 'quit' to go back, or tell your supervisor directly.{RESET}\n")

    #Options 3 so the user can pick the chart option
    def _show_charts(self) -> None:
        options = self._chart_manager.get_chart_options() + [("all", "All charts on one page")]
        labels = [label for key, label in options]

        label = self._prompter.choose_from("Charts", labels)
        if label is None:
            return
        key = options[labels.index(label)][0]

        if self._prompter.ask_yes_no("Open the chart in a window? (n saves it as a picture in the data folder)"):
            saved, message = self._chart_manager.show_chart(key)
        else:
            saved, message = self._chart_manager.show_chart(key, save_path=f"data/chart_{key}.png")

        print(f"{GREEN if saved else YELLOW}{message}{RESET}")

    #Start the app: show the main menu until the user exits (Ctrl+C also exits cleanly)
    def run(self) -> None:
        try:
            while True:
                choice = self._menus["main"].show()
                if choice == 1:
                    self._run_chatbot()
                elif choice == 2:
                    self._view_reports()
                elif choice == 3:
                    self._show_charts()
                else:
                    print(GOODBYE)
                    return
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GOODBYE}")