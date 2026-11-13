# --Window Text, Sizes and Colours Shared by Every GUI Class (Constants Only, No Class)-- #

import os

APP_TITLE = "Workplace Incident Reporting Assistant"

# Window and Taskbar Icon (Two Folders Up from src/gui_manager/), and the Windows App ID that Lets the Taskbar Use it
ICON_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.png")
WINDOWS_APP_ID = "P4-3.IncidentReportingAssistant"
APP_SUBTITLE = "Report what happened in any language."
EMERGENCY_TEXT = "Someone still in danger? Call 995 and your supervisor FIRST"

# Window Sizes at 100% Display Scaling (fit_window Grows Them to Match the Screen)
WINDOW_WIDTH, WINDOW_HEIGHT = 1060, 720
REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT = 660, 720

# Milliseconds Between Checks for Gemini's Reply, and Between "Thinking..." Dots
POLL_MS = 100
THINKING_MS = 400

# Shown in the Column Box when No Filter is Applied
ALL_REPORTS = "All reports"

# Columns Where the User Types a Keyword Instead of Picking a Saved Value
KEYWORD_FILTER_COLUMNS = ("location",)

# Grey Hint in the Empty Message Box
PLACEHOLDER = "Describe what happened, then press Enter..."

# Greetings in Singapore's Four Official Languages, on the Welcome Card
LANGUAGE_GREETINGS = [
    ("English", "You can talk to me in your own language."),
    ("Melayu", "Anda boleh bercakap dalam bahasa anda sendiri."),
    ("中文", "您可以用您的母语与我交谈。"),
    ("தமிழ்", "நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்."),
]

FONT = "Segoe UI"

# Colours
BG = "#f3f5f9"            # Window Background
SURFACE = "#ffffff"       # Cards, Table, Message Box
SURFACE_ALT = "#f8fafc"   # Every Other Table Row
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

# Score Colours, Highest First: (Lowest Score, Text Colour, Background)
SCORE_COLOURS = [
    (8, DANGER, DANGER_SOFT),
    (6, ORANGE, ORANGE_SOFT),
    (4, WARNING, WARNING_SOFT),
    (0, SUCCESS, SUCCESS_SOFT),
]

# Summary Cards above the Reports Table: (Key in report_stats, Caption, Number Colour)
STAT_CARDS = [
    ("total", "SAVED REPORTS", PRIMARY),
    ("mom", "MOM REPORTABLE", WARNING),
    ("overdue", "MOM OVERDUE", DANGER),
    ("hospitalised", "HOSPITALISED", ORANGE),
]

# Chat Bubbles: Kind -> (Name Above the Bubble, Bubble Colour, Text Colour, Side of the Window)
BUBBLE_STYLES = {
    "you": ("You", PRIMARY, "#ffffff", "e"),
    "ai": ("Assistant", AI_BUBBLE, TEXT, "w"),
    "error": ("Problem", DANGER_SOFT, DANGER, "w"),
    "good": ("Report saved", SUCCESS_SOFT, SUCCESS, "w"),
}

# Share of the Chat's Width a Bubble or the Welcome Card Text may Use Before Wrapping
BUBBLE_SHARE = 0.62
CARD_SHARE = 0.86
