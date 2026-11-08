# Terminal Colour and Style Codes, Shared by Every IO Class (Constants Only, No Class, so the One-Class-per-File Rule Holds)
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

#Full-Text Fields Wrapped Under Each Summary Row: (Label, Column Name in 'data.csv'), Since Whole Sentences Don't Fit in a Table Column
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