# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import ttk

from src.ai_manager.constants import WORKER_LABEL
from src.gui_manager.constants import BG, MUTED, REPORT_WINDOW_HEIGHT, REPORT_WINDOW_WIDTH, SURFACE, TEXT, TRANSCRIPT_NOTE
from src.gui_manager.theme import card, fit_window, font
from src.gui_manager.widgets.chat_view import ChatView

# ----- #
# Class
# ----- #

# Pop-Up Window Showing a Saved Conversation as Chat Bubbles, the Way the Chat Tab Showed it at the Time
class TranscriptWindow(tk.Toplevel):
    def __init__(self, parent, turns: list, title: str):
        super().__init__(parent, bg=BG)
        self.title(title)
        fit_window(self, REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT)
        self.transient(parent.winfo_toplevel())

        header = card(self, fill="x", padx=20, pady=(20, 12))
        inner = tk.Frame(header, bg=SURFACE)
        inner.pack(fill="x", padx=20, pady=16)
        tk.Label(inner, text=title, font=font(16, "bold"), fg=TEXT, bg=SURFACE).pack(anchor="w")
        tk.Label(inner, text=TRANSCRIPT_NOTE, font=font(10), fg=MUTED, bg=SURFACE).pack(anchor="w", pady=(2, 0))

        # Footer Packed Before the Chat, so it Keeps its Place when the Window is Made Smaller
        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        ttk.Button(footer, text="Close", style="Secondary.TButton", command=self.destroy).pack(side="right")

        # The Same Bubble List as the Chat Tab: the Worker on the Right, the Chatbot on the Left
        chat = ChatView(self)
        chat.pack(fill="both", expand=True, pady=(0, 12))
        for speaker, text in turns:
            chat.add_message("worker" if speaker == WORKER_LABEL else "ai", text)
        chat.scroll_to_top()

        self.bind("<Escape>", lambda event: self.destroy())
        self.focus_set()
