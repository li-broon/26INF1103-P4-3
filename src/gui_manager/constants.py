# Text, sizes and colours used by the GUI

import os

APP_TITLE = "Workplace Incident Reporting Assistant"

# App icon, and the ID Windows uses to show it in the taskbar
ICON_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.png")
WINDOWS_APP_ID = "P4-3.IncidentReportingAssistant"
APP_SUBTITLE = "Report what happened in any language."
EMERGENCY_TEXT = "Someone still in danger? Call 995 and your supervisor FIRST"

# Window sizes at 100% scaling
WINDOW_WIDTH, WINDOW_HEIGHT = 1060, 720
REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT = 660, 720

# Milliseconds between checks for the AI's reply, and between "thinking..." dots
POLL_MS = 100
THINKING_MS = 400

# Filter option for no filter
ALL_REPORTS = "All reports"

# Shown under the title of a saved conversation
TRANSCRIPT_NOTE = "Exactly as the worker and the chatbot wrote it, before any translation."

# Grey hint in the empty message box
PLACEHOLDER = "Describe what happened, then press Enter..."

# Greetings in Singapore's four official languages
LANGUAGE_GREETINGS = [
    ("English", "You can talk to me in your own language."),
    ("Melayu", "Anda boleh bercakap dalam bahasa anda sendiri."),
    ("中文", "您可以用您的母语与我交谈。"),
    ("தமிழ்", "நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்."),
]

FONT = "Segoe UI"

# Colours
BG = "#f3f5f9"            # Window background
SURFACE = "#ffffff"       # Cards, tables, message box
SURFACE_ALT = "#f8fafc"   # Every other table row
BORDER = "#dfe4ec"
TEXT = "#1e293b"
MUTED = "#64748b"
PRIMARY = "#2563eb"
PRIMARY_DARK = "#1d4ed8"
PRIMARY_SOFT = "#dbeafe"
HEADER_BG = "#0f172a"
HEADER_TEXT = "#f8fafc"
HEADER_MUTED = "#94a3b8"
DANGER = "#dc2626"
DANGER_SOFT = "#fef2f2"
ORANGE = "#ea580c"
ORANGE_SOFT = "#fff7ed"
WARNING = "#b45309"
WARNING_SOFT = "#fffbeb"
SUCCESS = "#15803d"
SUCCESS_SOFT = "#f0fdf4"
AI_BUBBLE = "#ffffff"

# Score colours, highest first: (lowest score, text colour, background)
SCORE_COLOURS = [
    (8, DANGER, DANGER_SOFT),
    (6, ORANGE, ORANGE_SOFT),
    (4, WARNING, WARNING_SOFT),
    (0, SUCCESS, SUCCESS_SOFT),
]

# Summary cards on the Reports tab: (key, caption, colour)
STAT_CARDS = [
    ("total", "SAVED REPORTS", PRIMARY),
    ("mom", "MOM REPORTABLE", WARNING),
    ("overdue", "MOM DEADLINE PASSED", DANGER),  # Includes reports already sent to MOM
    ("hospitalised", "HOSPITALISED", ORANGE),
]

# MOM table columns: (heading, column, width). The first column is the tick box
MOM_TABLE_COLUMNS = [
    ("Reported", "safety_officer_reported", 12),
    ("MOM Due", "deadline", 12),
    ("Severity", "ai_severity", 9),
    ("Score", "importance_score", 7),
    ("Location", "location", 16),
    ("Date", "incident_date", 12),
    ("Reporter", "reporter_name", 16),
    ("Reported On", "reported_on", 12),
]
TICKED, UNTICKED = "☑ Reported", "☐ Pending"

# Choices in the MOM tab's "Show" drop-down
MOM_SHOW_ALL, MOM_SHOW_PENDING, MOM_SHOW_REPORTED = "All", "Not yet reported", "Reported"

# Summary cards on the MOM tab: (key, caption, colour)
MOM_STAT_CARDS = [
    ("total", "MOM REPORTABLE", PRIMARY),
    ("pending", "NOT YET REPORTED", WARNING),
    ("overdue", "OVERDUE", DANGER),
    ("reported", "REPORTED", SUCCESS),
]

# Chat bubbles: kind -> (name, bubble colour, text colour, side)
BUBBLE_STYLES = {
    "you": ("You", PRIMARY, "#ffffff", "e"),
    "worker": ("Worker", PRIMARY, "#ffffff", "e"),  # Worker's messages in a saved conversation
    "ai": ("Chatbot", AI_BUBBLE, TEXT, "w"),
    "error": ("Problem", DANGER_SOFT, DANGER, "w"),
    "good": ("Report saved", SUCCESS_SOFT, SUCCESS, "w"),
}

# How much of the chat's width text can use before wrapping
BUBBLE_SHARE = 0.62
CARD_SHARE = 0.86
