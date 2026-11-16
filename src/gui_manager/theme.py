# Imports

import tkinter as tk
from tkinter import ttk

from src.gui_manager.constants import (
    BG, BORDER, FONT, MUTED, PRIMARY, PRIMARY_DARK, PRIMARY_SOFT, SURFACE, SURFACE_ALT, TEXT,
)

# Class

# Shared look of the app: fonts, styles, window size, cards and badges.
# All methods are static, so it is used as Theme.font(...) without creating a Theme
class Theme:

    # Font in the app's typeface
    @staticmethod
    def font(size=10, weight="normal"):
        return (FONT, size, weight)

    # Set up the styles for every widget ('clam' allows custom colours)
    @staticmethod
    def apply(root):
        style = ttk.Style(root)
        style.theme_use("clam")
        root.configure(bg=BG)
        root.option_add("*TCombobox*Listbox.font", Theme.font(10))
        root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY_SOFT)
        root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

        style.configure(".", background=BG, foreground=TEXT, font=Theme.font(10))
        style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED, font=Theme.font(9, "bold"))

        # Tabs
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(20, 12, 20, 0))
        style.configure("TNotebook.Tab", padding=(20, 9), font=Theme.font(10, "bold"), background=BG,
                        foreground=MUTED, borderwidth=0, lightcolor=BG, bordercolor=BG)
        style.map("TNotebook.Tab", background=[("selected", SURFACE), ("active", "#e8edf5")],
                  foreground=[("selected", PRIMARY)], lightcolor=[("selected", SURFACE)])

        # Buttons
        style.configure("Primary.TButton", background=PRIMARY, foreground="#ffffff", font=Theme.font(10, "bold"),
                        padding=(18, 8), borderwidth=0, focusthickness=0, lightcolor=PRIMARY, darkcolor=PRIMARY)
        style.map("Primary.TButton",
                  background=[("disabled", "#a5bff5"), ("pressed", PRIMARY_DARK), ("active", PRIMARY_DARK)],
                  lightcolor=[("active", PRIMARY_DARK)], darkcolor=[("active", PRIMARY_DARK)],
                  foreground=[("disabled", "#ffffff")])
        style.configure("Secondary.TButton", background=SURFACE, foreground=TEXT, font=Theme.font(10),
                        padding=(14, 8), bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
                        borderwidth=1, focusthickness=0)
        style.map("Secondary.TButton", background=[("pressed", "#e2e8f0"), ("active", "#eef2f7")])

        # Text boxes and drop-downs
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

        # Tables
        style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                        rowheight=34, font=Theme.font(10), borderwidth=0, relief="flat")
        style.configure("Treeview.Heading", background=SURFACE_ALT, foreground=MUTED, font=Theme.font(9, "bold"),
                        relief="flat", padding=(10, 9), borderwidth=0, lightcolor=BORDER, darkcolor=BORDER)
        style.map("Treeview.Heading", background=[("active", "#eef2f7")])
        style.map("Treeview", background=[("selected", PRIMARY_SOFT)], foreground=[("selected", TEXT)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # No border

        # Scrollbars
        style.configure("Vertical.TScrollbar", background="#cbd5e1", troughcolor=BG, bordercolor=BG,
                        arrowcolor=MUTED, lightcolor="#cbd5e1", darkcolor="#cbd5e1", gripcount=0)
        style.map("Vertical.TScrollbar", background=[("active", "#94a3b8")])

    # Size and centre a window, scaled for the screen
    @staticmethod
    def fit_window(window, width, height):
        scale = window.winfo_fpixels("1i") / 96  # 1.0 at 100% scaling, 1.5 at 150%
        width = min(int(width * scale), int(window.winfo_screenwidth() * 0.9))
        height = min(int(height * scale), int(window.winfo_screenheight() * 0.85))
        x = (window.winfo_screenwidth() - width) // 2
        y = max((window.winfo_screenheight() - height) // 3, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(int(width * 0.75), int(height * 0.75))
        return scale

    # White box with a thin border
    @staticmethod
    def card(parent, **pack_options):
        frame = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
        if pack_options:
            frame.pack(**pack_options)
        return frame

    # Small coloured label, e.g. for the score or severity
    @staticmethod
    def badge(parent, text, colour, background):
        return tk.Label(parent, text=text, fg=colour, bg=background, font=Theme.font(9, "bold"), padx=10, pady=3)
