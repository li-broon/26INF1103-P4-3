# ------- #
# Imports
# ------- #
from datetime import date, datetime  # Checks Whether a MOM Deadline has Passed

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.data_manager import (
    get_unique_values,
    load_matching_records,
    load_records,
)
from src.io_manager.constants import (
    ALERT_COLUMNS,
    BOLD,
    CANCEL_WORDS,
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
from src.io_manager.display.report_formatter import ReportFormatter
from src.io_manager.menus.filter_menu import FilterMenu
from src.io_manager.menus.main_menu import MainMenu
from src.io_manager.menus.menu import Menu
from src.io_manager.menus.page_menu import PageMenu
from src.io_manager.menus.view_menu import ViewMenu
from src.io_manager.prompts.prompter import Prompter
from src.io_manager.display.report_table_view import ReportTableView
from src.logic_manager import logic

_prompter= Prompter()
_formatter= ReportFormatter()
_table_view = ReportTableView(_formatter)
# One Object per Menu, Sharing the One Prompter (Moves into the IOManager Class Later)
_main_menu = MainMenu(_prompter)
_view_menu = ViewMenu(_prompter)
_page_menu = PageMenu(_prompter) 
_filter_menu = FilterMenu(_prompter)

#Print every field of one report in full, so long names and locations are not cut off
def _print_full_report(table, number):
    # Subtract 1 because the table numbers start at 1, but rows start at 0
    report = table.iloc[number - 1].fillna("-").to_dict()
    _print_report_card(report, f"Report #{number}")

#Print every field of one report under a title.Used for a saved report opened from
#the table, and for the confirmation card the worker sees after submitting
def _print_report_card(report, title):
    print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")
    for label, column in FULL_REPORT_FIELDS:
        value = report.get(column, "-")
        if column in YES_NO_COLUMNS:
            value = _formatter.yes_no(value)
        for line in _formatter.wrap_detail(label, value):
            print(line)
    print()

#Tell the worker whether their report was really saved. If it was, show it back to them
#as a confirmation card, with the score and MOM details the Logic Manager added.
def _print_save_outcome(report, outcome):
    # Only claim success when the Data Manager actually wrote the record
    if not outcome["saved"]:
        print(f"\n{RED}{BOLD} Your report was NOT saved.{RESET} {outcome['message']}")
        print(f"{YELLOW}Please tell your supervisor about this incident directly.{RESET}\n")
        return

    print(f"\n{GREEN}{BOLD} Your report has been saved.{RESET}")

    #The card shows what was saved: the worker's details plus the Logic Manager's results
    card = dict(report)
    for column in ("importance_score", "mom_reportable", "deadline"):
        card[column] = outcome[column]
    _print_report_card(card, "Your Saved Report")

    # A MOM-reportable incident has a legal deadline, so make it stand out
    if outcome["mom_reportable"] == "Yes":
        if _is_overdue(outcome["deadline"]):
            print(f"{RED}{BOLD}  OVERDUE: this incident had to be reported to MOM by {outcome['deadline']}. "
                  f"Tell your supervisor now.{RESET}\n")
        else:
            print(f"{RED}{BOLD}  This incident must be reported to MOM by {outcome['deadline']}.{RESET}\n")

#Check whether a MOM deadline has already passed.A deadline of today is not overdue yet
def _is_overdue(deadline, today=None):
    try:
        due = datetime.strptime(str(deadline), "%Y-%m-%d").date()
    except ValueError:
        return False  # e.g. "Check incident date": no real date to compare
    return due < (today or date.today())

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
            _print_full_report(table, number)
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
            _print_full_report(table, number)
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
        value = input(f"\n{BOLD}Enter a keyword to search in {heading}:{RESET} ").strip()
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
        user_text = input("> ").strip()
        #Reject blank input and ask again, instead of spending an API call on nothing
        if user_text == "":
            print(f"{YELLOW}Please type something, or 'quit' to go back to the menu.{RESET}")
            continue

            #let the workers leave without finishing 
        if user_text.lower() in CANCEL_WORDS:
            if _prompter.ask_yes_no("Leave without finishing this report?"):
                print(f"{YELLOW}Report cancelled. Nothing was saved.{RESET}\n")
                return
            continue

        #Let the worker know the AI is working, since a reply can take a few seconds
        print("Thinking...\n")
        result = conversation.send(user_text)

        # Catch API errors (like rate limits etc.) and allow the user to try again without losing their spot
        if result.error:
            print(f"{RED}{BOLD}  Error Occurred:{RESET}")

            if result.error_code is not None:
                print(f"   {BOLD}{RED}Code:{RESET}    {result.error_code}")
                print(f"   {BOLD}{RED}Status:{RESET}  {result.error_status}")

            print(f"   {BOLD}{RED}Message:{RESET} {result.error}")
            print(f"{BOLD}{RED}Please resend your last message to try again!{RESET}\n")

        else:
            # Print the AI's translated response to the terminal
            print(result.reply)

            # If all required fields are collected, push the payload to the Logic Manager for scoring
            if result.is_complete:
                outcome = logic(result.report)
                _print_save_outcome(result.report, outcome)

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

