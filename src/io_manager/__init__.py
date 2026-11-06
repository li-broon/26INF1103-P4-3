# ------- #
# Imports
# ------- #

import textwrap  # Wraps Long Sentences onto Several Lines so Nothing is Cut Off
from abc import ABC, abstractmethod  # Abstract Base Classes, for the Menu Contract
from datetime import date, datetime  # Checks Whether a MOM Deadline has Passed

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.data_manager import (
    get_unique_values,
    load_matching_records,
    load_records,
)
from src.logic_manager import logic

from .styles import BOLD, CYAN, GREEN, RED, RESET, UNDERLINE, YELLOW


WELCOME = f"""

========================================================================
{CYAN}{BOLD} 
            Workplace Incident Reporting Assistant {RESET}

========================================================================
{BOLD}
        Hello! I'm here to help you report a workplace incident.{RESET}
        Just tell me what happened, like you're talking to a friend.
        I'll ask a few questions if anything is missing. 📝
        
        {GREEN}{BOLD}{UNDERLINE} Speak in YOUR language! Any language or a mix is OK.{RESET}

      🇬🇧  {GREEN}English{RESET}   : You can talk to me in your own language.
      🇲🇾  {GREEN}Melayu{RESET}    : Anda boleh bercakap dalam bahasa anda sendiri.
      🇨🇳  {GREEN}中文{RESET}      : 您可以用您的母语与我交谈。
      🇮🇳  {GREEN}தமிழ்{RESET}      : நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்.
      🇮🇳  {GREEN}हिन्दी{RESET}     : आप अपनी भाषा में बात कर सकते हैं।
      🇧🇩  {GREEN}বাংলা{RESET}     : আপনি আপনার নিজের ভাষায় কথা বলতে পারেন।{RESET}
    
{RED}{BOLD} If someone is still in danger, call 995 and your supervisor FIRST! 🚨{RESET}
      {YELLOW} Type your message below and press Enter to start. ⬇️{RESET}
"""
GOODBYE = f"{GREEN}Goodbye! Stay safe. {RESET}"
CANCEL_WORDS = ("quit", "exit", "cancel")  # Typing one of these in the chatbot asks to leave

# How Many Reports are Shown on Each Page of the Table
PAGE_SIZE = 3
#Map UI headings to the exact column names and set their display width
TABLE_COLUMNS = [
    ("Score", "importance_score", 7),
    ("Severity", "ai_severity", 9),
    ("Hosp.", "hospitalised", 6),
    ("MOM Due", "deadline", 12),
    ("Root Cause", "root_cause_category", 16),
    ("Location", "location", 14),
    ("Date", "incident_date", 12),
]
# Yes/No Columns Shown in Red when the Value is YES
ALERT_COLUMNS = ("hospitalised", "mom_reportable")

#Full-Text Fields Printed Under Each Summary Row: (Label, Column Name in 'data.csv')
#These Hold Whole Sentences, so They are Wrapped Instead of Squeezed into a Column
#(a 200-Character Safety Recommendation Cut to 18 Characters is No Use to Anyone)
DETAIL_FIELDS = [
    ("Reported by", "reporter_name"),
    ("Injury", "injury_status"),
    ("What happened", "description"),
    ("Action taken", "immediate_action_taken"),
    ("Recommended action", "safety_recommendation"),
]

# Layout of the Wrapped Detail Lines
DETAIL_INDENT = 7        # Spaces Before the Label, so Details Sit Under their Row
DETAIL_LABEL_WIDTH = 20  # Width of the "Label:" Part, Keeps the Text Lined Up
DETAIL_TEXT_WIDTH = 54   # Characters per Line Before Wrapping (Ends Level with the Table)

# Values that Mean "Nothing Was Saved Here" - Detail Lines with These are Skipped
EMPTY_VALUES = ("", "-", "nan", "none", "null")

# Every Field Shown when One Report is Opened in Full: (Label, Column Name in 'data.csv')
FULL_REPORT_FIELDS = [
    ("Reporter", "reporter_name"),
    ("Location", "location"),
    ("Date", "incident_date"),
    ("Time", "incident_time"),
    ("Score", "importance_score"),
    ("Severity", "ai_severity"),
    ("Root cause", "root_cause_category"),
    ("Near miss", "is_near_miss"),
    ("Hospitalised", "hospitalised"),
    ("Lost time injury", "lost_time_injury"),
    ("Hours stopped", "work_stoppage_hours"),
    ("Injury", "injury_status"),
    ("What happened", "description"),
    ("Action taken", "immediate_action_taken"),
    ("Recommended action", "safety_recommendation"),
    ("Language", "detected_language"),
    ("MOM reportable", "mom_reportable"),
    ("MOM deadline", "deadline"),
]

# True/False Fields, Shown as YES/No in the Full Report
YES_NO_COLUMNS = ("is_near_miss", "hospitalised", "lost_time_injury", "mom_reportable")

FILTER_COLUMNS = [
    ("Score", "importance_score"),
    ("Date", "incident_date"),
    ("Location", "location"),
    ("Severity", "ai_severity"),
    ("Root Cause", "root_cause_category"),
    ("MOM Reportable", "mom_reportable"),
    ("MOM Deadline", "deadline"),
]

#Dynamically calculate the back option number so it stays correct if columns are added later
FILTER_BACK_OPTION = len(FILTER_COLUMNS) + 1



#Asks the User for Input and Keeps Asking Until the Answer is Valid
class Prompter:
    def __init__(self, read=input, cancel_words=CANCEL_WORDS):
        self._read=read
        self._cancel_words= cancel_words

    def ask_yes_no(self, question: str) -> bool:
        while True:
            answer = self._read(f"{question} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print(f"{YELLOW}Please type 'y' for yes or 'n' for no.{RESET}")

    def ask_number(self,prompt:str, low:int, high: int) -> int: 
        while True: 
            user_input = self._read(prompt).strip()

            #rejects blank input
            if user_input =="":
                print(f"{YELLOW}This can't be left blank. Please type a number.{RESET}")
                continue 
            
            try:
                choice= int(user_input)
            except ValueError:
                print(f"{YELLOW}'{user_input}' is not a number. Please type a whole number.{RESET}")
                continue
            if low <= choice <= high:
                return choice
            print(f"{YELLOW}{choice} is not an option. Please type a number from {low} to {high}.{RESET}")

# One Prompter Shared by the Whole App (Moves into the IOManager Class Later)
_prompter = Prompter()

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

# One Formatter Shared by the Whole App (Moves into the IOManager Class Later)
_formatter = ReportFormatter()

#Which page of a table is showing and moves between pages (Never Prints)
class Pager:
    def __init__(self, total_rows: int, page_size: int =PAGE_SIZE):
        self._total = total_rows #How many rows the table has
        self._page_size = page_size # How many rows fit on one page 
        self._page = 1 #Ensure the page starts at 1

    #the page currently shown 
    def current_page(self) -> int:
        return self._page 

    #How many pages the table needs so the table still has 1 empty table
    def page_count(self) -> int:
        # Divide and round UP: -(-7 // 3) = 3, because 7 rows need 3 pages (3 + 3 + 1)
        return max(-(-self._total//self._page_size), 1)

    # The first and last row positions on the current page, e.g. (0, 3) for page 1
    def row_range(self) -> tuple:
        first = (self._page - 1) * self._page_size
        last = min(first + self._page_size, self._total)
        return first, last

    #Moves to the next page, Return flase if already on the last page
    def next(self) -> bool:
        if self._page >= self.page_count():
            return False
        self._page += 1 #the Pager now remembers it's on the next page
        return True

    #Moves to the previous page. return false if already on Page 1
    def previous(self) -> bool:
        if self._page <=1:
            return False
        self._page -= 1
        return True

#A Numbered Menu: Shows a Title and Options, then Asks the User to Pick One
#Each Child Menu Only Says WHAT its Title and Options Are, the Parent Does the Showing and Asking
class Menu(ABC):
    def __init__(self, prompter: Prompter):
        self._prompter = prompter   # The shared Prompter, passed in (the menu uses it but doesn't own it)

    # Every child menu MUST say what its title is
    @abstractmethod
    def title(self) -> str:
        pass

    # Every child menu MUST list its options, in order
    @abstractmethod
    def options(self) -> list:
        pass

    # a child menu that needs one overrides this method
    def subtitle(self) -> str:
        return ""
    # Same for every menu: print the title box and numbered options, then ask for a valid number
    def show(self) -> int:
        line = "=" * 72
        print(f"\n{line}\n{CYAN}{BOLD}{self.title().center(72)}{RESET}\n{line}")

        if self.subtitle():
            print(f"      {self.subtitle()}")

        options = self.options()
        for number, label in enumerate(options, start=1):
            print(f"      {GREEN}{BOLD}{number}{RESET}.  {label}")
        return self._prompter.ask_number(f"Choose an option (1-{len(options)}): ", 1, len(options))


#child class of Menu(Main Menu)
class MainMenu(Menu):
    def title(self) -> str:
        return "Main Menu"

    def options(self) -> list:
        return [
            "Report a new incident (chatbot)",
            "View saved incident reports",
            "Exit",
        ]

#Child Class of Menu (View Menu)
class ViewMenu(Menu):
    def title(self) -> str:
        return "📄 Report Options"

    def options(self) -> list:
        return [
            "Next page",
            "Previous page",
            "Filter these reports",
            "View a full report",
            "Back to the main menu",
        ]


#Child Class of Menu(PageMenu)
class PageMenu(Menu):
    def title(self) -> str:
        return "Page Options"

    def options(self) -> list:
        return [
            "Next page",
            "Previous page",
            "View a full report",
            "Back to report options",
        ]

#The Menu Asking Which Column to Filter By; its Options Come from FILTER_COLUMNS, Plus Back
class FilterMenu(Menu):
    def title(self) -> str:
        return "🔍 Filter Reports"

    def subtitle(self) -> str:
        return "Which column would you like to filter by?"

    def options(self) -> list:
        return [heading for heading, column in FILTER_COLUMNS] + ["↩️  Back"]

# One Object per Menu, Sharing the One Prompter (Moves into the IOManager Class Later)
_main_menu = MainMenu(_prompter)
_view_menu = ViewMenu(_prompter)
_page_menu = PageMenu(_prompter) 
_filter_menu = FilterMenu(_prompter)

#Display a numbered list of values and return the user's selection
def _choose_value(heading, values):
  #The selected value, or None if the user chooses the 'Back' option.
    back_option = len(values) + 1

    print(f"\n{BOLD}Values saved under {heading}:{RESET}")
    #Print out every available filter option as a numbered list
    for number, value in enumerate(values, start=1):
        print(f"      {GREEN}{BOLD}{number}{RESET}. {value}")
    print(f"      {GREEN}{BOLD}{back_option}{RESET}.   Back")

    choice = _prompter.ask_number(f"Choose a value (1-{back_option}): ", 1, back_option)
    if choice == back_option:
        return None
        
    #Subtract 1 because our menu starts at 1, but python lists start at 0
    return values[choice - 1]

#print one formatted page of the incident reports table
def _print_table(table, title, pager):
    total = len(table)
    first, last = pager.row_range()   

    print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")

    # Build the header row using our fixed column widths
    header = _formatter.fit_text("No.", 5)
    for heading, column, width in TABLE_COLUMNS:
        header += _formatter.fit_text(heading, width)
    print(f"{BOLD}{header}{RESET}")
    print("-" * len(header))

    #.iloc to show position 0-4 in page 1 and 5-9 for page 2
    #fillna with - with empty cells and save the results to variable called rows
    rows = table.iloc[first:last].fillna("-")
    #One Block per Report: a Summary Row, then its Full-Text Details Underneath
    #(Empty Cells Shown as "-", Already Sorted by Urgency in 'data_manager')
    for number, report in enumerate(rows.to_dict("records"), start=first + 1):
        print(_formatter.build_row(number, report))

        for label, column in DETAIL_FIELDS:
            for line in _formatter.wrap_detail(label, report.get(column, "-")):
                print(line)
        print()


        print(f"\n{CYAN}Page {pager.current_page()} of {pager.page_count()}  (showing {first + 1}-{last} of {total}){RESET}\n")

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
            print(f"{RED}{BOLD}⚠️  OVERDUE: this incident had to be reported to MOM by {outcome['deadline']}. "
                  f"Tell your supervisor now.{RESET}\n")
        else:
            print(f"{RED}{BOLD}⚠️  This incident must be reported to MOM by {outcome['deadline']}.{RESET}\n")

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
            _print_table(table, title, pager)

        choice = _page_menu.show()
        if choice == 1:
            show_page = pager.next()
            if not show_page:
                print(f"{YELLOW} You are already on the last page. {RESET}")
        elif choice == 2:
            show_page = pager.previous()
            if not show_page:
                print(f"{YELLOW}You are already on the first page. {RESET}")
        elif choice == 3:
            number = _prompter.ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
            print_full_report(table, number)
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
            _print_table(table, title, pager)

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
        value = _choose_value(heading, get_unique_values(column))
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

