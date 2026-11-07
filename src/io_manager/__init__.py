# ------- #
# Imports
# ------- #
from types import (
    SimpleNamespace,  # Turns logic()'s dict into an object, until IOManager uses LogicManager
)

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.data_manager import (
    get_unique_values,
    load_matching_records,
    load_records,
)
from src.io_manager.constants import (
    ALERT_COLUMNS,
    BOLD,
    CYAN,
    DETAIL_FIELDS,
    DETAIL_INDENT,
    DETAIL_LABEL_WIDTH,
    DETAIL_TEXT_WIDTH,
    EMPTY_VALUES,
    FILTER_BACK_OPTION,
    FILTER_COLUMNS,
    FULL_REPORT_FIELDS,
    GOODBYE,
    GREEN,
    PAGE_SIZE,
    RED,
    RESET,
    TABLE_COLUMNS,
    UNDERLINE,
    WELCOME,
    YELLOW,
    YES_NO_COLUMNS,
)
from src.io_manager.display.pager import Pager
from src.io_manager.display.report_card_view import ReportCardView
from src.io_manager.display.report_formatter import ReportFormatter
from src.io_manager.display.report_table_view import ReportTableView
from src.io_manager.menus.filter_menu import FilterMenu
from src.io_manager.menus.main_menu import MainMenu
from src.io_manager.menus.menu import Menu
from src.io_manager.menus.page_menu import PageMenu
from src.io_manager.menus.view_menu import ViewMenu
from src.io_manager.prompts.prompter import Prompter
from src.logic_manager import logic

_prompter= Prompter()
_formatter= ReportFormatter()
_table_view = ReportTableView(_formatter)
_card_view = ReportCardView(_formatter)
# One Object per Menu, Sharing the One Prompter (Moves into the IOManager Class Later)
_main_menu = MainMenu(_prompter)
_view_menu = ViewMenu(_prompter)
_page_menu = PageMenu(_prompter) 
_filter_menu = FilterMenu(_prompter)

#Manage the pagination loop, allowing a user to scroll through a table
def browse_pages(table, title):
    pager = Pager(len(table))
    show_page = True

    # Keep the user in the page loop until they choose to exit
    while True:
        if show_page:
            _table_view.show(table, title, pager)

        choice = _page_menu.show()
        if choice == 1:
            show_page = pager.next()
            if not show_page:
                print(f"{YELLOW}You are already on the last page. {RESET}")
        elif choice == 2:
            show_page = pager.previous()
            if not show_page:
                print(f"{YELLOW}You are already on the first page. {RESET}")
        elif choice == 3:
            number = _prompter.ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
            _card_view.show_from_table(table, number)
            # Keep the full report on screen instead of printing the table over it
            show_page = False
        else:
            return

#Retrieve saved reports from the Data Manager and initiate the viewing sequence
def view_reports():
    table = load_records() # Load all saved data from the Data Manager

    #Handle the empty dataframe gracefully without crashing
    if table.empty:
        print(f"{YELLOW}No incident reports have been saved yet.{RESET}")
        return

    title = f"Saved Incident Reports ({len(table)} total, most urgent first)"
    pager = Pager(len(table))  # Tracks which page is showing
    show_page = True

    while True:
        #Only print the table if the page has changed or it's the first display
        if show_page:
            _table_view.show(table, title, pager)

        # Show sub-menu options for navigating pages or filtering reports
        choice = _view_menu.show()

        if choice == 1:
            show_page = pager.next()
            if not show_page:
                print(f"{YELLOW}You are already on the last page.{RESET}")
        elif choice == 2:
            show_page = pager.previous()
            if not show_page:
                print(f"{YELLOW}You are already on the first page.{RESET}")
        elif choice == 3:
            filter_reports()
            # Stop the main table from re-printing immediately after they finish viewing the filtered results
            show_page = False
        elif choice == 4:
            number = _prompter.ask_number(f"Which report number, out of all {len(table)} saved reports?: (1-{len(table)}):", 1, len(table))
            _card_view.show_from_table(table, number)
            # Keep the full report on screen instead of printing the table over it
            show_page = False
        else:
            break

#Prompt the user to filter the dataset by a specific column and value
def filter_reports():
    choice = _filter_menu.show()
    if choice == FILTER_BACK_OPTION:
        return
        
    #Extract the selected column and its UI heading to run the filter
    heading, column = FILTER_COLUMNS[choice - 1]

    #Open ended keyword search for location so users don't have to pick from a massive list
    if column in ["location"]:
        value = _prompter.ask_text(f"\n{BOLD}Enter a keyword to search in {heading}:{RESET} ")
        if not value:
            return
    else:
        #Display a list of unique values or threshold options for the selected column
        value = _prompter.choose_from(heading, get_unique_values(column))
        if value is None:
            return

    matches = load_matching_records(column, value)
    
    #Catch situations where the filter returned zero rows
    if matches.empty:
        print(f"{YELLOW}No reports found where {heading} is '{value}'.{RESET}")
        return

    #Pass the filtered subset into the pagination tool for viewing
    browse_pages(matches, f"Reports where {heading} matches '{value}' ({len(matches)} found, most urgent first)")

#Initialize the AI incident reporting chatbot, handle the conversation loop
def run_chatbot():
    #Set up Gemini before starting the chatbot (fails here if the API key is missing)
    try:
        conversation = AIManager(GeminiService()).start_conversation()
    except AIServiceError as error:
        print(f"{RED}{error.message}{RESET}")
        return

    print(WELCOME)

    while True:
        user_text = _prompter.ask_text("> ")
        #Reject blank input and ask again, instead of spending an API call on nothing
        if user_text == "":
            print(f"{YELLOW}Please type something, or 'quit' to go back to the menu.{RESET}")
            continue

            #let the workers leave without finishing 
        if _prompter.is_cancel(user_text):
            if _prompter.ask_yes_no("Leave without finishing this report?"):
                print(f"{YELLOW}Report cancelled. Nothing was saved.{RESET}\n")
                return
            continue

        #Let the worker know the AI is working, since a reply can take a few seconds
        print("Thinking...\n")
        result = conversation.send(user_text)

        # Something went wrong with this message: explain it, with advice that fits the kind of error
        if result.error:
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

        else:
            # Print the AI's translated response to the terminal
            print(result.reply)

            # If all required fields are collected, push the payload to the Logic Manager for scoring
            if result.is_complete:
                outcome = SimpleNamespace(**logic(result.report))
                _card_view.show_save_outcome(result.report, outcome)

                if _prompter.ask_yes_no("Would you like to view all saved reports now?"):
                    view_reports()
                break

# Display the main application loop. 
# Exits cleanly on Ctrl+C
def main():

    # The main application loop. Displays the main menu and routes user input to the core functions.
    try:
        while True:
            choice = _main_menu.show()  

            if choice == 1:
                run_chatbot()
            elif choice == 2:
                view_reports()
            else:
                print(GOODBYE)
                break

    except (KeyboardInterrupt, EOFError):
        print(f"\n{GOODBYE}")

