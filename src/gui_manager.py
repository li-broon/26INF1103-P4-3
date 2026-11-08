# --Tkinter Window for the Incident Reporting Assistant: Same Managers as 'io_manager', Shown in a GUI Instead of the Terminal-- #

# ------- #
# Imports
# ------- #

import os
import queue  # Carries Gemini's Reply from the Background Thread to the Window
import threading  # Gemini Replies Take Seconds, so They Run Off the Window's Thread
import tkinter as tk
from tkinter import messagebox, ttk

from src.ai_manager import AIManager, AIServiceError, GeminiService
from src.data_manager import get_unique_values, load_matching_records, load_records
from src.io_manager import (
    CANCEL_WORDS,
    FILTER_COLUMNS,
    FULL_REPORT_FIELDS,
    TABLE_COLUMNS,
    YES_NO_COLUMNS,
    ReportFormatter,
    _is_overdue,
)
from src.logic_manager import logic

# ------------- #
# Configuration
# ------------- #

APP_TITLE = "Workplace Incident Reporting Assistant"
APP_SUBTITLE = "Report what happened in any language."
EMERGENCY_TEXT = "Someone still in danger? Call 995 and your supervisor FIRST"

# Window Size at Normal (100%) Display Scaling; Grown to Match the Screen's Scaling
WINDOW_WIDTH, WINDOW_HEIGHT = 1060, 720
REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT = 660, 720

# How Often (Milliseconds) the Window Checks Whether Gemini has Replied, and Animates "Thinking..."
POLL_MS = 100
THINKING_MS = 400

# Shown in the Column Box when No Filter is Applied
ALL_REPORTS = "All reports"

# Columns Where the User Types a Keyword Instead of Picking a Saved Value
KEYWORD_FILTER_COLUMNS = ("location",)

# Grey Hint Shown in the Empty Message Box
PLACEHOLDER = "Describe what happened, then press Enter..."

# Greetings in Singapore's Four Official Languages, Shown as a Card at the Top of Each New Chat
LANGUAGE_GREETINGS = [
    ("English", "You can talk to me in your own language."),
    ("Melayu", "Anda boleh bercakap dalam bahasa anda sendiri."),
    ("中文", "您可以用您的母语与我交谈。"),
    ("தமிழ்", "நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்."),
]

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

# Chat Bubbles: Kind -> (Name Above the Bubble, Bubble Colour, Text Colour, Side of the Window)
BUBBLE_STYLES = {
    "you": ("You", PRIMARY, "#ffffff", "e"),
    "ai": ("Assistant", AI_BUBBLE, TEXT, "w"),
    "error": ("Problem", DANGER_SOFT, DANGER, "w"),
    "good": ("Report saved", SUCCESS_SOFT, SUCCESS, "w"),
}

# Share of the Chat's Width a Bubble may Use Before its Text Wraps
BUBBLE_SHARE = 0.62
CARD_SHARE = 0.86

FONT = "Segoe UI"

# The .env File the Docker Command Reads, Loaded Here Too so the GUI Runs Outside Docker
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

# One Formatter Shared by the Whole Window (YES/No Wording Matches the Terminal)
_formatter = ReportFormatter()


# Build a Font Tuple in the App's Typeface
def font(size=10, weight="normal"):
    return (FONT, size, weight)


# ------------------------------------ #
# gui_manager Helpers (No Tkinter Used)
# ------------------------------------ #

# Read GEMINI_API_KEY from '.env' if it is Not Already Set (Values Already Set Always Win)
def load_env_file(path=ENV_FILE):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))

# Turn a Cell into Display Text, Treating Blanks and NaN as "-"
def display_value(value):
    if value is None or (isinstance(value, float) and value != value):  # value != value is only True for NaN
        return "-"
    text = str(value).strip()
    return text if text else "-"

# The Values for One Table Row, in TABLE_COLUMNS Order, with True/False Shown as YES/No
def table_row_values(number, report):
    values = [number]
    for heading, column, width in TABLE_COLUMNS:
        value = report.get(column)
        if column in YES_NO_COLUMNS:
            values.append(_formatter.yes_no(value))
        else:
            values.append(display_value(value))
    return values

# A Row is Highlighted when Someone went to Hospital or the Incident Must Go to MOM
def needs_attention(report):
    return (_formatter.yes_no(report.get("hospitalised")) == "YES"
            or _formatter.yes_no(report.get("mom_reportable")) == "YES")

# Every (Label, Value) Pair Shown when a Report is Opened in Full
def full_report_lines(report):
    lines = []
    for label, column in FULL_REPORT_FIELDS:
        value = report.get(column)
        if column in YES_NO_COLUMNS:
            value = _formatter.yes_no(value)
        lines.append((label, display_value(value)))
    return lines

# The MOM Warning for a Report, or None if it Does Not Need Reporting
def mom_warning(report):
    if _formatter.yes_no(report.get("mom_reportable")) != "YES":
        return None
    deadline = display_value(report.get("deadline"))
    if _is_overdue(deadline):
        return f"OVERDUE: this incident had to be reported to MOM by {deadline}. Tell your supervisor now."
    return f"This incident must be reported to MOM by {deadline}."

# (Text Colour, Background) for an Importance Score: Red for the Most Urgent, Green for the Least
def score_colours(score):
    try:
        value = float(score)
    except (TypeError, ValueError):
        return MUTED, SURFACE_ALT
    for lowest, colour, background in SCORE_COLOURS:
        if value >= lowest:
            return colour, background
    return SCORE_COLOURS[-1][1], SCORE_COLOURS[-1][2]  # Negative or NaN Scores Count as Least Urgent

# Counts for the Summary Cards above the Reports Table
def report_stats(table):
    stats = {"total": len(table), "mom": 0, "overdue": 0, "hospitalised": 0}
    for report in table.to_dict("records"):
        if _formatter.yes_no(report.get("hospitalised")) == "YES":
            stats["hospitalised"] += 1
        if _formatter.yes_no(report.get("mom_reportable")) == "YES":
            stats["mom"] += 1
            if _is_overdue(display_value(report.get("deadline"))):
                stats["overdue"] += 1
    return stats


# ------------------------------ #
# Look and Feel (ttk Styles)
# ------------------------------ #

# Make Text Sharp on Windows Screens Scaled Above 100% (Without This, Windows Stretches a Blurry Image)
def enable_sharp_text():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass  # Not Windows, or an Old Windows Version: Keep the Default

# Set Up Every ttk Style the Window Uses ('clam' is the Built-In Theme that Allows Custom Colours)
def apply_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.font", font(10))
    root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style.configure(".", background=BG, foreground=TEXT, font=font(10))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Card.TLabel", background=SURFACE)
    style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED, font=font(9, "bold"))

    # Tabs
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(20, 12, 20, 0))
    style.configure("TNotebook.Tab", padding=(20, 9), font=font(10, "bold"), background=BG,
                    foreground=MUTED, borderwidth=0, lightcolor=BG, bordercolor=BG)
    style.map("TNotebook.Tab", background=[("selected", SURFACE), ("active", "#e8edf5")],
              foreground=[("selected", PRIMARY)], lightcolor=[("selected", SURFACE)])

    # Buttons
    style.configure("Primary.TButton", background=PRIMARY, foreground="#ffffff", font=font(10, "bold"),
                    padding=(18, 8), borderwidth=0, focusthickness=0, lightcolor=PRIMARY, darkcolor=PRIMARY)
    style.map("Primary.TButton",
              background=[("disabled", "#a5bff5"), ("pressed", PRIMARY_DARK), ("active", PRIMARY_DARK)],
              lightcolor=[("active", PRIMARY_DARK)], darkcolor=[("active", PRIMARY_DARK)],
              foreground=[("disabled", "#ffffff")])
    style.configure("Secondary.TButton", background=SURFACE, foreground=TEXT, font=font(10),
                    padding=(14, 8), bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
                    borderwidth=1, focusthickness=0)
    style.map("Secondary.TButton", background=[("pressed", "#e2e8f0"), ("active", "#eef2f7")])

    # Text Boxes and Drop-Downs
    style.configure("TEntry", fieldbackground=SURFACE, foreground=TEXT, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, padding=(10, 8), insertcolor=TEXT)
    style.map("TEntry", bordercolor=[("focus", PRIMARY)], lightcolor=[("focus", PRIMARY)],
              fieldbackground=[("disabled", SURFACE_ALT)])
    style.configure("Placeholder.TEntry", foreground=MUTED)
    style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, arrowcolor=MUTED, padding=(8, 5))
    style.map("TCombobox",
              fieldbackground=[("readonly", SURFACE), ("disabled", SURFACE_ALT)],
              foreground=[("disabled", "#a0aec0")],
              selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", TEXT)],
              bordercolor=[("focus", PRIMARY)], lightcolor=[("focus", PRIMARY)])

    # Reports Table
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    rowheight=34, font=font(10), borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", background=SURFACE_ALT, foreground=MUTED, font=font(9, "bold"),
                    relief="flat", padding=(10, 9), borderwidth=0, lightcolor=BORDER, darkcolor=BORDER)
    style.map("Treeview.Heading", background=[("active", "#eef2f7")])
    style.map("Treeview", background=[("selected", PRIMARY_SOFT)], foreground=[("selected", TEXT)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # No Sunken Border

    # Scrollbars
    style.configure("Vertical.TScrollbar", background="#cbd5e1", troughcolor=BG, bordercolor=BG,
                    arrowcolor=MUTED, lightcolor="#cbd5e1", darkcolor="#cbd5e1", gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", "#94a3b8")])

# Size and Centre a Window: Grown to Match Display Scaling, but Never Bigger than 90% of the Screen
def fit_window(window, width, height):
    scale = window.winfo_fpixels("1i") / 96  # 1.0 at 100% Display Scaling, 1.5 at 150%
    width = min(int(width * scale), int(window.winfo_screenwidth() * 0.9))
    height = min(int(height * scale), int(window.winfo_screenheight() * 0.85))
    x = (window.winfo_screenwidth() - width) // 2
    y = max((window.winfo_screenheight() - height) // 3, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.minsize(min(int(width * 0.75), width), min(int(height * 0.75), height))
    return scale

# A White Card with a Thin Border (a Plain tk Frame, so the Border Colour can be Set)
def card(parent, **pack_options):
    frame = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
    if pack_options:
        frame.pack(**pack_options)
    return frame

# A Small Coloured Label, Used for the Score, Severity and MOM Status
def badge(parent, text, colour, background, bg=SURFACE):
    holder = tk.Frame(parent, bg=bg)
    tk.Label(holder, text=text, fg=colour, bg=background, font=font(9, "bold"), padx=10, pady=3).pack()
    return holder


# ------------------------------- #
# Window Showing One Full Report
# ------------------------------- #

class ReportWindow(tk.Toplevel):
    def __init__(self, parent, report, title):
        super().__init__(parent, bg=BG)
        self.title(title)
        scale = fit_window(self, REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT)
        self.transient(parent.winfo_toplevel())

        # Header: Title, Who/Where/When, and Badges
        header = card(self, fill="x", padx=20, pady=(20, 12))
        inner = tk.Frame(header, bg=SURFACE)
        inner.pack(fill="x", padx=20, pady=16)
        tk.Label(inner, text=title, font=font(16, "bold"), fg=TEXT, bg=SURFACE).pack(anchor="w")

        when = " ".join(part for part in (display_value(report.get("incident_date")),
                                          display_value(report.get("incident_time"))) if part != "-")
        summary = "  ·  ".join(part for part in (display_value(report.get("reporter_name")),
                                                  display_value(report.get("location")), when) if part and part != "-")
        if summary:
            tk.Label(inner, text=summary, font=font(10), fg=MUTED, bg=SURFACE,
                     wraplength=int(560 * scale), justify="left").pack(anchor="w", pady=(2, 10))

        badges = tk.Frame(inner, bg=SURFACE)
        badges.pack(anchor="w")
        score = display_value(report.get("importance_score"))
        colour, background = score_colours(report.get("importance_score"))
        badge(badges, f"Score {score}", colour, background).pack(side="left", padx=(0, 6))
        severity = display_value(report.get("ai_severity"))
        if severity != "-":
            badge(badges, f"{severity} severity", PRIMARY, PRIMARY_SOFT).pack(side="left", padx=(0, 6))
        if _formatter.yes_no(report.get("mom_reportable")) == "YES":
            badge(badges, "MOM reportable", DANGER, DANGER_SOFT).pack(side="left", padx=(0, 6))
        else:
            badge(badges, "Not MOM reportable", SUCCESS, SUCCESS_SOFT).pack(side="left", padx=(0, 6))

        # The MOM Deadline is a Legal Requirement, so it Sits Above Everything Else
        warning = mom_warning(report)
        if warning:
            tk.Label(self, text=warning, fg=DANGER, bg=DANGER_SOFT, font=font(10, "bold"), anchor="w",
                     justify="left", padx=16, pady=10, wraplength=int(580 * scale),
                     highlightthickness=1, highlightbackground="#fecaca").pack(fill="x", padx=20, pady=(0, 12))

        # Footer First, so it Keeps its Place when the Window is Made Smaller
        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        ttk.Button(footer, text="Close", style="Secondary.TButton", command=self.destroy).pack(side="right")

        # Every Field, Label Above Value
        body = card(self, fill="both", expand=True, padx=20, pady=(0, 12))
        text = tk.Text(body, wrap="word", relief="flat", bd=0, bg=SURFACE, fg=TEXT, padx=20, pady=12,
                       font=font(11), highlightthickness=0, cursor="arrow")
        scrollbar = ttk.Scrollbar(body, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        text.tag_configure("label", font=font(8, "bold"), foreground=MUTED, spacing1=12)
        text.tag_configure("value", font=font(11), foreground=TEXT, spacing1=2, lmargin1=0)
        text.tag_configure("alert", font=font(11, "bold"), foreground=DANGER, spacing1=2)
        for label, value in full_report_lines(report):
            text.insert("end", label.upper() + "\n", "label")
            text.insert("end", value + "\n", "alert" if value == "YES" else "value")
        text.configure(state="disabled")  # Read Only: Saved Reports are Not Edited Here

        self.bind("<Escape>", lambda event: self.destroy())
        self.focus_set()


# ---------------------------------------- #
# Scrolling List of Chat Bubbles
# ---------------------------------------- #

class ChatView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._wrapped = []  # (Label, Share of the Width) so Text Re-Wraps when the Window is Resized

        self._inner.bind("<Configure>", lambda event: self._update_scroll_region())
        self._canvas.bind("<Configure>", self._resize)
        self.bind_all("<MouseWheel>", self._mouse_wheel, add="+")

    def _update_scroll_region(self):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # Keep the Bubbles as Wide as the Chat, and Re-Wrap their Text
    def _resize(self, event):
        self._canvas.itemconfigure(self._window, width=event.width)
        for label, share in self._wrapped:
            label.configure(wraplength=max(240, int(event.width * share)))

    # Scroll Only when the Pointer is Over the Chat (the Table and Report Windows Scroll Themselves)
    def _mouse_wheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget is None or not str(widget).startswith(str(self._canvas)):
            return
        if self._canvas.yview() == (0.0, 1.0):
            return  # Everything Already Fits
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _wrap_width(self, share):
        return max(240, int(self._canvas.winfo_width() * share))

    def _scroll_to_end(self):
        self.update_idletasks()
        self._update_scroll_region()
        self._canvas.yview_moveto(1.0)

    # Remove Every Message (for a New Report)
    def clear(self):
        for child in self._inner.winfo_children():
            child.destroy()
        self._wrapped = []
        self._canvas.yview_moveto(0.0)

    # Add One Chat Bubble: the Worker's on the Right, Everything Else on the Left
    def add_message(self, kind, text):
        name, bubble, ink, side = BUBBLE_STYLES[kind]
        row = tk.Frame(self._inner, bg=BG)
        row.pack(fill="x", padx=24, pady=(4, 8))
        tk.Label(row, text=name, bg=BG, fg=MUTED, font=font(9, "bold")).pack(anchor=side, padx=2)
        label = tk.Label(row, text=text, bg=bubble, fg=ink, font=font(11), justify="left", anchor="w",
                         padx=16, pady=10, wraplength=self._wrap_width(BUBBLE_SHARE),
                         highlightthickness=1 if bubble == AI_BUBBLE else 0, highlightbackground=BORDER)
        label.pack(anchor=side, pady=(3, 0))
        self._wrapped.append((label, BUBBLE_SHARE))
        self._scroll_to_end()

    # The Welcome Card at the Top of Each New Chat
    def add_welcome(self):
        welcome = card(self._inner, fill="x", padx=24, pady=(20, 12))
        inner = tk.Frame(welcome, bg=SURFACE)
        inner.pack(fill="x", padx=22, pady=18)

        tk.Label(inner, text="Hello! I'm here to help you report a workplace incident.", font=font(14, "bold"),
                 fg=TEXT, bg=SURFACE).pack(anchor="w")
        intro = tk.Label(inner, text="Just tell me what happened, like you're talking to a friend. "
                                     "I'll ask a few questions if anything is missing.",
                         font=font(10), fg=MUTED, bg=SURFACE, justify="left", wraplength=self._wrap_width(CARD_SHARE))
        intro.pack(anchor="w", pady=(4, 12))
        self._wrapped.append((intro, CARD_SHARE))

        tk.Label(inner, text="Speak in YOUR language. Any language or a mix is OK.", font=font(10, "bold"),
                 fg=PRIMARY, bg=SURFACE).pack(anchor="w", pady=(0, 6))
        languages = tk.Frame(inner, bg=SURFACE)
        languages.pack(anchor="w", fill="x")
        for row, (language, greeting) in enumerate(LANGUAGE_GREETINGS):
            tk.Label(languages, text=language, font=font(10, "bold"), fg=TEXT, bg=SURFACE,
                     width=8, anchor="w").grid(row=row, column=0, sticky="w", pady=1)
            tk.Label(languages, text=greeting, font=font(10), fg=MUTED, bg=SURFACE,
                     anchor="w").grid(row=row, column=1, sticky="w", pady=1)
        self._scroll_to_end()


# ------------------------------------ #
# Tab 1: Chat with the AI to Report
# ------------------------------------ #

class ChatTab(ttk.Frame):
    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self._on_saved = on_saved      # Called after a Report is Saved, so the Reports Tab Refreshes
        self._conversation = None
        self._busy = False             # True while Waiting for Gemini, so Messages Aren't Sent Twice
        self._finished = False         # True once the Report is Saved, until a New Report is Started
        self._replies = queue.Queue()  # The Background Thread Leaves Gemini's Reply Here (Tkinter is Not Thread-Safe)
        self._placeholder = False      # True while the Grey Hint is Showing in the Message Box
        self._dots = 0                 # Animation Step for "Thinking..."

        self._chat = ChatView(self)
        self._chat.pack(fill="both", expand=True)

        self._thinking = tk.Label(self, text="", bg=BG, fg=MUTED, font=font(10, "italic"), anchor="w")
        self._thinking.pack(fill="x", padx=28, pady=(0, 4))

        # Message Box and Buttons, in a Card along the Bottom
        input_card = card(self, fill="x", padx=24, pady=(0, 20))
        input_row = tk.Frame(input_card, bg=SURFACE)
        input_row.pack(fill="x", padx=12, pady=12)
        self._entry = ttk.Entry(input_row, font=font(11))
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", lambda event: self.send())
        self._entry.bind("<FocusIn>", lambda event: self._hide_placeholder())
        self._entry.bind("<FocusOut>", lambda event: self._show_placeholder())
        self._send_button = ttk.Button(input_row, text="Send", style="Primary.TButton", command=self.send)
        self._send_button.pack(side="left", padx=(10, 0))
        ttk.Button(input_row, text="New report", style="Secondary.TButton",
                   command=self.ask_new_report).pack(side="left", padx=(8, 0))

        self.start_new_report()

    # Grey Hint in the Empty Message Box
    def _show_placeholder(self):
        if not self._entry.get() and str(self._entry.cget("state")) == "normal":
            self._entry.insert(0, PLACEHOLDER)
            self._entry.configure(style="Placeholder.TEntry")
            self._placeholder = True

    def _hide_placeholder(self):
        if self._placeholder:
            self._entry.delete(0, "end")
            self._entry.configure(style="TEntry")
            self._placeholder = False

    # What the Worker Typed (Never the Grey Hint)
    def _typed_text(self):
        return "" if self._placeholder else self._entry.get().strip()

    # Turn the Message Box and Send Button On or Off Together
    def _set_input(self, enabled):
        if enabled:
            self._entry.configure(state="normal")
            self._send_button.configure(state="normal")
            self._entry.focus_set()
            self._hide_placeholder()
        else:
            self._hide_placeholder()
            self._entry.configure(state="disabled")
            self._send_button.configure(state="disabled")

    # Animated "Assistant is thinking..." Line while Waiting for Gemini
    def _animate_thinking(self):
        if not self._busy:
            self._thinking.configure(text="")
            return
        self._dots = self._dots % 3 + 1
        self._thinking.configure(text="Assistant is thinking" + "." * self._dots)
        self.after(THINKING_MS, self._animate_thinking)

    # Clear the Chat and Start a Fresh Gemini Conversation (Shows the Error if the API Key is Missing)
    def start_new_report(self):
        self._chat.clear()
        self._finished = False
        self._chat.add_welcome()

        try:
            self._conversation = AIManager(GeminiService()).start_conversation()
        except AIServiceError as error:
            self._conversation = None
            self._chat.add_message("error", error.message)
            self._set_input(False)
            return
        self._set_input(True)

    # "New report" Button: Confirm First if a Report is Half Done
    def ask_new_report(self):
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Please wait for the assistant to finish replying.", parent=self)
            return
        if self._conversation and not self._finished:
            if not messagebox.askyesno(APP_TITLE, "Leave without finishing this report? Nothing will be saved.",
                                       parent=self):
                return
        self.start_new_report()

    # Send the Worker's Message to Gemini in the Background
    def send(self):
        if self._busy or self._conversation is None or self._finished:
            return
        user_text = self._typed_text()
        if not user_text:
            return
        self._entry.delete(0, "end")

        # Typing "quit" Works the Same as in the Terminal
        if user_text.lower() in CANCEL_WORDS:
            self.ask_new_report()
            return

        self._chat.add_message("you", user_text)
        self._busy = True
        self._set_input(False)
        self._animate_thinking()
        threading.Thread(target=self._worker, args=(user_text,), daemon=True).start()
        self.after(POLL_MS, self._check_for_reply)

    # Runs on the Background Thread: Never Touches Tkinter, Only Puts the Reply in the Queue
    def _worker(self, user_text):
        try:
            reply = self._conversation.send(user_text)
        except Exception as error:  # A Crash Here Would Otherwise Leave the Window Stuck on "Thinking..."
            reply = error
        self._replies.put(reply)

    # Runs on the Window's Thread: Check for Gemini's Reply, and Look Again Shortly if it Isn't Here Yet
    def _check_for_reply(self):
        try:
            reply = self._replies.get_nowait()
        except queue.Empty:
            self.after(POLL_MS, self._check_for_reply)
            return
        self._show_reply(reply)

    # Show the Reply, and Save the Report once it is Complete
    def _show_reply(self, reply):
        self._busy = False
        self._thinking.configure(text="")

        if isinstance(reply, Exception):
            self._chat.add_message("error", f"Something went wrong: {reply}\nPlease resend your last message.")
            self._set_input(True)
            return

        if reply.error:
            details = f"Code {reply.error_code} · {reply.error_status}\n" if reply.error_code is not None else ""
            self._chat.add_message("error", f"{details}{reply.error}\nPlease resend your last message to try again.")
            self._set_input(True)
            return

        self._chat.add_message("ai", reply.reply)
        if not reply.is_complete:
            self._set_input(True)
            return

        self._save_report(reply.report)

    # Score and Save the Finished Report through 'logic_manager', then Show the Worker What was Saved
    def _save_report(self, report):
        self._finished = True
        outcome = logic(report)

        # Only Claim Success when the Data Manager Actually Wrote the Record
        if not outcome["saved"]:
            self._chat.add_message("error", f"Your report was NOT saved. {outcome['message']}\n"
                                            "Please tell your supervisor about this incident directly.")
            return

        card_data = dict(report)
        for column in ("importance_score", "mom_reportable", "deadline"):
            card_data[column] = outcome[column]

        lines = [f"Importance score: {outcome['importance_score']}"]
        warning = mom_warning(card_data)
        lines.append(warning if warning else "This incident does not need to be reported to MOM.")
        lines.append("Press 'New report' to report another incident.")
        self._chat.add_message("good", "\n".join(lines))

        self._on_saved()
        ReportWindow(self, card_data, "Your Saved Report")


# --------------------------------------- #
# Tab 2: Browse and Filter Saved Reports
# --------------------------------------- #

class ReportsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._table = None  # The Reports Currently Listed (a DataFrame, Most Urgent First)

        # Summary Cards (Always Count Every Saved Report, Whatever the Filter)
        stats_row = tk.Frame(self, bg=BG)
        stats_row.pack(fill="x", padx=24, pady=(20, 12))
        self._stat_labels = {}
        for column, (key, caption, colour) in enumerate([
            ("total", "SAVED REPORTS", PRIMARY),
            ("mom", "MOM REPORTABLE", WARNING),
            ("overdue", "MOM OVERDUE", DANGER),
            ("hospitalised", "HOSPITALISED", ORANGE),
        ]):
            stat = card(stats_row)
            stat.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
            stats_row.columnconfigure(column, weight=1, uniform="stats")
            tk.Label(stat, text=caption, font=font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(14, 0))
            number = tk.Label(stat, text="0", font=font(22, "bold"), fg=colour, bg=SURFACE)
            number.pack(anchor="w", padx=18, pady=(0, 12))
            self._stat_labels[key] = number

        # Filter Bar
        bar_card = card(self, fill="x", padx=24, pady=(0, 12))
        bar = tk.Frame(bar_card, bg=SURFACE)
        bar.pack(fill="x", padx=16, pady=12)

        # Buttons Packed First so They Keep their Size when the Window is Narrow
        ttk.Button(bar, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Clear", style="Secondary.TButton", command=self.clear_filter).pack(side="right", padx=8)
        ttk.Button(bar, text="Apply", style="Primary.TButton", command=self.apply_filter).pack(side="right")

        ttk.Label(bar, text="FILTER BY", style="CardMuted.TLabel").pack(side="left")
        self._column_box = ttk.Combobox(bar, state="readonly", width=15, font=font(10),
                                        values=[ALL_REPORTS] + [heading for heading, column in FILTER_COLUMNS])
        self._column_box.set(ALL_REPORTS)
        self._column_box.pack(side="left", padx=(10, 18))
        self._column_box.bind("<<ComboboxSelected>>", lambda event: self._column_changed())

        ttk.Label(bar, text="VALUE", style="CardMuted.TLabel").pack(side="left")
        self._value_box = ttk.Combobox(bar, state="disabled", width=22, font=font(10))
        self._value_box.pack(side="left", padx=(10, 18))
        self._value_box.bind("<Return>", lambda event: self.apply_filter())
        self._value_box.bind("<<ComboboxSelected>>", lambda event: self.apply_filter())

        # Status Line and Hint
        info = tk.Frame(self, bg=BG)
        info.pack(fill="x", padx=26, pady=(0, 8))
        self._status = tk.Label(info, text="", font=font(10, "bold"), fg=TEXT, bg=BG)
        self._status.pack(side="left")
        tk.Label(info, text="Double-click a report to open it   ·   Red rows: hospitalised or MOM reportable",
                 font=font(9), fg=MUTED, bg=BG).pack(side="right")

        # Report Table
        table_card = card(self, fill="both", expand=True, padx=24, pady=(0, 20))
        columns = ["number"] + [column for heading, column, width in TABLE_COLUMNS]
        self._tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")
        self._tree.heading("number", text="NO.")
        self._tree.column("number", width=56, anchor="center", stretch=False)
        centred = ("importance_score", "hospitalised", "ai_severity")
        for heading, column, width in TABLE_COLUMNS:
            self._tree.heading(column, text=heading.upper(), anchor="center" if column in centred else "w")
            self._tree.column(column, width=width * 10, anchor="center" if column in centred else "w")
        self._tree.tag_configure("odd", background=SURFACE_ALT)
        self._tree.tag_configure("alert", foreground=DANGER, background=DANGER_SOFT)

        scrollbar = ttk.Scrollbar(table_card, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.bind("<Double-1>", lambda event: self.open_selected())
        self._tree.bind("<Return>", lambda event: self.open_selected())

        # Shown over the Table when there is Nothing to List
        self._empty = tk.Label(table_card, text="", font=font(11), fg=MUTED, bg=SURFACE)

        self.refresh()

    # The data.csv Column Name for the Heading Chosen in the Column Box (None for All Reports)
    def _chosen_column(self):
        for heading, column in FILTER_COLUMNS:
            if heading == self._column_box.get():
                return heading, column
        return None, None

    # Fill the Value Box for the Chosen Column: Saved Values to Pick, or Free Typing for Location
    def _column_changed(self):
        heading, column = self._chosen_column()
        self._value_box.set("")
        if column is None:
            self._value_box.configure(state="disabled", values=[])
            self.refresh()
        elif column in KEYWORD_FILTER_COLUMNS:
            self._value_box.configure(state="normal", values=[])
            self._value_box.focus_set()
        else:
            self._value_box.configure(state="readonly", values=get_unique_values(column))

    # Update the Summary Cards from Every Saved Report
    def _update_stats(self):
        for key, value in report_stats(load_records()).items():
            self._stat_labels[key].configure(text=str(value))

    # Put a Table of Reports into the Treeview
    def _show(self, table, status, empty_message=""):
        self._table = table
        self._tree.delete(*self._tree.get_children())
        for number, report in enumerate(table.to_dict("records"), start=1):
            if needs_attention(report):
                tags = ("alert",)
            else:
                tags = ("odd",) if number % 2 == 0 else ()
            self._tree.insert("", "end", iid=str(number), values=table_row_values(number, report), tags=tags)
        self._status.configure(text=status)

        if table.empty:
            self._empty.configure(text=empty_message)
            self._empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._empty.place_forget()
        self._update_stats()

    # Reload Every Saved Report, Keeping the Current Filter if One is Applied
    def refresh(self):
        heading, column = self._chosen_column()
        if column is not None and self._value_box.get().strip():
            self.apply_filter()
            return
        table = load_records()
        if table.empty:
            self._show(table, "No reports yet", "No incident reports have been saved yet.")
            return
        self._show(table, f"All reports  ·  {len(table)} total, most urgent first")

    # Show Only the Reports Matching the Chosen Column and Value
    def apply_filter(self):
        heading, column = self._chosen_column()
        if column is None:
            self.refresh()
            return
        value = self._value_box.get().strip()
        if not value:
            messagebox.showinfo(APP_TITLE, f"Choose or type a value for {heading} first.", parent=self)
            return

        matches = load_matching_records(column, value)
        if matches.empty:
            self._show(matches, f"{heading}: {value}  ·  0 found", f"No reports found where {heading} is '{value}'.")
            return
        self._show(matches, f"{heading}: {value}  ·  {len(matches)} found, most urgent first")

    # Go Back to Showing Every Report
    def clear_filter(self):
        self._column_box.set(ALL_REPORTS)
        self._column_changed()

    # Open the Highlighted Row in its Own Window
    def open_selected(self):
        selected = self._tree.selection()
        if not selected or self._table is None:
            return
        number = int(selected[0])
        report = self._table.iloc[number - 1].to_dict()
        ReportWindow(self, report, f"Report #{number}")


# ------------ #
# Main Window
# ------------ #

class IncidentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        fit_window(self, WINDOW_WIDTH, WINDOW_HEIGHT)
        apply_theme(self)

        # Header Bar: App Name, then a Full-Width Red Strip with the Emergency Reminder
        header = tk.Frame(self, bg=HEADER_BG)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=HEADER_BG)
        titles.pack(side="left", padx=24, pady=16)
        tk.Label(titles, text=APP_TITLE, font=font(16, "bold"), fg=HEADER_TEXT, bg=HEADER_BG).pack(anchor="w")
        tk.Label(titles, text=APP_SUBTITLE, font=font(10), fg=HEADER_MUTED, bg=HEADER_BG).pack(anchor="w")
        tk.Label(self, text=f"⚠  {EMERGENCY_TEXT}", font=font(10, "bold"), fg="#ffffff", bg=DANGER,
                 pady=7).pack(fill="x")

        tabs = ttk.Notebook(self)
        self._reports_tab = ReportsTab(tabs)
        self._chat_tab = ChatTab(tabs, on_saved=self._reports_tab.refresh)
        tabs.add(self._chat_tab, text="Report an incident")
        tabs.add(self._reports_tab, text="Saved reports")
        tabs.pack(fill="both", expand=True)


# ----------------------- #
# gui_manager Main Function
# ----------------------- #

def main():
    load_env_file()
    enable_sharp_text()
    IncidentApp().mainloop()
