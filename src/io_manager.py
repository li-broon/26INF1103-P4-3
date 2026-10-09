# ------- #
# Imports
# ------- #

import textwrap  # Wraps Long Sentences onto Several Lines so Nothing is Cut Off

from src.ai_manager import start_chat, send_message, check_api_key
from src.logic_manager import logic
from src.data_manager import load_records  # Gets Saved Reports from 'data_manager'

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

# Summary Row of Each Report: (Heading, Column Name in 'data.csv', Width)
# Ordered the Way a Safety Officer Triages a List: How Urgent is it, How Bad was it,
# Did Anyone Go to Hospital, What Caused it, Where, When, and Who Reported it Last.
TABLE_COLUMNS = [
    ("Score", "importance_score", 7),
    ("Severity", "ai_severity", 10),
    ("Hosp.", "hospitalised", 7),
    ("Root Cause", "root_cause_category", 20),
    ("Location", "location", 18),
    ("Date", "incident_date", 12),
    ("Reporter", "reporter_name", 12),
]

# Full-Text Fields Printed Under Each Summary Row: (Label, Column Name in 'data.csv')
# These Hold Whole Sentences, so They are Wrapped Instead of Squeezed into a Column
# (a 200-Character Safety Recommendation Cut to 18 Characters is No Use to Anyone).
DETAIL_FIELDS = [
    ("Injury", "injury_status"),
    ("What happened", "description"),
    ("Action taken", "immediate_action_taken"),
    ("Recommended action", "safety_recommendation"),
]

# Layout of the Wrapped Detail Lines
DETAIL_INDENT = 7        # Spaces Before the Label, so Details Sit Under their Row
DETAIL_LABEL_WIDTH = 20  # Width of the "Label:" Part, Keeps the Text Lined Up
DETAIL_TEXT_WIDTH = 64   # Characters per Line Before Wrapping (Ends Level with the Table)

# Values that Mean "Nothing Was Saved Here" - Detail Lines with These are Skipped
EMPTY_VALUES = ("", "-", "nan", "none", "null")

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
def _build_row(number, report):
    row = _fit(number, 5)
    for heading, column, width in TABLE_COLUMNS:
        value = report.get(column, "-")

        # Hospitalisation is a Straight Yes/No, and YES is Worth Shouting About
        if column == "hospitalised":
            value = _yes_no(value)
            cell = _fit(value, width)  # Padded Before Colouring, so Columns Stay Lined Up
            row += f"{RED}{BOLD}{cell}{RESET}" if value == "YES" else cell
            continue

        row += _fit(value, width)
    return row

# ------------------------- #
# io_manager Main Functions
# ------------------------- #

# Show the Menu and Return the User's Choice as an Integer (1, 2 or 3)
def show_menu():
    print(MENU)

    # Keep Asking until a Valid Option is Typed
    while True:
        user_input = input(f"Choose an option ({MIN_OPTION}-{MAX_OPTION}): ").strip()

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

        # Check the Integer is One of the Menu Options
        if MIN_OPTION <= choice <= MAX_OPTION:
            return choice
        print(f"{YELLOW}{choice} is not an option. Please type a number from {MIN_OPTION} to {MAX_OPTION}.{RESET}")

# Get Saved Reports from 'data_manager' and Print them in the Terminal
def view_reports():

    # Step 1: Go to 'data_manager' for the Data (Returns a Table, Empty if Nothing is Saved)
    table = load_records()

    # Step 2: Back in 'io_manager', Print the Data for the User
    if table.empty:
        print(f"{YELLOW}No incident reports have been saved yet.{RESET}")
        return

    print(f"\n{BOLD}{UNDERLINE}Saved Incident Reports ({len(table)} total, most urgent first){RESET}\n")

    # Heading Row, then a Line Underneath
    header = _fit("No.", 5)
    for heading, column, width in TABLE_COLUMNS:
        header += _fit(heading, width)
    print(f"{BOLD}{header}{RESET}")
    print("-" * len(header))

    # One Block per Report: a Summary Row, then its Full-Text Details Underneath
    # (Empty Cells Shown as "-", Already Sorted by Urgency in 'data_manager')
    table = table.fillna("-")
    for number, report in enumerate(table.to_dict("records"), start=1):
        print(_build_row(number, report))

        for label, column in DETAIL_FIELDS:
            for line in _wrap_detail(label, report.get(column, "-")):
                print(line)
        print()

# Run the Chatbot to Collect One Incident Report
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

        # Error Handling, Show Error Message Nicely
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
                print(f"\n{GREEN}{BOLD}✅ Your report has been saved.{RESET}\n")

                # Offer to Show the Saved Reports from 'data_manager' Straight Away
                if _ask_yes_no("Would you like to view all saved reports now?"):
                    view_reports()
                break

# Main Loop: Show Menu, Run the Chosen Option, Repeat until User Exits
def main():
    while True:
        choice = show_menu()  # Always an Integer (1, 2 or 3)

        if choice == 1:
            run_chatbot()
        elif choice == 2:
            view_reports()
        else:
            print(f"{GREEN}Goodbye! Stay safe. 👷{RESET}")
            break
