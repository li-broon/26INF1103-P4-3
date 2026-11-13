# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import (
    AI_BUBBLE, BG, BORDER, BUBBLE_SHARE, BUBBLE_STYLES, CARD_SHARE, LANGUAGE_GREETINGS, MUTED, PRIMARY, SURFACE, TEXT,
)
from src.gui_manager.theme import card, font

# ----- #
# Class
# ----- #

# Scrolling List of Chat Bubbles, with the Welcome Card at the Top
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
        self._wrapped = []  # (Label, Share of the Width), so Text Re-Wraps when the Window is Resized

        self._inner.bind("<Configure>", self._update_scroll_region)
        self._canvas.bind("<Configure>", self._resize)
        # Windows and macOS Send the Wheel as <MouseWheel>; Linux (and Docker) Send Buttons 4 (Up) and 5 (Down).
        # Bound on this Chat's Own Window (Not the Whole App), so the Binding Goes Away with the Window
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.winfo_toplevel().bind(sequence, self._mouse_wheel, add="+")

    def _update_scroll_region(self, event=None):
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
        scroll_up = event.num == 4 or event.delta > 0
        self._canvas.yview_scroll(-1 if scroll_up else 1, "units")

    def _wrap_width(self, share):
        return max(240, int(self._canvas.winfo_width() * share))

    def _scroll_to_end(self):
        self.update_idletasks()
        self._update_scroll_region()
        self._canvas.yview_moveto(1.0)

    # Back to the First Message (a Saved Conversation is Read from the Start)
    def scroll_to_top(self):
        self._canvas.yview_moveto(0.0)

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
