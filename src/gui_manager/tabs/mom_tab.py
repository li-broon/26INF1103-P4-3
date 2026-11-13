# ------- #
# Imports
# ------- #

import tkinter as tk
from tkinter import messagebox, ttk

from src.data_manager.constants import MOM_ID_FIELD
from src.gui_manager.constants import (
    APP_TITLE, BG, DANGER, DANGER_SOFT, MOM_SHOW_ALL, MOM_SHOW_PENDING, MOM_SHOW_REPORTED, MOM_STAT_CARDS,
    MOM_TABLE_COLUMNS, MUTED, SUCCESS, SUCCESS_SOFT, SURFACE, TEXT,
)
from src.gui_manager.theme import card, font
from src.gui_manager.windows.report_window import ReportWindow

# ----- #
# Class
# ----- #

# Tab 3: the MOM Register. Only MOM Reportable Reports, with a Tick Box for "the Safety Officer has Reported This"; Ticking Writes Straight to mom_data.csv
class MomTab(ttk.Frame):
    def __init__(self, parent, mom_store, formatter):
        super().__init__(parent)
        # Handed in by GUIManager, Used but Not Owned (Association)
        self._mom_store = mom_store
        self._formatter = formatter
        self._table = None  # The Register as Last Loaded (a DataFrame); Rows are Found by their mom_id

        # Summary Cards (Always Count the Whole Register, Whatever "Show" is Set To)
        stats_row = tk.Frame(self, bg=BG)
        stats_row.pack(fill="x", padx=24, pady=(20, 12))
        self._stat_labels = {}
        for column, (key, caption, colour) in enumerate(MOM_STAT_CARDS):
            stat = card(stats_row)
            stat.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
            stats_row.columnconfigure(column, weight=1, uniform="mom_stats")
            tk.Label(stat, text=caption, font=font(8, "bold"), fg=MUTED, bg=SURFACE).pack(anchor="w", padx=18, pady=(14, 0))
            number = tk.Label(stat, text="0", font=font(22, "bold"), fg=colour, bg=SURFACE)
            number.pack(anchor="w", padx=18, pady=(0, 12))
            self._stat_labels[key] = number

        # Bar: Buttons Packed First so they Keep their Size when the Window is Narrow
        bar_card = card(self, fill="x", padx=24, pady=(0, 12))
        bar = tk.Frame(bar_card, bg=SURFACE)
        bar.pack(fill="x", padx=16, pady=12)
        ttk.Button(bar, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Tick / untick selected", style="Primary.TButton",
                   command=self.toggle_selected).pack(side="right", padx=8)

        ttk.Label(bar, text="SHOW", style="CardMuted.TLabel").pack(side="left")
        self._show_box = ttk.Combobox(bar, state="readonly", width=18, font=font(10),
                                      values=[MOM_SHOW_ALL, MOM_SHOW_PENDING, MOM_SHOW_REPORTED])
        self._show_box.set(MOM_SHOW_ALL)
        self._show_box.pack(side="left", padx=(10, 0))
        self._show_box.bind("<<ComboboxSelected>>", lambda event: self.refresh())

        # Status Line and Hint
        info = tk.Frame(self, bg=BG)
        info.pack(fill="x", padx=26, pady=(0, 8))
        self._status = tk.Label(info, text="", font=font(10, "bold"), fg=TEXT, bg=BG)
        self._status.pack(side="left")
        tk.Label(info, text="Click a tick box (or press Space) once the safety officer has reported it   ·   Double-click a row to open it",
                 font=font(9), fg=MUTED, bg=BG).pack(side="right")

        # MOM Table
        table_card = card(self, fill="both", expand=True, padx=24, pady=(0, 20))
        self._tree = ttk.Treeview(table_card, columns=[column for _, column, _ in MOM_TABLE_COLUMNS],
                                  show="headings", selectmode="browse")
        centred = ("safety_officer_reported", "importance_score", "ai_severity")
        for heading, column, width in MOM_TABLE_COLUMNS:
            anchor = "center" if column in centred else "w"
            self._tree.heading(column, text=heading.upper(), anchor=anchor)
            self._tree.column(column, width=width * 10, anchor=anchor)
        self._tree.tag_configure("overdue", foreground=DANGER, background=DANGER_SOFT)
        self._tree.tag_configure("reported", foreground=SUCCESS, background=SUCCESS_SOFT)

        scrollbar = ttk.Scrollbar(table_card, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.bind("<Button-1>", self._clicked)
        self._tree.bind("<Double-1>", self.open_selected)
        self._tree.bind("<space>", self.toggle_selected)
        self._tree.bind("<Return>", self.open_selected)
        self._tree.bind("<KP_Enter>", self.open_selected)

        # Shown over the Table when there is Nothing to List
        self._empty = tk.Label(table_card, text="", font=font(11), fg=MUTED, bg=SURFACE)

        self.refresh()

    # Reload the Register from the File, Keeping the "Show" Choice and the Highlighted Row
    def refresh(self):
        selected = self._tree.selection()
        self._table = self._mom_store.load_records()
        everything = self._table
        shown = self._filtered(everything)

        self._tree.delete(*self._tree.get_children())
        for report in shown.to_dict("records"):
            self._tree.insert("", "end", iid=report[MOM_ID_FIELD], values=self._formatter.mom_table_row_values(report),
                              tags=(self._formatter.mom_row_state(report),))
        if selected and self._tree.exists(selected[0]):
            self._tree.selection_set(selected[0])

        stats = self._formatter.mom_stats(everything)
        for key, value in stats.items():
            self._stat_labels[key].configure(text=str(value))
        self._status.configure(text=f"{self._show_box.get()}  ·  {len(shown)} of {stats['total']} shown")

        if shown.empty:
            self._empty.configure(text="No MOM reportable incidents yet." if everything.empty
                                  else "Nothing to show for this choice.")
            self._empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self._empty.place_forget()

    # The Reports that Match the "Show" Box
    def _filtered(self, table):
        if table.empty or self._show_box.get() == MOM_SHOW_ALL:
            return table
        wanted = self._show_box.get() == MOM_SHOW_REPORTED
        keep = [self._formatter.is_reported(report) == wanted for report in table.to_dict("records")]
        return table[keep]

    # A Click on the Tick Box Cell Ticks or Unticks that Row; a Click Anywhere Else Just Selects it
    def _clicked(self, event):
        if self._tree.identify_region(event.x, event.y) != "cell" or self._tree.identify_column(event.x) != "#1":
            return
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.selection_set(row)
            self._toggle(row)
            return "break"  # Stops Tk from Also Starting its Own Selection

    # "Tick / untick selected" Button and the Space Key
    def toggle_selected(self, event=None):
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo(APP_TITLE, "Select a report in the table first.", parent=self)
            return "break"
        self._toggle(selected[0])
        return "break"

    # Flip the Reported Status of One Report and Save it to the Register File Straight Away
    def _toggle(self, mom_id):
        matches = self._table[self._table[MOM_ID_FIELD] == mom_id]
        if matches.empty:
            self.refresh()
            return
        reported = not self._formatter.is_reported(matches.iloc[0].to_dict())

        saved, message = self._mom_store.set_reported(mom_id, reported)
        if not saved:
            messagebox.showerror(APP_TITLE, f"Could not update the MOM register. {message}", parent=self)
        self.refresh()

    # Open the Double-Clicked or Highlighted Row in its Own Window (a Double-Click on the Headings or Empty Space is Ignored)
    def open_selected(self, event=None):
        if event is not None and event.num == 1:
            if self._tree.identify_region(event.x, event.y) != "cell" or self._tree.identify_column(event.x) == "#1":
                return  # Headings, Empty Space and the Tick Box Column Never Open a Report
        selected = self._tree.selection()
        if not selected or self._table is None:
            return
        matches = self._table[self._table[MOM_ID_FIELD] == selected[0]]
        if not matches.empty:
            ReportWindow(self, self._formatter, matches.iloc[0].to_dict(), "MOM Report")
