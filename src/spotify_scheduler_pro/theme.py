
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

PALETTE = {
    "background": "#090D18",
    "header": "#0D1322",
    "surface": "#121A2B",
    "elevated": "#182238",
    "border": "#293650",
    "text": "#F5F7FB",
    "muted": "#98A4BC",
    "accent": "#7C5CFC",
    "accent_hover": "#9278FF",
    "secondary": "#38D6C7",
    "success": "#32D583",
    "warning": "#F5A524",
    "danger": "#F97066",
    "selection": "#4338A8",
    "console": "#080C16",
}

METRICS = {
    "window_padding": 24,
    "card_padding": 18,
    "control_padding_x": 14,
    "control_padding_y": 9,
    "tree_row_height": 32,
}

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def is_hex_color(value: str) -> bool:
    return bool(_HEX_COLOR.fullmatch(value))


def _relative_luminance(color: str) -> float:
    if not is_hex_color(color):
        raise ValueError(f"Color no válido: {color}")
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def configure_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(background=PALETTE["background"])

    style.configure(
        ".",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        fieldbackground=PALETTE["elevated"],
        bordercolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        troughcolor=PALETTE["background"],
        font=("Segoe UI", 10),
    )

    style.configure("TFrame", background=PALETTE["background"])
    style.configure("App.TFrame", background=PALETTE["background"])
    style.configure("Header.TFrame", background=PALETTE["header"])
    style.configure("Footer.TFrame", background=PALETTE["header"])
    style.configure(
        "Glass.TFrame",
        background=PALETTE["surface"],
        bordercolor=PALETTE["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Hero.TFrame",
        background=PALETTE["elevated"],
        bordercolor=PALETTE["accent"],
        relief="solid",
        borderwidth=1,
    )

    style.configure("TLabel", background=PALETTE["surface"], foreground=PALETTE["text"])
    label_styles = {
        "Wordmark.TLabel": (PALETTE["header"], PALETTE["text"], ("Segoe UI Semibold", 22)),
        "Eyebrow.TLabel": (PALETTE["header"], PALETTE["secondary"], ("Segoe UI Semibold", 8)),
        "Title.TLabel": (PALETTE["background"], PALETTE["text"], ("Segoe UI Semibold", 18)),
        "Subtitle.TLabel": (PALETTE["background"], PALETTE["muted"], ("Segoe UI", 10)),
        "Muted.TLabel": (PALETTE["background"], PALETTE["muted"], ("Segoe UI", 9)),
        "GlassMuted.TLabel": (PALETTE["surface"], PALETTE["muted"], ("Segoe UI", 10)),
        "HeroEyebrow.TLabel": (
            PALETTE["elevated"],
            PALETTE["secondary"],
            ("Segoe UI Semibold", 9),
        ),
        "HeroTitle.TLabel": (
            PALETTE["elevated"],
            PALETTE["text"],
            ("Segoe UI Semibold", 15),
        ),
        "HeroMuted.TLabel": (PALETTE["elevated"], PALETTE["muted"], ("Segoe UI", 10)),
        "Footer.TLabel": (PALETTE["header"], PALETTE["muted"], ("Segoe UI", 9)),
        "StatusGood.TLabel": (
            PALETTE["surface"],
            PALETTE["success"],
            ("Segoe UI Semibold", 11),
        ),
        "StatusWarn.TLabel": (
            PALETTE["surface"],
            PALETTE["warning"],
            ("Segoe UI Semibold", 11),
        ),
    }
    for name, (background, foreground, font) in label_styles.items():
        style.configure(name, background=background, foreground=foreground, font=font)

    chip_styles = {
        "ChipGood.TLabel": ("#173C35", PALETTE["success"]),
        "ChipWarn.TLabel": ("#3B2D1B", PALETTE["warning"]),
        "ChipMuted.TLabel": (PALETTE["elevated"], PALETTE["muted"]),
    }
    for name, (background, foreground) in chip_styles.items():
        style.configure(
            name,
            background=background,
            foreground=foreground,
            padding=(12, 7),
            font=("Segoe UI Semibold", 9),
        )

    style.configure(
        "Glass.TLabelframe",
        background=PALETTE["surface"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Glass.TLabelframe.Label",
        background=PALETTE["surface"],
        foreground=PALETTE["secondary"],
        font=("Segoe UI Semibold", 10),
    )

    padding = (METRICS["control_padding_x"], METRICS["control_padding_y"])
    style.configure(
        "TButton",
        background=PALETTE["elevated"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        padding=padding,
        relief="flat",
        font=("Segoe UI Semibold", 9),
    )
    style.map(
        "TButton",
        background=[
            ("pressed", PALETTE["selection"]),
            ("active", PALETTE["border"]),
            ("disabled", PALETTE["surface"]),
        ],
        foreground=[("disabled", "#5F6A80")],
    )
    style.configure(
        "Primary.TButton",
        background=PALETTE["accent"],
        foreground="#FFFFFF",
        bordercolor=PALETTE["accent"],
        padding=padding,
    )
    style.map(
        "Primary.TButton",
        background=[
            ("pressed", PALETTE["selection"]),
            ("active", PALETTE["accent_hover"]),
            ("disabled", PALETTE["border"]),
        ],
    )
    style.configure(
        "Secondary.TButton",
        background=PALETTE["elevated"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        padding=padding,
    )
    style.configure(
        "Danger.TButton",
        background="#3A2029",
        foreground=PALETTE["danger"],
        bordercolor="#61303E",
        padding=padding,
    )
    style.map("Danger.TButton", background=[("active", "#512A36"), ("pressed", "#2D1820")])

    style.configure(
        "Spoxu.TNotebook",
        background=PALETTE["background"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "Spoxu.TNotebook.Tab",
        background=PALETTE["background"],
        foreground=PALETTE["muted"],
        borderwidth=0,
        padding=(16, 10),
        font=("Segoe UI Semibold", 9),
    )
    style.map(
        "Spoxu.TNotebook.Tab",
        background=[("selected", PALETTE["surface"]), ("active", PALETTE["elevated"])],
        foreground=[("selected", PALETTE["text"]), ("active", PALETTE["text"])],
    )

    style.configure(
        "Treeview",
        background=PALETTE["surface"],
        fieldbackground=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        borderwidth=0,
        rowheight=METRICS["tree_row_height"],
        font=("Segoe UI", 9),
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["selection"])],
        foreground=[("selected", "#FFFFFF")],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["elevated"],
        foreground=PALETTE["muted"],
        bordercolor=PALETTE["border"],
        relief="flat",
        padding=(8, 9),
        font=("Segoe UI Semibold", 9),
    )
    style.map("Treeview.Heading", background=[("active", PALETTE["border"])])

    for widget_style in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            widget_style,
            fieldbackground=PALETTE["elevated"],
            foreground=PALETTE["text"],
            bordercolor=PALETTE["border"],
            lightcolor=PALETTE["border"],
            darkcolor=PALETTE["border"],
            insertcolor=PALETTE["text"],
            padding=(10, 7),
        )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", PALETTE["elevated"]),
            ("disabled", PALETTE["surface"]),
        ],
        foreground=[("readonly", PALETTE["text"]), ("disabled", "#5F6A80")],
        selectbackground=[("readonly", PALETTE["elevated"])],
        selectforeground=[("readonly", PALETTE["text"])],
    )
    for widget_style in ("TCheckbutton", "TRadiobutton"):
        style.configure(
            widget_style,
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            indicatorbackground=PALETTE["elevated"],
            padding=(2, 4),
        )
        style.map(
            widget_style,
            background=[("active", PALETTE["surface"])],
            foreground=[("disabled", "#5F6A80")],
        )
    style.configure(
        "TScrollbar",
        background=PALETTE["elevated"],
        troughcolor=PALETTE["background"],
        bordercolor=PALETTE["background"],
        arrowcolor=PALETTE["muted"],
    )
    return style
