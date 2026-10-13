# ------- #
# Imports
# ------- #

import textwrap  # Wraps Long Sentences onto Several Lines so Nothing is Cut Off
from datetime import date, datetime  # Checks Whether a MOM Deadline has Passed

from src.ai_manager import start_chat, send_message, check_api_key
from src.logic_manager import logic
from src.data_manager import ( 
    load_records,
    get_unique_values,
    load_matching_records,
)

# --------------- #
# Welcome Message
# --------------- #

RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"

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

# --------- #
# Main Menu
# --------- #

MENU = f"""
========================================================================
{CYAN}{BOLD}                     Main Menu{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}.  Report a new incident (chatbot)
      {GREEN}{BOLD}2{RESET}.  View saved incident reports
      {GREEN}{BOLD}3{RESET}.  Exit
"""

MIN_OPTION = 1
MAX_OPTION = 3
GOODBYE = f"{GREEN}Goodbye! Stay safe. {RESET}"
CANCEL_WORDS = ("quit", "exit", "cancel")

# -------------------- #
# Saved Report Display
# -------------------- #

# Map UI headings to the exact column names and set their display width

TABLE_COLUMNS = [
    ("Score", "importance_score", 7),
    ("Severity", "ai_severity", 9),
    ("Hosp.", "hospitalised", 6),
    ("MOM Due", "deadline", 12),
    ("Root Cause", "root_cause_category", 16),
    ("Location", "location", 14),
    ("Date", "incident_date", 12),
]

# Full-Text Fields Printed Under Each Summary Row: (Label, Column Name in 'data.csv')
# These Hold Whole Sentences, so They are Wrapped Instead of Squeezed into a Column
# (a 200-Character Safety Recommendation Cut to 18 Characters is No Use to Anyone).
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

# ---------------------------- #
# Saved Report Sub Menu
# ---------------------------- #

VIEW_MENU = f"""
========================================================================
{CYAN}{BOLD}                    📄 Report Options{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}.  Next page
      {GREEN}{BOLD}2{RESET}.  Previous page
      {GREEN}{BOLD}3{RESET}.  Filter these reports
      {GREEN}{BOLD}4{RESET}.  View a full report
      {GREEN}{BOLD}5{RESET}.  Back to the main menu
"""
VIEW_MIN_OPTION = 1
VIEW_MAX_OPTION = 5

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

# ------------- #
# Filter Menu
# ------------- #

PAGE_MENU = f"""
========================================================================
{CYAN}{BOLD}                     Page Options{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}.  Next page
      {GREEN}{BOLD}2{RESET}.  Previous page
      {GREEN}{BOLD}3{RESET}.  View a full report 
      {GREEN}{BOLD}4{RESET}.  Back to report options 
"""

PAGE_MIN_OPTION = 1
PAGE_MAX_OPTION = 4
PAGE_SIZE = 3

FILTER_COLUMNS = [
    ("Score", "importance_score"),
    ("Date", "incident_date"),
    ("Location", "location"),
    ("Severity", "ai_severity"),
    ("Root Cause", "root_cause_category"),
    ("MOM Reportable", "mom_reportable"),
    ("MOM Deadline", "deadline"),
]

# Dynamically calculate the back option number so it stays correct if columns are added later
FILTER_BACK_OPTION = len(FILTER_COLUMNS) + 1

FILTER_HEADER = f"""
========================================================================
{CYAN}{BOLD}                    🔍 Filter Reports{RESET}
========================================================================
      Which column would you like to filter by?
"""

# ---------------------------- #
# io_manager Private Functions
# ---------------------------- #

def _ask_yes_no(question):
    """
    Prompt the user with a yes/no question until a valid response is given.

    Parameters:
    question (str): The prompt to display.

    Returns:
    bool: True if the user answers 'yes'/'y', False if 'no'/'n'.
    """
    # Keep looping until they give a clear yes or no answer
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print(f"{YELLOW}Please type 'y' for yes or 'n' for no.{RESET}")

def _fit(text, width):
    """
    Format text to fit a specific column width, truncating or padding as needed.

    Parameters:
    text (any): The data to format into a string.
    width (int): The exact character width of the output column.

    Returns:
    str: The formatted string padded with spaces or truncated with an ellipsis '…'.
    """
    text = str(text)
    # If the text is too long, cut it and add an ellipsis so it doesn't break the table layout
    if len(text) >= width:
        text = text[:width - 2] + "…"
    # Otherwise, add spaces to pad the column so everything lines up nicely
    return text.ljust(width)

# Show True/False as YES/No (Safety Officers Scan this Column First for Hospital Cases)
def _yes_no(value):
    text = str(value).strip().lower()
    if text in ("true", "yes", "1", "1.0"):
        return "YES"
    if text in ("false", "no", "0", "0.0"):
        return "No"
    return "-"

# Turn One Long Field into Wrapped, Indented Lines (Returns [] if the Field is Empty)
def _wrap_detail(label, text):
    text = str(text).strip()
    if text.lower() in EMPTY_VALUES:
        return []

    indent = " " * DETAIL_INDENT
    label_cell = f"{label}:".ljust(DETAIL_LABEL_WIDTH)
    lines = textwrap.wrap(text, width=DETAIL_TEXT_WIDTH) or [text]

    # First Line Carries the Label, the Rest Line Up Underneath the Text
    wrapped = [f"{indent}{CYAN}{label_cell}{RESET}{lines[0]}"]
    wrapped += [f"{indent}{' ' * DETAIL_LABEL_WIDTH}{line}" for line in lines[1:]]
    return wrapped

# Build One Summary Row, Highlighting Hospital Cases in Red
# Columns Shown in Red when the Value is YES
ALERT_COLUMNS = ("hospitalised", "mom_reportable")

# Build One Summary Row, Highlighting Hospital and MOM Cases in Red
def _build_row(number, report):
    row = _fit(number, 5)
    for heading, column, width in TABLE_COLUMNS:
        value = report.get(column, "-")

        # Yes/No Columns: YES is Worth Shouting About
        if column in ALERT_COLUMNS:
            value = _yes_no(value)
            cell = _fit(value, width)  # Padded Before Colouring, so Columns Stay Lined Up
            row += f"{RED}{BOLD}{cell}{RESET}" if value == "YES" else cell
            continue

        # The Deadline is Only Urgent when MOM Must be Told
        if column == "deadline":
            cell = _fit(value, width)
            must_report = _yes_no(report.get("mom_reportable")) == "YES"
            row += f"{RED}{BOLD}{cell}{RESET}" if must_report else cell
            continue

        row += _fit(value, width)
    return row

def _ask_number(prompt, low, high):
    """
    Ask the user to input a number within a specific range. Re-prompts on invalid input.

    Parameters:
    prompt (str): The message to display to the user.
    low (int): The minimum acceptable integer.
    high (int): The maximum acceptable integer.

    Returns:
    int: A valid integer choice within the specified bounds.
    """
    while True:
        user_input = input(prompt).strip()

        # Reject blank input
        if user_input == "":
            print(f"{YELLOW}This can't be left blank. Please type a number.{RESET}")
            continue

        # Make sure they actually typed a number, not text
        try:
            choice = int(user_input)
        except ValueError:
            print(f"{YELLOW}'{user_input}' is not a number. Please type a whole number.{RESET}")
            continue

        # Ensure the number is one of the valid menu options
        if low <= choice <= high:
            return choice
        print(f"{YELLOW}{choice} is not an option. Please type a number from {low} to {high}.{RESET}")

def _choose_value(heading, values):
    """
    Display a numbered list of values and return the user's selection.

    Parameters:
    heading (str): The title for the list of values.
    values (list): A list of unique strings/options to display.

    Returns:
    str | None: The selected value, or None if the user chooses the 'Back' option.
    """
    back_option = len(values) + 1

    print(f"\n{BOLD}Values saved under {heading}:{RESET}")
    # Print out every available filter option as a numbered list
    for number, value in enumerate(values, start=1):
        print(f"      {GREEN}{BOLD}{number}{RESET}. {value}")
    print(f"      {GREEN}{BOLD}{back_option}{RESET}. ↩️  Back")

    choice = _ask_number(f"Choose a value (1-{back_option}): ", 1, back_option)
    if choice == back_option:
        return None
        
    # Subtract 1 because our menu starts at 1, but python lists start at 0
    return values[choice - 1]

def _page_count(table):
    """
    Calculate the total number of pages required to display the data table.

    Parameters:
    table (pd.DataFrame): The data to be paginated.

    Returns:
    int: The total number of pages (minimum 1).
    """
    pages = -(-len(table) // PAGE_SIZE)  # Divide and Round Up
    return max(pages, 1)

def _print_table(table, title, page=1):
    """
    Print one formatted page of the incident reports table.

    Parameters:
    table (pd.DataFrame): The data to print.
    title (str): The title to display above the table.
    page (int): The current page number to render (default 1).
    """
    total = len(table)
    # Figure out exactly which rows belong on the current page
    first = (page - 1) * PAGE_SIZE           
    last = min(first + PAGE_SIZE, total)     

    print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")

    # Build the header row using our fixed column widths
    header = _fit("No.", 5)
    for heading, column, width in TABLE_COLUMNS:
        header += _fit(heading, width)
    print(f"{BOLD}{header}{RESET}")
    print("-" * len(header))

    #.iloc to show position 0-4 in page 1 and 5-9 for page 2
    #fillna with - with empty cells and save the results to variable called rows
    rows = table.iloc[first:last].fillna("-")
    # One Block per Report: a Summary Row, then its Full-Text Details Underneath
    # (Empty Cells Shown as "-", Already Sorted by Urgency in 'data_manager')
    for number, report in enumerate(rows.to_dict("records"), start=first + 1):
        print(_build_row(number, report))

        for label, column in DETAIL_FIELDS:
            for line in _wrap_detail(label, report.get(column, "-")):
                print(line)
        print()


    print(f"\n{CYAN}Page {page} of {_page_count(table)}  (showing {first + 1}-{last} of {total}){RESET}\n")

def _print_full_report(table, number):
    """
    Print every field of one report in full, so long names and locations are not cut off.

    Parameters:
    table (pd.DataFrame): The data the report is in.
    number (int): The report's 'No.' as shown in the table (starts at 1).
    """
    # Subtract 1 because the table numbers start at 1, but rows start at 0
    report = table.iloc[number - 1].fillna("-").to_dict()
    _print_report_card(report, f"Report #{number}")

def _print_report_card(report, title):
    """
    Print every field of one report under a title. Used for a saved report opened from
    the table, and for the confirmation card the worker sees after submitting.

    Parameters:
    report (dict): The report's fields, keyed by column name. Empty fields are skipped.
    title (str): The heading shown above the fields.
    """
    print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")
    for label, column in FULL_REPORT_FIELDS:
        value = report.get(column, "-")
        if column in YES_NO_COLUMNS:
            value = _yes_no(value)
        for line in _wrap_detail(label, value):
            print(line)
    print()

def _go_next(page, pages):
    """
    Increment the page index if a next page exists.

    Parameters:
    page (int): The current page number.
    pages (int): The total number of pages available.

    Returns:
    tuple: (new_page_number, boolean indicating if the page changed)
    """
    # Prevent the user from scrolling past the end of the data
    if page >= pages:
        print(f"{YELLOW}You are already on the last page.{RESET}")
        return page, False
    return page + 1, True

def _go_previous(page):
    """
    Decrement the page index if a previous page exists.

    Parameters:
    page (int): The current page number.

    Returns:
    tuple: (new_page_number, boolean indicating if the page changed)
    """
    # Prevent the user from scrolling into negative pages
    if page <= 1:
        print(f"{YELLOW}You are already on the first page.{RESET}")
        return page, False
    return page - 1, True

def _print_save_outcome(report, outcome):
    """
    Tell the worker whether their report was really saved. If it was, show it back to them
    as a confirmation card, with the score and MOM details the Logic Manager added.

    Parameters:
    report (dict): The report the AI collected from the worker.
    outcome (dict): The result from logic(): saved, message, importance_score, mom_reportable, deadline.
    """
    # Only claim success when the Data Manager actually wrote the record
    if not outcome["saved"]:
        print(f"\n{RED}{BOLD}❌ Your report was NOT saved.{RESET} {outcome['message']}")
        print(f"{YELLOW}Please tell your supervisor about this incident directly.{RESET}\n")
        return

    print(f"\n{GREEN}{BOLD}✅ Your report has been saved.{RESET}")

    # The card shows what was saved: the worker's details plus the Logic Manager's results
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

def _is_overdue(deadline, today=None):
    """
    Check whether a MOM deadline has already passed. A deadline of today is not overdue yet.

    Parameters:
    deadline (str): The deadline as YYYY-MM-DD.
    today (date): The date to compare against (default: today). Lets tests pick the date.

    Returns:
    bool: True if the deadline is before today. False if it is today, later, or not a valid date.
    """
    try:
        due = datetime.strptime(str(deadline), "%Y-%m-%d").date()
    except ValueError:
        return False  # e.g. "Check incident date": no real date to compare
    return due < (today or date.today())

# ------------------------- #
# io_manager Main Functions
# ------------------------- #

def show_menu():
    """
    Display the main menu and prompt the user for a selection.

    Returns:
    int: The selected menu option.
    """
    print(MENU)
    return _ask_number(f"Choose an option ({MIN_OPTION}-{MAX_OPTION}): ", MIN_OPTION, MAX_OPTION)

def show_view_menu():
    """
    Display the sub-menu for viewing saved reports.

    Returns:
    int: The selected menu option.
    """
    print(VIEW_MENU)
    return _ask_number(f"Choose an option ({VIEW_MIN_OPTION}-{VIEW_MAX_OPTION}): ", VIEW_MIN_OPTION, VIEW_MAX_OPTION)

def show_page_menu():
    """
    Display the pagination control menu.

    Returns:
    int: The selected menu option.
    """
    print(PAGE_MENU)
    return _ask_number(f"Choose an option ({PAGE_MIN_OPTION}-{PAGE_MAX_OPTION}): ", PAGE_MIN_OPTION, PAGE_MAX_OPTION)

def show_filter_menu():
    """
    Display the available columns that can be used for filtering.

    Returns:
    int: The index of the selected column to filter by, or the 'Back' option.
    """
    print(FILTER_HEADER)
    for number, (heading, column) in enumerate(FILTER_COLUMNS, start=1):
        print(f"      {GREEN}{BOLD}{number}{RESET}. {heading}")
    print(f"      {GREEN}{BOLD}{FILTER_BACK_OPTION}{RESET}. ↩️  Back")
    return _ask_number(f"Choose a column (1-{FILTER_BACK_OPTION}): ", 1, FILTER_BACK_OPTION)

def browse_pages(table, title):
    """
    Manage the pagination loop, allowing a user to scroll through a table.
    and open any row in full. Report numbers are counted against the table
    passed in, so they stay corrected for a filtered subset. 

    Parameters:
    table (pd.DataFrame): The dataset to display.
    title (str): The title of the table view.
    """
    pages = _page_count(table)
    page = 1
    show_page = True

    # Keep the user in the page loop until they choose to exit
    while True:
        if show_page:
            _print_table(table, title, page)

        choice = show_page_menu()
        if choice == 1:
            page, show_page = _go_next(page, pages)
        elif choice == 2:
            page, show_page = _go_previous(page)
        elif choice == 3: 
            number = _ask_number(f"Which report number? (1-{len(table)}): ", 1, len(table))
            _print_full_report(table, number)
            # Keep the full report on screen instead of printing the table over it
            show_page = False
        else:
            return

def view_reports():
    """
    Retrieve saved reports from the Data Manager and initiate the viewing sequence.
    Provides options to paginate, filter the full dataset, or open one report in full.
    """
    table = load_records() # Load all saved data from the Data Manager

    # Handle the empty dataframe gracefully without crashing
    if table.empty:
        print(f"{YELLOW}No incident reports have been saved yet.{RESET}")
        return

    title = f"Saved Incident Reports ({len(table)} total, most urgent first)"
    pages = _page_count(table) # Calculate the total number of pages based on the dataset size
    page = 1
    show_page = True  

    while True:
        # Only print the table if the page has changed or it's the first display
        if show_page: 
            _print_table(table, title, page)

        # Show sub-menu options for navigating pages or filtering reports
        choice = show_view_menu()

        if choice == 1:
            page, show_page = _go_next(page, pages)
        elif choice == 2:
            page, show_page = _go_previous(page)
        elif choice == 3:
            filter_reports()
            # Stop the main table from re-printing immediately after they finish viewing the filtered results
            show_page = False
        elif choice == 4:
            number = _ask_number(f"Which report number, out of all {len(table)} saved reports?: (1-{len(table)}):", 1, len(table))
            _print_full_report(table, number)
            # Keep the full report on screen instead of printing the table over it
            show_page = False
        else:
            break

def filter_reports():
    """
    Prompt the user to filter the dataset by a specific column and value.
    Supports open keyword search for location fields and exact match/thresholds for others.
    """
    choice = show_filter_menu()
    if choice == FILTER_BACK_OPTION:
        return
        
    # Extract the selected column and its UI heading to run the filter
    heading, column = FILTER_COLUMNS[choice - 1]

    # Open ended keyword search for location so users don't have to pick from a massive list
    if column in ["location"]:
        value = input(f"\n{BOLD}Enter a keyword to search in {heading}:{RESET} ").strip()
        if not value:
            return
    else:
        # Display a list of unique values or threshold options for the selected column
        value = _choose_value(heading, get_unique_values(column))
        if value is None:
            return

    matches = load_matching_records(column, value)
    
    # Catch situations where the filter returned zero rows
    if matches.empty:
        print(f"{YELLOW}No reports found where {heading} is '{value}'.{RESET}")
        return

    # Pass the filtered subset into the pagination tool for viewing
    browse_pages(matches, f"Reports where {heading} matches '{value}' ({len(matches)} found, most urgent first)")

def run_chatbot():
    """
    Initialize the AI incident reporting chatbot, handle the conversation loop,
    and submit the finalized report to the Logic Manager.
    """
    # Verify we can connect to Gemini before starting the chatbot
    error = check_api_key()
    if error:
        print(f"{RED}{error}{RESET}")
        return

    chat = start_chat()
    print(WELCOME)

    while True:
        user_text = input("> ").strip()
        # Reject blank input and ask again, instead of spending an API call on nothing
        if user_text == "":
            print(f"{YELLOW}Please type something, or 'quit' to go back to the menu.{RESET}")
            continue

            #let the workers leave without finishing 
        if user_text.lower() in CANCEL_WORDS:
            if _ask_yes_no("Leave without finishing this report?"):
                print(f"{YELLOW}Report cancelled. Nothing was saved.{RESET}\n")
                return
            continue

        # Let the worker know the AI is working, since a reply can take a few seconds
        print("Thinking...\n")
        result = send_message(chat, user_text)

        # Catch API errors (like rate limits etc.) and allow the user to try again without losing their spot
        if "error" in result:
            print(f"{RED}{BOLD}  Error Occurred:{RESET}")

            if "error_code" in result:
                print(f"   {BOLD}{RED}Code:{RESET}    {result['error_code']}")
                print(f"   {BOLD}{RED}Status:{RESET}  {result['error_status']}")

            print(f"   {BOLD}{RED}Message:{RESET} {result['error']}")
            print(f"{BOLD}{RED}Please resend your last message to try again!{RESET}\n")

        else:
            # Print the AI's translated response to the terminal
            print(result["reply"])

            # If all required fields are collected, push the payload to the Logic Manager for scoring
            if result["is_complete"]:
                outcome = logic(result["report"])
                _print_save_outcome(result["report"], outcome)

                if _ask_yes_no("Would you like to view all saved reports now?"):
                    view_reports()
                break

#Display the main application loop. 
#Exits cleanly on Ctrl+C
def main():
    """
    The main application loop. Displays the main menu and routes user input to the core functions.
    """
    try:
        while True:
            choice = show_menu()  

            if choice == 1:
                run_chatbot()
            elif choice == 2:
                view_reports()
            else:
                print(GOODBYE)
                break

    except (KeyboardInterrupt, EOFError):
        print(f"\n{GOODBYE}")