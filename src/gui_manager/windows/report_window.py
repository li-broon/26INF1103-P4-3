# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import (
    BG, DANGER, DANGER_SOFT, MUTED, PRIMARY, PRIMARY_SOFT, REPORT_WINDOW_HEIGHT, REPORT_WINDOW_WIDTH,
    SUCCESS, SUCCESS_SOFT, SURFACE, TEXT,
)
from src.gui_manager.theme import badge, card, fit_window, font
from src.gui_manager.windows.transcript_window import TranscriptWindow

# ----- #
# Class
# ----- #

# Pop-Up Window Showing One Full Report (a Report Opened from the Table, or the One Just Saved), with its Conversation a Click Away
class ReportWindow(tk.Toplevel):
    def __init__(self, parent, formatter, report: dict, title: str, transcript: str | None = None):
        super().__init__(parent, bg=BG)
        self.title(title)
        scale = fit_window(self, REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT)
        self.transient(parent.winfo_toplevel())
        self._formatter = formatter
        self._transcript = transcript  # The Saved Conversation Text, or None for a Report Without One
        self._title = title
        show = formatter.display_value

        # Header: Title, Who/Where/When, and Badges
        header = card(self, fill="x", padx=20, pady=(20, 12))
        inner = tk.Frame(header, bg=SURFACE)
        inner.pack(fill="x", padx=20, pady=16)
        tk.Label(inner, text=title, font=font(16, "bold"), fg=TEXT, bg=SURFACE).pack(anchor="w")

        when = " ".join(part for part in (show(report.get("incident_date")), show(report.get("incident_time"))) if part != "-")
        summary = "  ·  ".join(part for part in (show(report.get("reporter_name")), show(report.get("location")), when)
                               if part and part != "-")
        if summary:
            tk.Label(inner, text=summary, font=font(10), fg=MUTED, bg=SURFACE,
                     wraplength=int(560 * scale), justify="left").pack(anchor="w", pady=(2, 10))

        badges = tk.Frame(inner, bg=SURFACE)
        badges.pack(anchor="w")
        score_colour, score_background = formatter.score_colours(report.get("importance_score"))
        badge_specs = [(f"Score {show(report.get('importance_score'))}", score_colour, score_background)]
        severity = show(report.get("ai_severity"))
        if severity != "-":
            badge_specs.append((f"{severity} severity", PRIMARY, PRIMARY_SOFT))
        if formatter.yes_no(report.get("mom_reportable")) == "YES":
            badge_specs.append(("MOM reportable", DANGER, DANGER_SOFT))
        else:
            badge_specs.append(("Not MOM reportable", SUCCESS, SUCCESS_SOFT))
        for text, colour, background in badge_specs:
            badge(badges, text, colour, background).pack(side="left", padx=(0, 6))

        # The MOM Deadline is a Legal Requirement, so it Sits Above Everything Else
        warning = formatter.mom_warning(report)
        if warning:
            tk.Label(self, text=warning, fg=DANGER, bg=DANGER_SOFT, font=font(10, "bold"), anchor="w",
                     justify="left", padx=16, pady=10, wraplength=int(580 * scale),
                     highlightthickness=1, highlightbackground="#fecaca").pack(fill="x", padx=20, pady=(0, 12))

        # Footer Packed Before the Body, so it Keeps its Place when the Window is Made Smaller
        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        ttk.Button(footer, text="Close", style="Secondary.TButton", command=self.destroy).pack(side="right")
        if transcript:
            ttk.Button(footer, text="View conversation", style="Secondary.TButton",
                       command=self._open_transcript).pack(side="left")

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
        for label, value in formatter.full_report_lines(report):
            text.insert("end", label.upper() + "\n", "label")
            text.insert("end", value + "\n", "alert" if value == "YES" else "value")
        text.configure(state="disabled")  # Read Only: Saved Reports are Not Edited Here

        # Lambda Drops the Event Tkinter Passes, since destroy() Takes None
        self.bind("<Escape>", lambda event: self.destroy())
        self.focus_set()

    # "View conversation" Button: the Untranslated Chat Behind this Report, in a Third Window
    def _open_transcript(self):
        TranscriptWindow(self, self._formatter.transcript_turns(self._transcript), f"Conversation for {self._title}")
