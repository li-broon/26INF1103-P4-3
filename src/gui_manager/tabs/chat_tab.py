# ------- #
# Imports
# ------- #

import queue  # Carries Gemini's Reply from the Background Thread to the Window
import threading  # Gemini Replies Take Seconds, so They Run Off the Window's Thread
import tkinter as tk
from tkinter import messagebox, ttk

from src.ai_manager import AIServiceError
from src.io_manager.constants import CANCEL_WORDS
from src.gui_manager.constants import APP_TITLE, BG, MUTED, PLACEHOLDER, POLL_MS, SURFACE, THINKING_MS
from src.gui_manager.theme import card, font
from src.gui_manager.widgets.chat_view import ChatView
from src.gui_manager.windows.report_window import ReportWindow

# ----- #
# Class
# ----- #

# Tab 1: Chat with the AI to Report an Incident, then Score and Save it
class ChatTab(ttk.Frame):
    def __init__(self, parent, ai_manager, logic_manager, data_manager, formatter, on_saved):
        super().__init__(parent)
        # Handed in by GUIManager, Used but Not Owned (Association)
        self._ai_manager = ai_manager
        self._logic_manager = logic_manager
        self._data_manager = data_manager  # Only for the Transcript; the Report Itself is Saved through the Logic Manager
        self._formatter = formatter
        self._on_saved = on_saved      # Called after a Save, so the Reports Tab Refreshes

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
        self._entry.bind("<Return>", self.send)
        self._entry.bind("<KP_Enter>", self.send)  # The Number Pad's Enter on Linux and macOS
        self._entry.bind("<FocusIn>", self._hide_placeholder)
        self._entry.bind("<FocusOut>", self._show_placeholder)
        self._send_button = ttk.Button(input_row, text="Send", style="Primary.TButton", command=self.send)
        self._send_button.pack(side="left", padx=(10, 0))
        ttk.Button(input_row, text="New report", style="Secondary.TButton",
                   command=self.ask_new_report).pack(side="left", padx=(8, 0))

        self.start_new_report()

    # Grey Hint in the Empty Message Box
    def _show_placeholder(self, event=None):
        if not self._entry.get() and str(self._entry.cget("state")) == "normal":
            self._entry.insert(0, PLACEHOLDER)
            self._entry.configure(style="Placeholder.TEntry")
            self._placeholder = True

    def _hide_placeholder(self, event=None):
        if self._placeholder:
            self._entry.delete(0, "end")
            self._entry.configure(style="TEntry")
            self._placeholder = False

    # What the Worker Typed (Never the Grey Hint)
    def _typed_text(self):
        return "" if self._placeholder else self._entry.get().strip()

    # Turn the Message Box and Send Button On or Off Together (the Hint is Removed While Still Editable)
    def _set_input(self, enabled):
        self._hide_placeholder()
        state = "normal" if enabled else "disabled"
        self._entry.configure(state=state)
        self._send_button.configure(state=state)
        if enabled:
            self._entry.focus_set()

    # Animated "Chatbot is thinking..." Line while Waiting for Gemini
    def _animate_thinking(self):
        if not self._busy:
            self._thinking.configure(text="")
            return
        self._dots = self._dots % 3 + 1
        self._thinking.configure(text="Chatbot is thinking" + "." * self._dots)
        self.after(THINKING_MS, self._animate_thinking)

    # Clear the Chat and Start a Fresh Conversation (Shows the Error if the API Key is Missing)
    def start_new_report(self):
        self._chat.clear()
        self._finished = False
        self._chat.add_welcome()

        try:
            self._conversation = self._ai_manager.start_conversation()
        except AIServiceError as error:
            self._conversation = None
            self._chat.add_message("error", error.message)
            self._set_input(False)
            return
        self._set_input(True)

    # "New report" Button: Confirm First if a Report is Half Done
    def ask_new_report(self):
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Please wait for the chatbot to finish replying.", parent=self)
            return
        if self._conversation and not self._finished:
            if not messagebox.askyesno(APP_TITLE, "Leave without finishing this report? Nothing will be saved.",
                                       parent=self):
                return
        self.start_new_report()

    # Send the Worker's Message to Gemini in the Background
    def send(self, event=None):
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

    # Score and Save the Finished Report through the Logic Manager, then Show the Worker What was Saved
    def _save_report(self, report):
        self._finished = True
        outcome = self._logic_manager.process(report)

        # Only Claim Success when the Data Manager Actually Wrote the Record
        if not outcome.saved:
            self._chat.add_message("error", f"Your report was NOT saved. {outcome.message}\n"
                                            "Please tell your supervisor about this incident directly.")
            return

        # Keep the conversation next to the saved report (the report is already safe if only this part fails)
        transcript = self._conversation.transcript
        saved, message = self._data_manager.save_transcript(transcript.transcript_id, transcript.as_text())
        if not saved:
            self._chat.add_message("error", message)

        card_data = dict(report)
        for column in ("importance_score", "mom_reportable", "deadline"):
            card_data[column] = getattr(outcome, column)

        warning = self._formatter.mom_warning(card_data)
        lines = [f"Importance score: {outcome.importance_score}",
                 warning or "This incident does not need to be reported to MOM.",
                 "Press 'New report' to report another incident."]
        self._chat.add_message("good", "\n".join(lines))

        self._on_saved()
        ReportWindow(self, self._formatter, card_data, "Your Saved Report", transcript=transcript.as_text())
