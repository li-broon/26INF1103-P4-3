# ------- #
# Imports
# ------- #

from src.ai_manager import start_chat, send_message, check_api_key
from src.logic_manager import logic
from src.data_manager import (  # Gets Saved Reports from 'data_manager'
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

# Menu Options Range (Change MAX_OPTION if More Options are Added to the Menu)
MIN_OPTION = 1
MAX_OPTION = 3

# -------------------- #
# Saved Report Display
# -------------------- #

# Columns in the Saved Reports Table: (Heading, Column Name in 'data.csv', Width)
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

# Sub Menu View Options for saved reports (next page, previous page, filter, back to main menu)
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

# Page Menu Options range
PAGE_MIN_OPTION = 1
PAGE_MAX_OPTION = 3

# Page Size for Saved Reports Table (Number of Rows per Page)
PAGE_SIZE = 5

# Column Labels for the Filter Menu
FILTER_COLUMNS = [
    ("Score", "importance_score"),
    ("Date", "incident_date"),
    ("Location", "location"),
    ("Severity", "ai_severity"),
    ("Root Cause", "root_cause_category"),
]

# The "Back" Option is always the last index of the list of filter columns, so it is calculated dynamically
FILTER_BACK_OPTION = len(FILTER_COLUMNS) + 1

# Title Shown Above the Filter Options
FILTER_HEADER = f"""
========================================================================
{CYAN}{BOLD}                    🔍 Filter Reports{RESET}
========================================================================
      Which column would you like to filter by?
"""

# ---------------------------- #
# io_manager Private Functions
# ---------------------------- #

# Ask a Yes/No Question and Return True for Yes, False for No (Re-asks on Anything Else)
def _ask_yes_no(question):
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print(f"{YELLOW}Please type 'y' for yes or 'n' for no.{RESET}")

# Fit Text into a Column: Cut it Short with "…" if Too Long, Pad with Spaces if Too Short
def _fit(text, width):
    text = str(text)
    if len(text) >= width:
        text = text[:width - 2] + "…"
    return text.ljust(width)

# Ask for a number between low and high (inclusive), re-ask if invalid input is given
def _ask_number(prompt, low, high):
    while True:
        user_input = input(prompt).strip()

        # Reject Blank Input
        if user_input == "":
            print(f"{YELLOW}This can't be left blank. Please type a number.{RESET}")
            continue

        # Check it is an Integer (int() Raises ValueError for Text like "abc" or "1.5")
        try:
            choice = int(user_input)
        except ValueError:
            print(f"{YELLOW}'{user_input}' is not a number. Please type a whole number.{RESET}")
            continue

        # Check the Integer is in one of the menu options
        if low <= choice <= high:
            return choice
        print(f"{YELLOW}{choice} is not an option. Please type a number from {low} to {high}.{RESET}")

# Show the Saved Values as a Numbered List and Return the One the User Picks (None if they go Back)
def _choose_value(heading, values):
    back_option = len(values) + 1

    print(f"\n{BOLD}Values saved under {heading}:{RESET}")
    # Shows the data field values as a list of options, with the last option being "Back"
    for number, value in enumerate(values, start=1):
        print(f"      {GREEN}{BOLD}{number}{RESET}. {value}")
    print(f"      {GREEN}{BOLD}{back_option}{RESET}. ↩️  Back")

    choice = _ask_number(f"Choose a value (1-{back_option}): ", 1, back_option)
    if choice == back_option:
        return None
    return values[choice - 1]

# Calculate the total number of pages needed to display the table
def _page_count(table):
    pages = -(-len(table) // PAGE_SIZE)  # Divide and Round Up
    return max(pages, 1)

# Print ONE Page of a Table of Reports (Used by Both the Full List and the Filtered List)
def _print_table(table, title, page=1):
    total = len(table)
    first = (page - 1) * PAGE_SIZE           # Index of the First Row on this Page
    last = min(first + PAGE_SIZE, total)     # Index After the Last Row on this Page

    print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")

    header = _fit("No.", 5)
    for heading, column, width in TABLE_COLUMNS:
        header += _fit(heading, width)
    print(f"{BOLD}{header}{RESET}")
    print("-" * len(header))

    # One Row per Report on this Page (Empty Cells Shown as "-", Already Sorted by Urgency in 'data_manager')
    rows = table.iloc[first:last].fillna("-")
    for number, report in enumerate(rows.to_dict("records"), start=first + 1):
        row = _fit(number, 5)
        for heading, column, width in TABLE_COLUMNS:
            row += _fit(report.get(column, "-"), width)
        print(row)

    print(f"\n{CYAN}Page {page} of {_page_count(table)}  (showing {first + 1}-{last} of {total}){RESET}\n")

# Go to the Next Page, or Stay Put with a Message if Already on the Last Page
# Returns (new_page, moved) so the Caller Knows whether to Print the Page Again
def _go_next(page, pages):
    if page >= pages:
        print(f"{YELLOW}You are already on the last page.{RESET}")
        return page, False
    return page + 1, True

# Go to the Previous Page, or Stay Put with a Message if Already on the First Page
def _go_previous(page):
    if page <= 1:
        print(f"{YELLOW}You are already on the first page.{RESET}")
        return page, False
    return page - 1, True
    
# ------------------------- #
# io_manager Main Functions
# ------------------------- #

# Show the Menu and Return the User's Choice as an Integer limit user choices to the range of options available in the menu
def show_menu():
    print(MENU)
    return _ask_number(f"Choose an option ({MIN_OPTION}-{MAX_OPTION}): ", MIN_OPTION, MAX_OPTION)

# Show the Saved Reports Sub-Menu and Return the User's Choice (VIEW_MIN_OPTION to VIEW_MAX_OPTION)
def show_view_menu():
    print(VIEW_MENU)
    return _ask_number(f"Choose an option ({VIEW_MIN_OPTION}-{VIEW_MAX_OPTION}): ", VIEW_MIN_OPTION, VIEW_MAX_OPTION)

# Show the Page Menu and Return the User's Choice (PAGE_MIN_OPTION to PAGE_MAX_OPTION)
def show_page_menu():
    print(PAGE_MENU)
    return _ask_number(f"Choose an option ({PAGE_MIN_OPTION}-{PAGE_MAX_OPTION}): ", PAGE_MIN_OPTION, PAGE_MAX_OPTION)

# Show the Filter Menu and Return the User's Choice (1 to FILTER_BACK_OPTION)
def show_filter_menu():
    print(FILTER_HEADER)
    for number, (heading, column) in enumerate(FILTER_COLUMNS, start=1):
        print(f"      {GREEN}{BOLD}{number}{RESET}. {heading}")
    print(f"      {GREEN}{BOLD}{FILTER_BACK_OPTION}{RESET}. ↩️  Back")
    return _ask_number(f"Choose a column (1-{FILTER_BACK_OPTION}): ", 1, FILTER_BACK_OPTION)

# Print a Table One Page at a Time and Let the User Move Between Pages (Used for Filtered Results)
def browse_pages(table, title):
    pages = _page_count(table)
    page = 1
    show_page = True

    while True:
        if show_page:
            _print_table(table, title, page)

        # Everything Fits on One Page, so there is Nothing to Scroll
        if pages == 1:
            return

        choice = show_page_menu()
        if choice == 1:
            page, show_page = _go_next(page, pages)
        elif choice == 2:
            page, show_page = _go_previous(page)
        else:
            return

# Get Saved Reports from 'data_manager', Print them One Page at a Time, then Offer the Sub-Menu
def view_reports():

    # Go to 'data_manager' for the Data (Returns a Table, Empty if Nothing is Saved)
    table = load_records()

    # Back in 'io_manager', Print the Data for the User
    if table.empty:
        print(f"{YELLOW}No incident reports have been saved yet.{RESET}")
        return

    title = f"Saved Incident Reports ({len(table)} total, most urgent first)"
    pages = _page_count(table)
    page = 1
    show_page = True  # Only Print the Table Again when the Page Changed

    # Keep Offering the Sub-Menu until the User Goes Back (so they can Scroll or Filter More than Once)
    while True:
        if show_page:
            _print_table(table, title, page)

        choice = show_view_menu()

        if choice == 1:
            page, show_page = _go_next(page, pages)
        elif choice == 2:
            page, show_page = _go_previous(page)
        elif choice == 3:
            filter_reports()
            show_page = False  # The Filtered Results are on Screen, so Don't Reprint the Full Table
        else:
            break

# Let the User Pick a Column and a Value, then Show Only the Matching Reports
def filter_reports():
    # Choose the column to filter
    choice = show_filter_menu()
    if choice == FILTER_BACK_OPTION:
        return
    heading, column = FILTER_COLUMNS[choice - 1]

    # Open Ended search for location
    if column in ["location"]:
        value = input(f"\n{BOLD}Enter a keyword to search in {heading}:{RESET} ").strip()
        if not value:
            return
    else:
        value = _choose_value(heading, get_unique_values(column))
        if value is None:
            return

    # Step 3: Go to 'data_manager' for the Matching Rows (Most Urgent First) and Print them
    matches = load_matching_records(column, value)
    if matches.empty:
        print(f"{YELLOW}No reports found where {heading} is '{value}'.{RESET}")
        return

    browse_pages(matches, f"Reports where {heading} = {value} ({len(matches)} found, most urgent first)")

# Run the Chatbot to collect Incident Report
def run_chatbot():

    # Check if API Key Exists (Go Back to the Menu if it Doesn't)
    error = check_api_key()
    if error:
        print(f"{RED}{error}{RESET}")
        return

    # Initalise AI & Welcome User
    chat = start_chat()
    print(WELCOME)

    while True:
        result = send_message(chat, input("> "))  # User Input

        # Error Handling, Show Error Message
        if "error" in result:
            print(f"{RED}{BOLD}⚠️  Error Occurred:{RESET}")

            # Only API Errors have a Code/ Status
            if "error_code" in result:
                print(f"   {BOLD}{RED}Code:{RESET}    {result['error_code']}")
                print(f"   {BOLD}{RED}Status:{RESET}  {result['error_status']}")

            print(f"   {BOLD}{RED}Message:{RESET} {result['error']}")
            print(f"{BOLD}{RED}Please resend your last message to try again!{RESET}\n")

        # The AI Replies
        else:
            print(result["reply"])

            # If Chat is Completed, Send Completed JSON to 'logic_manager' (Scores & Saves it)
            if result["is_complete"]:
                logic(result["report"])
                print(f"\n{GREEN}{BOLD} Your report has been saved.{RESET}\n")

                # Offer to Show the Saved Reports from 'data_manager' Straight Away
                if _ask_yes_no("Would you like to view all saved reports now?"):
                    view_reports()
                break

# Main Loop: Show Menu, Run the Chosen Option, Repeat until User Exits
def main():
    while True:
        choice = show_menu()  

        if choice == 1:
            run_chatbot()
        elif choice == 2:
            view_reports()
        else:
            print(f"{GREEN}Goodbye! Stay safe. 👷{RESET}")
            break
