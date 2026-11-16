# Imports

import tkinter as tk
from tkinter import ttk

from src.ai_manager.constants import WORKER_LABEL
from src.gui_manager.constants import BG, MUTED, REPORT_WINDOW_HEIGHT, REPORT_WINDOW_WIDTH, SURFACE, TEXT, TRANSCRIPT_NOTE
from src.gui_manager.theme import Theme
from src.gui_manager.widgets.chat_view import ChatView

# Class

# Pop-up window showing a saved conversation as chat bubbles
class TranscriptWindow(tk.Toplevel):
    def __init__(self, parent, turns: list, title: str):
        super().__init__(parent, bg=BG)
        self.title(title)
        Theme.fit_window(self, REPORT_WINDOW_WIDTH, REPORT_WINDOW_HEIGHT)
        self.transient(parent.winfo_toplevel())

        header = Theme.card(self, fill="x", padx=20, pady=(20, 12))
        inner = tk.Frame(header, bg=SURFACE)
        inner.pack(fill="x", padx=20, pady=16)
        tk.Label(inner, text=title, font=Theme.font(16, "bold"), fg=TEXT, bg=SURFACE).pack(anchor="w")
        tk.Label(inner, text=TRANSCRIPT_NOTE, font=Theme.font(10), fg=MUTED, bg=SURFACE).pack(anchor="w", pady=(2, 0))

        # Footer is packed first so it stays visible when the window is small
        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        ttk.Button(footer, text="Close", style="Secondary.TButton", command=self.destroy).pack(side="right")

        # Worker on the right, chatbot on the left
        chat = ChatView(self)
        chat.pack(fill="both", expand=True, pady=(0, 12))
        for speaker, text in turns:
            chat.add_message("worker" if speaker == WORKER_LABEL else "ai", text)
        chat.scroll_to_top()

        self.bind("<Escape>", lambda event: self.destroy())
        self.focus_set()
