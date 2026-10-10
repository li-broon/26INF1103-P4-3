# ------- #
# Imports
# ------- #

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
            👷 Workplace Incident Reporting Assistant 🦺{RESET}

========================================================================
{BOLD}
      👋 Hello! I'm here to help you report a workplace incident.{RESET}
      Just tell me what happened, like you're talking to a friend.
          I'll ask a few questions if anything is missing. 📝
        
        {GREEN}{BOLD}{UNDERLINE}🌏 Speak in YOUR language! Any language or a mix is OK.{RESET}

      🇬🇧  {GREEN}English{RESET}   : You can talk to me in your own language.
      🇲🇾  {GREEN}Melayu{RESET}    : Anda boleh bercakap dalam bahasa anda sendiri.
      🇨🇳  {GREEN}中文{RESET}      : 您可以用您的母语与我交谈。
      🇮🇳  {GREEN}தமிழ்{RESET}      : நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்.
      🇮🇳  {GREEN}हिन्दी{RESET}     : आप अपनी भाषा में बात कर सकते हैं।
      🇧🇩  {GREEN}বাংলা{RESET}     : আপনি আপনার নিজের ভাষায় কথা বলতে পারেন।{RESET}
    
{RED}{BOLD}🚨 If someone is still in danger, call 995 and your supervisor FIRST! 🚨{RESET}
      {YELLOW}💬 Type your message below and press Enter to start. ⬇️{RESET}
"""

# --------- #
# Main Menu
# --------- #

MENU = f"""
========================================================================
{CYAN}{BOLD}                    📋 Main Menu{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}. 💬 Report a new incident (chatbot)
      {GREEN}{BOLD}2{RESET}. 📂 View saved incident reports
      {GREEN}{BOLD}3{RESET}. 🚪 Exit
"""

MIN_OPTION = 1
MAX_OPTION = 3

# -------------------- #
# Saved Report Display
# -------------------- #

# Map UI headings to the exact column names and set their display width
TABLE_COLUMNS = [
    ("Score", "importance_score", 7),
    ("Date", "incident_date", 12),
    ("Reporter", "reporter_name", 15),
    ("Location", "location", 18),
    ("Severity", "ai_severity", 10),
    ("Root Cause", "root_cause_category", 18),
]

# ---------------------------- #
# Saved Report Sub Menu
# ---------------------------- #

VIEW_MENU = f"""
========================================================================
{CYAN}{BOLD}                    📄 Report Options{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}. ➡️  Next page
      {GREEN}{BOLD}2{RESET}. ⬅️  Previous page
      {GREEN}{BOLD}3{RESET}. 🔍 Filter these reports
      {GREEN}{BOLD}4{RESET}. ↩️  Back to the main menu
"""
VIEW_MIN_OPTION = 1
VIEW_MAX_OPTION = 4

# ------------- #
# Filter Menu
# ------------- #

PAGE_MENU = f"""
========================================================================
{CYAN}{BOLD}                    📄 Page Options{RESET}
========================================================================
      {GREEN}{BOLD}1{RESET}. ➡️  Next page
      {GREEN}{BOLD}2{RESET}. ⬅️  Previous page
      {GREEN}{BOLD}3{RESET}. ↩️  Back to report options
"""

PAGE_MIN_OPTION = 1
PAGE_MAX_OPTION = 3
PAGE_SIZE = 5

FILTER_COLUMNS = [
    ("Score", "importance_score"),
    ("Date", "incident_date"),
    ("Location", "location"),
    ("Severity", "ai_severity"),
    ("Root Cause", "root_cause_category"),
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

    # Slice the dataframe to only show the rows for this specific page
    rows = table.iloc[first:last].fillna("-")
    
    # Print each row, set - to missing data, and truncate/pad to fit the column width
    for number, report in enumerate(rows.to_dict("records"), start=first + 1):
        row = _fit(number, 5)
        for heading, column, width in TABLE_COLUMNS:
            row += _fit(report.get(column, "-"), width)
        print(row)

    print(f"\n{CYAN}Page {page} of {_page_count(table)}  (showing {first + 1}-{last} of {total}){RESET}\n")

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

        # If everything fits on screen, skip the next/prev menu entirely
        if pages == 1:
            return

        choice = show_page_menu()
        if choice == 1:
            page, show_page = _go_next(page, pages)
        elif choice == 2:
            page, show_page = _go_previous(page)
        else:
            return

def view_reports():
    """
    Retrieve saved reports from the Data Manager and initiate the viewing sequence.
    Provides options to paginate or filter the full dataset.
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
        result = send_message(chat, input("> "))  

        # Catch API errors (like rate limits etc.) and allow the user to try again without losing their spot
        if "error" in result:
            print(f"{RED}{BOLD}⚠️  Error Occurred:{RESET}")

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
                logic(result["report"])
                print(f"\n{GREEN}{BOLD}✅ Your report has been saved.{RESET}\n")

                if _ask_yes_no("Would you like to view all saved reports now?"):
                    view_reports()
                break

def main():
    """
    The main application loop. Displays the main menu and routes user input to the core functions.
    """
    while True:
        choice = show_menu()  

        if choice == 1:
            run_chatbot()
        elif choice == 2:
            view_reports()
        else:
            print(f"{GREEN}Goodbye! Stay safe. 👷{RESET}")
            break