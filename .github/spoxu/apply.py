
from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def method(source: str) -> str:
    return textwrap.indent(textwrap.dedent(source).strip(), "    ")


def replace_method(text: str, name: str, source: str) -> str:
    pattern = re.compile(
        rf"^    def {re.escape(name)}\b.*?(?=^    def |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(method(source) + "\n\n", text, count=1)
    if count != 1:
        raise RuntimeError(f"method {name}: expected one match, found {count}")
    return updated


write(
    "src/spotify_scheduler_pro/branding.py",
    """
from __future__ import annotations

DISPLAY_NAME = "Spoxu"
VERSION = "0.2.0"
TAGLINE = "Automatización musical"
WINDOW_TITLE = f"{DISPLAY_NAME} · {TAGLINE}"
EXECUTABLE_NAME = "Spoxu"
ARTIFACT_NAME = "Spoxu-Windows"
TECHNICAL_PACKAGE = "spotify_scheduler_pro"

# Stable compatibility identifiers. They deliberately keep their historical
# values so an upgrade continues to see existing schedules and credentials.
LEGACY_DATA_DIR_NAME = "SpotifySchedulerPro"
LEGACY_KEYRING_SERVICE = "SpotifySchedulerPro"
LEGACY_OAUTH_SERVICE = "SpotifySchedulerProOAuth"
LEGACY_AUTOSTART_NAME = "SpotifySchedulerPro"
PLAYLIST_EXPORT_FORMAT = "spotify-scheduler-pro-playlist-v1"
""",
)

write(
    "src/spotify_scheduler_pro/theme.py",
    """
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
""",
)


main_path = "src/spotify_scheduler_pro/gui/main_window.py"
main = read(main_path)
main = replace_once(
    main,
    "from ..autostart import set_start_with_windows\n",
    (
        "from ..autostart import set_start_with_windows\n"
        "from ..branding import DISPLAY_NAME, TAGLINE, VERSION, WINDOW_TITLE\n"
    ),
    label="main branding import",
)
main = replace_once(
    main,
    "from ..tray import TrayController\n",
    "from ..theme import PALETTE, configure_theme\nfrom ..tray import TrayController\n",
    label="main theme import",
)

main = replace_method(
    main,
    "_configure_root",
    """
def _configure_root(self) -> None:
    self.root.title(WINDOW_TITLE)
    self.root.geometry("1240x800")
    self.root.minsize(1040, 700)
    self.root.configure(background=PALETTE["background"])
    self.root.option_add("*Font", "Segoe UI 10")
    self.root.protocol("WM_DELETE_WINDOW", self.on_close_requested)
""",
)
main = replace_method(
    main,
    "_build_style",
    """
def _build_style(self) -> None:
    self.style = configure_theme(self.root)
""",
)
main = replace_method(
    main,
    "_build_menu",
    """
def _build_menu(self) -> None:
    menu_options = {
        "background": PALETTE["surface"],
        "foreground": PALETTE["text"],
        "activebackground": PALETTE["accent"],
        "activeforeground": "#FFFFFF",
        "activeborderwidth": 0,
        "borderwidth": 0,
    }
    menu = tk.Menu(self.root, **menu_options)

    app_menu = tk.Menu(menu, tearoff=False, **menu_options)
    app_menu.add_command(label="Mostrar carpeta de datos", command=self.open_data_folder)
    app_menu.add_command(label="Actualizar datos", command=self.refresh_everything)
    app_menu.add_separator()
    app_menu.add_command(label="Salir", command=self.exit)
    menu.add_cascade(label=DISPLAY_NAME, menu=app_menu)

    automation_menu = tk.Menu(menu, tearoff=False, **menu_options)
    automation_menu.add_command(
        label="Pausar/Reanudar automatización",
        command=self.toggle_automation,
    )
    automation_menu.add_command(label="Pausar reproducción", command=self.manual_pause)
    automation_menu.add_command(
        label="Limpiar playlists temporales antiguas",
        command=self.cleanup_temporary_playlists,
    )
    menu.add_cascade(label="Automatización", menu=automation_menu)

    help_menu = tk.Menu(menu, tearoff=False, **menu_options)
    help_menu.add_command(label="Acerca de Spoxu", command=self.show_about)
    menu.add_cascade(label="Ayuda", menu=help_menu)
    self.root.configure(menu=menu)
""",
)
main = replace_method(
    main,
    "_build_layout",
    """
def _build_layout(self) -> None:
    header = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 17))
    header.pack(fill="x")

    brand = ttk.Frame(header, style="Header.TFrame")
    brand.pack(side="left")
    ttk.Label(brand, text=DISPLAY_NAME.upper(), style="Wordmark.TLabel").pack(anchor="w")
    ttk.Label(brand, text=TAGLINE.upper(), style="Eyebrow.TLabel").pack(anchor="w")

    status = ttk.Frame(header, style="Header.TFrame")
    status.pack(side="right")
    self.connection_var = tk.StringVar(value="Spotify · desconectado")
    self.connection_label = ttk.Label(
        status,
        textvariable=self.connection_var,
        style="ChipMuted.TLabel",
    )
    self.connection_label.pack(side="right", padx=(8, 0))

    self.automation_var = tk.StringVar(value="Automatización · iniciando")
    self.automation_label = ttk.Label(
        status,
        textvariable=self.automation_var,
        style="ChipWarn.TLabel",
    )
    self.automation_label.pack(side="right")

    self.notebook = ttk.Notebook(self.root, style="Spoxu.TNotebook")
    self.notebook.pack(fill="both", expand=True, padx=20, pady=(14, 12))

    self.dashboard_tab = ttk.Frame(self.notebook, style="App.TFrame")
    self.schedule_tab = ttk.Frame(self.notebook, style="App.TFrame")
    self.settings_tab = ttk.Frame(self.notebook, style="App.TFrame")
    self.history_tab = ttk.Frame(self.notebook, style="App.TFrame")
    self.transfer_tab = ttk.Frame(self.notebook, style="App.TFrame")
    self.logs_tab = ttk.Frame(self.notebook, style="App.TFrame")

    self.notebook.add(self.dashboard_tab, text="Inicio")
    self.notebook.add(self.schedule_tab, text="Horarios")
    self.notebook.add(self.settings_tab, text="Conexión")
    self.notebook.add(self.history_tab, text="Actividad")
    self.notebook.add(self.transfer_tab, text="Playlists")
    self.notebook.add(self.logs_tab, text="Sistema")

    self._build_dashboard_tab()
    self._build_schedule_tab()
    self._build_settings_tab()
    self._build_history_tab()
    self._build_transfer_tab()
    self._build_logs_tab()

    footer = ttk.Frame(self.root, style="Footer.TFrame", padding=(20, 8))
    footer.pack(fill="x")
    self.footer_var = tk.StringVar(value="Listo.")
    ttk.Label(footer, textvariable=self.footer_var, style="Footer.TLabel").pack(side="left")
    ttk.Label(
        footer,
        text=f"DATOS LOCALES · {self.paths.root}",
        style="Footer.TLabel",
    ).pack(side="right")
""",
)
main = replace_method(
    main,
    "_build_dashboard_tab",
    """
def _build_dashboard_tab(self) -> None:
    container = ttk.Frame(self.dashboard_tab, style="App.TFrame", padding=20)
    container.pack(fill="both", expand=True)
    container.columnconfigure(0, weight=1)
    container.columnconfigure(1, weight=1)
    container.rowconfigure(1, weight=1)

    hero = ttk.Frame(container, style="Hero.TFrame", padding=20)
    hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    ttk.Label(
        hero,
        text="ESTADO EN TIEMPO REAL",
        style="HeroEyebrow.TLabel",
    ).pack(anchor="w")

    self.dashboard_status_var = tk.StringVar(value="Iniciando…")
    ttk.Label(
        hero,
        textvariable=self.dashboard_status_var,
        style="HeroTitle.TLabel",
        wraplength=1040,
    ).pack(anchor="w", pady=(7, 0))

    self.next_schedule_var = tk.StringVar(value="")
    ttk.Label(
        hero,
        textvariable=self.next_schedule_var,
        style="HeroMuted.TLabel",
        wraplength=1040,
    ).pack(anchor="w", pady=(7, 0))

    playback_card = ttk.LabelFrame(
        container,
        text=" REPRODUCCIÓN ACTUAL ",
        padding=18,
        style="Glass.TLabelframe",
    )
    playback_card.grid(row=1, column=0, sticky="nsew", padx=(0, 7))
    self.now_playing_var = tk.StringVar(value="Sin datos.")
    ttk.Label(
        playback_card,
        textvariable=self.now_playing_var,
        justify="left",
        wraplength=500,
        font=("Segoe UI", 11),
    ).pack(anchor="nw", fill="both", expand=True)

    device_card = ttk.LabelFrame(
        container,
        text=" DISPOSITIVOS ",
        padding=18,
        style="Glass.TLabelframe",
    )
    device_card.grid(row=1, column=1, sticky="nsew", padx=(7, 0))
    self.device_listbox = tk.Listbox(
        device_card,
        height=12,
        activestyle="none",
        font=("Segoe UI", 10),
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        selectbackground=PALETTE["selection"],
        selectforeground="#FFFFFF",
        highlightbackground=PALETTE["border"],
        highlightcolor=PALETTE["accent"],
        highlightthickness=1,
        borderwidth=0,
        relief="flat",
    )
    self.device_listbox.pack(fill="both", expand=True)

    controls = ttk.Frame(container, style="App.TFrame")
    controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
    ttk.Button(
        controls,
        text="Actualizar Spotify",
        command=self.refresh_spotify_data,
        style="Primary.TButton",
    ).pack(side="left")
    ttk.Button(
        controls,
        text="Pausar/Reanudar automatización",
        command=self.toggle_automation,
        style="Secondary.TButton",
    ).pack(side="left", padx=8)
    ttk.Button(
        controls,
        text="Pausar música",
        command=self.manual_pause,
        style="Secondary.TButton",
    ).pack(side="left")
    ttk.Button(
        controls,
        text="Ocultar en bandeja",
        command=self.hide_to_tray,
        style="Secondary.TButton",
    ).pack(side="right")
""",
)
main = replace_method(
    main,
    "_build_schedule_tab",
    """
def _build_schedule_tab(self) -> None:
    container = ttk.Frame(self.schedule_tab, style="App.TFrame", padding=16)
    container.pack(fill="both", expand=True)
    container.rowconfigure(1, weight=1)
    container.columnconfigure(0, weight=1)

    heading = ttk.Frame(container, style="App.TFrame")
    heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    ttk.Label(heading, text="Rutinas programadas", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        heading,
        text="Define qué debe sonar, cuándo y en qué dispositivo.",
        style="Subtitle.TLabel",
    ).pack(anchor="w", pady=(3, 0))

    columns = (
        "enabled",
        "name",
        "kind",
        "when",
        "start",
        "end",
        "playlist",
        "device",
        "random",
        "priority",
    )
    self.schedule_tree = ttk.Treeview(
        container,
        columns=columns,
        show="headings",
        selectmode="browse",
    )
    headings = {
        "enabled": "Activo",
        "name": "Nombre",
        "kind": "Tipo",
        "when": "Día/Fecha",
        "start": "Inicio",
        "end": "Fin",
        "playlist": "Playlist",
        "device": "Dispositivo",
        "random": "Aleatorio",
        "priority": "Prioridad",
    }
    widths = {
        "enabled": 55,
        "name": 150,
        "kind": 90,
        "when": 110,
        "start": 80,
        "end": 80,
        "playlist": 240,
        "device": 150,
        "random": 75,
        "priority": 70,
    }
    for column in columns:
        self.schedule_tree.heading(column, text=headings[column])
        self.schedule_tree.column(column, width=widths[column], anchor="center")

    scrollbar = ttk.Scrollbar(
        container,
        orient="vertical",
        command=self.schedule_tree.yview,
    )
    self.schedule_tree.configure(yscrollcommand=scrollbar.set)
    self.schedule_tree.grid(row=1, column=0, sticky="nsew")
    scrollbar.grid(row=1, column=1, sticky="ns")
    self.schedule_tree.bind("<Double-1>", lambda _event: self.edit_schedule())

    buttons = ttk.Frame(container, style="App.TFrame")
    buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
    ttk.Button(
        buttons,
        text="Nuevo horario",
        command=self.add_schedule,
        style="Primary.TButton",
    ).pack(side="left")
    ttk.Button(
        buttons,
        text="Editar",
        command=self.edit_schedule,
        style="Secondary.TButton",
    ).pack(side="left", padx=6)
    ttk.Button(
        buttons,
        text="Eliminar",
        command=self.delete_schedule,
        style="Danger.TButton",
    ).pack(side="left")
    ttk.Button(
        buttons,
        text="Habilitar/Deshabilitar",
        command=self.toggle_schedule,
        style="Secondary.TButton",
    ).pack(side="left", padx=6)
    ttk.Button(
        buttons,
        text="Probar ahora",
        command=self.test_schedule_now,
        style="Secondary.TButton",
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        buttons,
        text="Actualizar",
        command=self.refresh_schedules,
        style="Secondary.TButton",
    ).pack(side="right")

    self.schedule_info_var = tk.StringVar(value="")
    ttk.Label(
        container,
        textvariable=self.schedule_info_var,
        style="Muted.TLabel",
        wraplength=1000,
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
""",
)

main = replace_method(
    main,
    "_build_history_tab",
    """
def _build_history_tab(self) -> None:
    notebook = ttk.Notebook(self.history_tab, style="Spoxu.TNotebook")
    notebook.pack(fill="both", expand=True, padx=12, pady=12)

    recent_frame = ttk.Frame(notebook, style="App.TFrame", padding=10)
    local_frame = ttk.Frame(notebook, style="App.TFrame", padding=10)
    notebook.add(recent_frame, text="Spotify · canciones recientes")
    notebook.add(local_frame, text="Eventos de automatización")

    recent_columns = ("played_at", "title", "artist", "explicit")
    self.recent_tree = ttk.Treeview(
        recent_frame,
        columns=recent_columns,
        show="headings",
    )
    for column, title, width in [
        ("played_at", "Fecha/hora", 190),
        ("title", "Canción", 340),
        ("artist", "Artista", 280),
        ("explicit", "Explícita", 80),
    ]:
        self.recent_tree.heading(column, text=title)
        self.recent_tree.column(column, width=width)
    self.recent_tree.pack(fill="both", expand=True)
    ttk.Button(
        recent_frame,
        text="Actualizar",
        command=self.refresh_recent_tracks,
        style="Secondary.TButton",
    ).pack(anchor="e", pady=(8, 0))

    event_columns = ("timestamp", "type", "schedule", "playlist", "device", "details")
    self.events_tree = ttk.Treeview(
        local_frame,
        columns=event_columns,
        show="headings",
    )
    for column, title, width in [
        ("timestamp", "Fecha/hora", 170),
        ("type", "Evento", 150),
        ("schedule", "Horario ID", 80),
        ("playlist", "Playlist", 260),
        ("device", "Dispositivo", 150),
        ("details", "Detalles", 260),
    ]:
        self.events_tree.heading(column, text=title)
        self.events_tree.column(column, width=width)
    self.events_tree.pack(fill="both", expand=True)
    ttk.Button(
        local_frame,
        text="Actualizar",
        command=self.refresh_local_events,
        style="Secondary.TButton",
    ).pack(anchor="e", pady=(8, 0))
""",
)
main = replace_method(
    main,
    "_build_transfer_tab",
    """
def _build_transfer_tab(self) -> None:
    container = ttk.Frame(self.transfer_tab, style="App.TFrame", padding=24)
    container.pack(fill="both", expand=True)

    card = ttk.Frame(container, style="Glass.TFrame", padding=24)
    card.pack(fill="x")
    ttk.Label(card, text="Biblioteca portátil", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        card,
        text=(
            "Exporta una playlist a JSON con sus canciones y, cuando sea posible, "
            "su portada. También puedes importar archivos compatibles."
        ),
        style="GlassMuted.TLabel",
        wraplength=900,
    ).pack(anchor="w", pady=(8, 22))

    self.transfer_playlist_var = tk.StringVar()
    self.transfer_playlist_combo = ttk.Combobox(
        card,
        textvariable=self.transfer_playlist_var,
        width=90,
    )
    self.transfer_playlist_combo.pack(fill="x")

    buttons = ttk.Frame(card, style="Glass.TFrame")
    buttons.pack(fill="x", pady=16)
    ttk.Button(
        buttons,
        text="Exportar playlist",
        command=self.export_playlist,
        style="Primary.TButton",
    ).pack(side="left")
    ttk.Button(
        buttons,
        text="Importar desde JSON",
        command=self.import_playlist,
        style="Secondary.TButton",
    ).pack(side="left", padx=8)
    ttk.Button(
        buttons,
        text="Actualizar lista",
        command=self.refresh_spotify_data,
        style="Secondary.TButton",
    ).pack(side="left")

    self.transfer_status_var = tk.StringVar(value="")
    ttk.Label(
        card,
        textvariable=self.transfer_status_var,
        style="GlassMuted.TLabel",
        wraplength=900,
    ).pack(anchor="w", pady=(8, 0))
""",
)
main = replace_method(
    main,
    "_build_logs_tab",
    """
def _build_logs_tab(self) -> None:
    container = ttk.Frame(self.logs_tab, style="App.TFrame", padding=12)
    container.pack(fill="both", expand=True)
    self.log_text = tk.Text(
        container,
        wrap="none",
        font=("Consolas", 9),
        state="disabled",
        background=PALETTE["console"],
        foreground=PALETTE["text"],
        insertbackground=PALETTE["text"],
        selectbackground=PALETTE["selection"],
        selectforeground="#FFFFFF",
        highlightbackground=PALETTE["border"],
        highlightcolor=PALETTE["accent"],
        highlightthickness=1,
        borderwidth=0,
        relief="flat",
    )
    y_scroll = ttk.Scrollbar(container, orient="vertical", command=self.log_text.yview)
    x_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.log_text.xview)
    self.log_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    self.log_text.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)

    controls = ttk.Frame(container, style="App.TFrame")
    controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Button(
        controls,
        text="Actualizar",
        command=self.refresh_log,
        style="Primary.TButton",
    ).pack(side="left")
    ttk.Button(
        controls,
        text="Abrir carpeta de logs",
        command=self.open_logs_folder,
        style="Secondary.TButton",
    ).pack(side="left", padx=8)
""",
)
main = replace_method(
    main,
    "_apply_controller_status",
    """
def _apply_controller_status(
    self,
    message: str,
    _payload: dict[str, Any] | None,
) -> None:
    self.dashboard_status_var.set(message)
    paused = self.controller.paused
    self.automation_var.set(
        "Automatización · pausada" if paused else "Automatización · activa"
    )
    self.automation_label.configure(
        style="ChipWarn.TLabel" if paused else "ChipGood.TLabel"
    )
""",
)
main = replace_method(
    main,
    "_set_connection_status",
    """
def _set_connection_status(self, text: str) -> None:
    self.connection_var.set(text.replace("Spotify:", "Spotify ·"))
    self.connection_label.configure(
        style="ChipGood.TLabel" if self.spotify.connected else "ChipMuted.TLabel"
    )
""",
)
main = replace_method(
    main,
    "show_about",
    """
def show_about(self) -> None:
    messagebox.showinfo(
        f"Acerca de {DISPLAY_NAME}",
        f"{DISPLAY_NAME} {VERSION}\\n{TAGLINE}\\n\\n"
        "Diseño glass oscuro y motor modular de automatización.\\n"
        "Inspirado en spotify-scheduler de Szymon Andrzejewski.\\n"
        "Licencia MIT. Proyecto independiente, no afiliado con Spotify.\\n\\n"
        "Requiere Spotify Premium y un dispositivo Spotify Connect.",
    )
""",
)
main = replace_once(
    main,
    'canvas = tk.Canvas(self.settings_tab, highlightthickness=0)',
    (
        'canvas = tk.Canvas(\n'
        '            self.settings_tab,\n'
        '            highlightthickness=0,\n'
        '            background=PALETTE["background"],\n'
        '        )'
    ),
    label="settings canvas",
)
main = replace_once(
    main,
    "frame = ttk.Frame(canvas, padding=20)",
    'frame = ttk.Frame(canvas, padding=20, style="App.TFrame")',
    label="settings frame",
)
for variable in ("credentials", "playback", "behavior"):
    main = replace_once(
        main,
        f'{variable} = ttk.LabelFrame(frame, text=',
        f'{variable} = ttk.LabelFrame(frame, style="Glass.TLabelframe", text=',
        label=f"settings {variable} card",
    )
main = main.replace('foreground="#666666",', 'style="GlassMuted.TLabel",')
write(main_path, main)

dialogs_path = "src/spotify_scheduler_pro/gui/dialogs.py"
dialogs = read(dialogs_path)
dialogs = replace_once(
    dialogs,
    "from ..models import ScheduleEntry, ScheduleKind, SpotifyDevice, SpotifyPlaylist\n",
    (
        "from ..branding import DISPLAY_NAME\n"
        "from ..models import ScheduleEntry, ScheduleKind, SpotifyDevice, SpotifyPlaylist\n"
    ),
    label="dialogs branding import",
)
dialogs = replace_once(
    dialogs,
    "from ..scheduler import DAY_NAMES_ES, parse_date, parse_time\n",
    "from ..scheduler import DAY_NAMES_ES, parse_date, parse_time\nfrom ..theme import PALETTE\n",
    label="dialogs theme import",
)
dialogs = replace_once(
    dialogs,
    'self.title("Editar horario" if entry else "Nuevo horario")',
    (
        'self.title(\n'
        '            f"{DISPLAY_NAME} · Editar horario"\n'
        '            if entry\n'
        '            else f"{DISPLAY_NAME} · Nuevo horario"\n'
        '        )'
    ),
    label="dialogs title",
)
dialogs = replace_once(
    dialogs,
    'self.geometry("720x650")\n        self.minsize(650, 600)',
    (
        'self.geometry("740x680")\n'
        '        self.minsize(680, 620)\n'
        '        self.configure(background=PALETTE["background"])'
    ),
    label="dialogs geometry",
)
dialogs = replace_once(
    dialogs,
    'self.protocol("WM_DELETE_WINDOW", self.destroy)\n        self.wait_visibility()',
    (
        'self.protocol("WM_DELETE_WINDOW", self.destroy)\n'
        '        self.bind("<Escape>", lambda _event: self.destroy())\n'
        '        self.bind("<Control-Return>", lambda _event: self._save())\n'
        '        self.wait_visibility()'
    ),
    label="dialogs bindings",
)
dialogs = replace_once(
    dialogs,
    'container = ttk.Frame(self, padding=18)\n        container.pack(fill="both", expand=True)',
    (
        'container = ttk.Frame(self, padding=18, style="Glass.TFrame")\n'
        '        container.pack(fill="both", expand=True, padx=18, pady=18)'
    ),
    label="dialogs container",
)
dialogs = dialogs.replace(
    "type_frame = ttk.Frame(container)",
    'type_frame = ttk.Frame(container, style="Glass.TFrame")',
)
dialogs = dialogs.replace('foreground="#666666",', 'style="GlassMuted.TLabel",')
dialogs = replace_once(
    dialogs,
    'options = ttk.LabelFrame(container, text="Opciones", padding=12)',
    (
        'options = ttk.LabelFrame(\n'
        '            container,\n'
        '            text="Opciones",\n'
        '            padding=12,\n'
        '            style="Glass.TLabelframe",\n'
        '        )'
    ),
    label="dialogs options",
)
dialogs = replace_once(
    dialogs,
    "buttons = ttk.Frame(container)",
    'buttons = ttk.Frame(container, style="Glass.TFrame")',
    label="dialogs buttons frame",
)
dialogs = replace_once(
    dialogs,
    'ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")',
    (
        'ttk.Button(\n'
        '            buttons,\n'
        '            text="Cancelar",\n'
        '            command=self.destroy,\n'
        '            style="Secondary.TButton",\n'
        '        ).pack(side="right")'
    ),
    label="dialogs cancel",
)
dialogs = replace_once(
    dialogs,
    'ttk.Button(buttons, text="Guardar", command=self._save).pack(side="right", padx=(0, 10))',
    (
        'ttk.Button(\n'
        '            buttons,\n'
        '            text="Guardar horario",\n'
        '            command=self._save,\n'
        '            style="Primary.TButton",\n'
        '        ).pack(side="right", padx=(0, 10))'
    ),
    label="dialogs save",
)
write(dialogs_path, dialogs)

write(
    "src/spotify_scheduler_pro/tray.py",
    """
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PIL import Image, ImageDraw

from .branding import DISPLAY_NAME

LOGGER = logging.getLogger("spotify_scheduler_pro.tray")


def _make_icon() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (5, 5, 59, 59),
        radius=17,
        fill=(18, 26, 43, 255),
        outline=(124, 92, 252, 255),
        width=3,
    )
    draw.arc((16, 14, 48, 36), start=190, end=350, fill=(56, 214, 199, 255), width=5)
    draw.arc((16, 28, 48, 50), start=10, end=170, fill=(124, 92, 252, 255), width=5)
    draw.ellipse((42, 17, 48, 23), fill=(56, 214, 199, 255))
    draw.ellipse((16, 41, 22, 47), fill=(124, 92, 252, 255))
    return image


class TrayController:
    def __init__(
        self,
        show_callback: Callable[[], None],
        pause_callback: Callable[[], bool],
        exit_callback: Callable[[], None],
    ):
        self.show_callback = show_callback
        self.pause_callback = pause_callback
        self.exit_callback = exit_callback
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        try:
            import pystray
        except ImportError:
            LOGGER.warning("pystray no está instalado; bandeja deshabilitada.")
            return

        def show(_icon=None, _item=None):
            self.show_callback()

        def pause(_icon=None, _item=None):
            paused = self.pause_callback()
            if self._icon:
                self._icon.title = (
                    f"{DISPLAY_NAME} · Pausado"
                    if paused
                    else f"{DISPLAY_NAME} · Activo"
                )

        def quit_app(_icon=None, _item=None):
            self.exit_callback()

        self._icon = pystray.Icon(
            DISPLAY_NAME,
            _make_icon(),
            DISPLAY_NAME,
            menu=pystray.Menu(
                pystray.MenuItem(f"Abrir {DISPLAY_NAME}", show, default=True),
                pystray.MenuItem("Pausar/Reanudar automatización", pause),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", quit_app),
            ),
        )
        self._thread = threading.Thread(
            target=self._icon.run,
            name="TrayIcon",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                LOGGER.exception("No se pudo detener el icono de bandeja.")
            self._icon = None
""",
)

autostart_path = "src/spotify_scheduler_pro/autostart.py"
autostart = read(autostart_path)
autostart = replace_once(
    autostart,
    'from pathlib import Path\n\nAPP_NAME = "SpotifySchedulerPro"\n',
    (
        "from pathlib import Path\n\n"
        "from .branding import LEGACY_AUTOSTART_NAME\n\n"
        "APP_NAME = LEGACY_AUTOSTART_NAME\n"
    ),
    label="autostart compatibility constant",
)
write(autostart_path, autostart)

config_path = "src/spotify_scheduler_pro/config.py"
config = read(config_path)
config = replace_once(
    config,
    'from keyring.errors import KeyringError\n\nSERVICE_NAME = "SpotifySchedulerPro"\n',
    (
        "from keyring.errors import KeyringError\n\n"
        "from .branding import LEGACY_KEYRING_SERVICE\n\n"
        "SERVICE_NAME = LEGACY_KEYRING_SERVICE\n"
    ),
    label="config compatibility constant",
)
write(config_path, config)

paths_path = "src/spotify_scheduler_pro/paths.py"
paths = read(paths_path)
paths = replace_once(
    paths,
    "from platformdirs import user_data_path\n",
    "from platformdirs import user_data_path\n\nfrom .branding import LEGACY_DATA_DIR_NAME\n",
    label="paths branding import",
)
paths = replace_once(
    paths,
    'user_data_path("SpotifySchedulerPro", appauthor=False, ensure_exists=True)',
    "user_data_path(LEGACY_DATA_DIR_NAME, appauthor=False, ensure_exists=True)",
    label="paths compatibility id",
)
write(paths_path, paths)

spotify_path = "src/spotify_scheduler_pro/spotify_client.py"
spotify = read(spotify_path)
spotify = replace_once(
    spotify,
    "from .config import AppConfig, ConfigManager\n",
    (
        "from .branding import (\n"
        "    DISPLAY_NAME,\n"
        "    LEGACY_OAUTH_SERVICE,\n"
        "    PLAYLIST_EXPORT_FORMAT,\n"
        ")\n"
        "from .config import AppConfig, ConfigManager\n"
    ),
    label="spotify branding import",
)
spotify = replace_once(
    spotify,
    'SERVICE_NAME = "SpotifySchedulerProOAuth"',
    "SERVICE_NAME = LEGACY_OAUTH_SERVICE",
    label="spotify oauth compatibility id",
)
spotify = spotify.replace(
    'description="Generada automáticamente por Spotify Scheduler Pro."',
    'description=f"Generada automáticamente por {DISPLAY_NAME}."',
)
spotify = spotify.replace(
    '"format": "spotify-scheduler-pro-playlist-v1"',
    '"format": PLAYLIST_EXPORT_FORMAT',
)
spotify = spotify.replace(
    'if payload.get("format") != "spotify-scheduler-pro-playlist-v1":',
    'if payload.get("format") != PLAYLIST_EXPORT_FORMAT:',
)
spotify = spotify.replace(
    'raise ValueError("El archivo no pertenece al formato Spotify Scheduler Pro.")',
    'raise ValueError(f"El archivo no pertenece al formato compatible de {DISPLAY_NAME}.")',
)
spotify = spotify.replace(
    'description=f"Importada por Spotify Scheduler Pro el {datetime.now():%Y-%m-%d}."',
    'description=f"Importada por {DISPLAY_NAME} el {datetime.now():%Y-%m-%d}."',
)
write(spotify_path, spotify)

write(
    "src/spotify_scheduler_pro/__init__.py",
    """
\"\"\"Spoxu automation engine.\"\"\"

from .branding import VERSION as __version__

__all__ = ["__version__"]
""",
)

main_entry_path = "src/spotify_scheduler_pro/__main__.py"
main_entry = read(main_entry_path)
main_entry = replace_once(
    main_entry,
    'parser = argparse.ArgumentParser(description="Spotify Scheduler Pro")',
    'parser = argparse.ArgumentParser(description="Spoxu · Automatización musical")',
    label="cli branding",
)
write(main_entry_path, main_entry)

write(
    "pyproject.toml",
    """
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "spoxu"
version = "0.2.0"
description = "Spoxu automates Spotify playback with schedules, safe local storage, and a glass-inspired desktop interface."
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
  {name = "Szymon Andrzejewski"},
  {name = "Spoxu contributors"}
]
dependencies = [
  "spotipy>=2.26.0",
  "psutil>=6.0.0",
  "Pillow>=10.0.0",
  "platformdirs>=4.0.0",
  "keyring>=25.0.0",
  "pystray>=0.19.5",
  "requests>=2.31.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "ruff>=0.8.0",
  "pyinstaller>=6.0.0"
]

[project.scripts]
spoxu = "spotify_scheduler_pro.__main__:main"
spotify-scheduler-pro = "spotify_scheduler_pro.__main__:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
""",
)

write(
    "build_exe.ps1",
    r"""
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "Spoxu" `
  --collect-all keyring `
  --collect-all pystray `
  --collect-all spotipy `
  --paths "src" `
  "src\spotify_scheduler_pro\__main__.py"

Write-Host ""
Write-Host "EXE generado en: dist\Spoxu\Spoxu.exe"
""",
)

write(
    "README.md",
    r"""
# Spoxu

**Automatización musical para espacios que no pueden detenerse.**

Spoxu es una aplicación de escritorio para programar y controlar la reproducción
de Spotify en restaurantes, centros educativos, oficinas y otros espacios. Su
interfaz oscura, minimalista y de inspiración glass concentra horarios,
dispositivos, actividad y playlists sin obligarte a cambiar música manualmente.

> Spoxu es un proyecto independiente y no está afiliado, patrocinado ni respaldado por Spotify.

## Qué incluye

- Horarios semanales y por fecha específica.
- Ventanas nocturnas como `22:00–02:00`.
- Prioridades y detección precisa de conflictos.
- Pausa automática fuera del horario.
- Selección de dispositivos Spotify Connect y prueba inmediata de playlists.
- Random Queue con menos repeticiones, separación de artistas y exclusión de
  canciones recientes.
- Filtro opcional de canciones explícitas.
- Importación y exportación de playlists.
- Historial local, logs rotativos y almacenamiento SQLite.
- Credenciales y tokens en el almacén seguro del sistema.
- Bandeja, autoinicio de Windows y prevención opcional de suspensión.
- Pruebas automatizadas y construcción reproducible del EXE en GitHub Actions.

## Diseño Spoxu

La interfaz usa una estética glass oscura basada en superficies profundas,
bordes sutiles, acentos violeta/cian y estados de alto contraste. Tkinter no
ofrece blur nativo por widget; Spoxu evita transparencias que reduzcan la
legibilidad y reproduce el lenguaje glass mediante jerarquía, color y espacio.

## Requisitos

- Windows 10 u 11 recomendado.
- Python 3.11 o superior para ejecutar desde código.
- Una cuenta Spotify Premium.
- Una aplicación creada en Spotify Developer Dashboard.
- Al menos un dispositivo Spotify Connect disponible.

## Configuración de Spotify

1. Crea una aplicación en Spotify Developer Dashboard.
2. Registra exactamente esta Redirect URI:

```text
http://127.0.0.1:23918
```

3. Abre Spoxu y entra en **Conexión**.
4. Pega el Client ID, el Client Secret y la Redirect URI.
5. Pulsa **Guardar y autorizar**.
6. Completa el inicio de sesión en el navegador.

El Client Secret y los tokens OAuth no se guardan en `config.json`; se almacenan
mediante `keyring`.

## Ejecutar desde código

```powershell
git clone <URL_DE_TU_FORK>
cd spotify-scheduler
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
spoxu
```

El alias técnico anterior sigue disponible para compatibilidad:

```powershell
python -m spotify_scheduler_pro
```

## Construir el EXE

```powershell
.\build_exe.ps1
```

El resultado es `dist\Spoxu\Spoxu.exe`. También puedes ejecutar manualmente el
workflow **Build Windows EXE** y descargar el artefacto `Spoxu-Windows`.

## Datos locales y compatibilidad

Para que una actualización no pierda horarios, configuración ni credenciales,
la versión 0.2 mantiene los identificadores internos heredados. La carpeta de
datos continúa siendo:

- Windows: `%LOCALAPPDATA%\SpotifySchedulerPro`
- Linux: `~/.local/share/SpotifySchedulerPro`
- macOS: `~/Library/Application Support/SpotifySchedulerPro`

Allí se almacenan `scheduler.db`, `config.json` y `logs/app.log`.

## Verificación

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

CI ejecuta estos controles en cada push y pull request.

## Uso responsable

Spotify no permite el uso público o comercial de su servicio. Cada usuario debe
cumplir los términos, las políticas de desarrolladores, las licencias y las
normas aplicables de Spotify. Este software se distribuye para uso personal y no
comercial.

## Privacidad

Spoxu no mantiene un servidor propio ni envía telemetría. Consulta
[`PRIVACY.md`](PRIVACY.md) para conocer qué datos se guardan localmente.

## Origen y licencia

Spoxu deriva del trabajo del proyecto original
[`sandrzejewskipl/spotify-scheduler`](https://github.com/sandrzejewskipl/spotify-scheduler).
Se mantienen la licencia MIT, la atribución a Szymon Andrzejewski y el código de
conducta del repositorio original.
""",
)

write(
    "CHANGELOG.md",
    """
# Historial de cambios de Spoxu

## 0.2.0 · Identidad Spoxu

- Nueva marca pública Spoxu y versión 0.2.0.
- Interfaz oscura minimalista con estética glass, tarjetas, estados tipo chip y
  paleta violeta/cian de alto contraste.
- Navegación centrada en Inicio, Horarios, Conexión, Actividad, Playlists y Sistema.
- Icono de bandeja propio, separado de la identidad visual de Spotify.
- Ejecutable y artefacto Windows renombrados a `Spoxu`.
- Constantes de marca y tema centralizadas y verificadas mediante pruebas.
- Compatibilidad preservada con datos, keyring, exportaciones, namespace y autoinicio.

## 0.1.0 · Reescritura modular

- Motor de horarios semanales, por fecha, nocturnos, prioridades y conflictos.
- SQLite, keyring, bandeja, autoinicio y prevención de suspensión.
- Random Queue, importación/exportación, historial, logs, tests y compilación Windows.
- OAuth atómico, llamadas Spotify serializadas y claves foráneas SQLite.

La licencia MIT y la atribución del autor original se mantienen.
""",
)

write(
    "PRIVACY.md",
    """
# Privacidad

Spoxu es una aplicación de escritorio para uso personal y no comercial. No
mantiene un servidor propio ni envía telemetría.

La configuración no sensible, los horarios, el historial y los logs se guardan
localmente. Para preservar compatibilidad, la carpeta mantiene el identificador
técnico `SpotifySchedulerPro`. El Client Secret y los tokens OAuth se almacenan
mediante keyring en el almacén de credenciales del sistema.

Cerrar la sesión OAuth elimina los tokens y cualquier caché heredada. Para
eliminar todos los datos, cierra la aplicación y borra su carpeta local de
datos. Las solicitudes musicales se envían directamente a la API de Spotify.
""",
)

license_text = read("LICENSE")
license_text = replace_once(
    license_text,
    "Copyright (c) 2026 contributors to Spotify Scheduler Pro",
    "Copyright (c) 2026 Spoxu contributors",
    label="license contributors",
)
write("LICENSE", license_text)

write(
    "tests/test_branding.py",
    """
from spotify_scheduler_pro import __version__
from spotify_scheduler_pro.branding import (
    ARTIFACT_NAME,
    DISPLAY_NAME,
    EXECUTABLE_NAME,
    LEGACY_AUTOSTART_NAME,
    LEGACY_DATA_DIR_NAME,
    LEGACY_KEYRING_SERVICE,
    LEGACY_OAUTH_SERVICE,
    PLAYLIST_EXPORT_FORMAT,
    TAGLINE,
    TECHNICAL_PACKAGE,
    VERSION,
    WINDOW_TITLE,
)


def test_public_spoxu_identity_is_consistent() -> None:
    assert DISPLAY_NAME == "Spoxu"
    assert VERSION == __version__ == "0.2.0"
    assert TAGLINE in WINDOW_TITLE
    assert WINDOW_TITLE.startswith(DISPLAY_NAME)
    assert EXECUTABLE_NAME == "Spoxu"
    assert ARTIFACT_NAME == "Spoxu-Windows"


def test_technical_compatibility_identifiers_are_stable() -> None:
    assert TECHNICAL_PACKAGE == "spotify_scheduler_pro"
    assert LEGACY_DATA_DIR_NAME == "SpotifySchedulerPro"
    assert LEGACY_KEYRING_SERVICE == "SpotifySchedulerPro"
    assert LEGACY_OAUTH_SERVICE == "SpotifySchedulerProOAuth"
    assert LEGACY_AUTOSTART_NAME == "SpotifySchedulerPro"
    assert PLAYLIST_EXPORT_FORMAT == "spotify-scheduler-pro-playlist-v1"
""",
)

write(
    "tests/test_theme.py",
    """
from spotify_scheduler_pro.theme import METRICS, PALETTE, contrast_ratio, is_hex_color


def test_theme_tokens_are_valid_hex_colors() -> None:
    required = {
        "background",
        "header",
        "surface",
        "elevated",
        "border",
        "text",
        "muted",
        "accent",
        "secondary",
        "success",
        "warning",
        "danger",
        "selection",
        "console",
    }
    assert required <= PALETTE.keys()
    assert all(is_hex_color(color) for color in PALETTE.values())


def test_theme_text_has_accessible_contrast() -> None:
    assert contrast_ratio(PALETTE["text"], PALETTE["background"]) >= 7
    assert contrast_ratio(PALETTE["text"], PALETTE["surface"]) >= 7
    assert contrast_ratio(PALETTE["muted"], PALETTE["background"]) >= 4.5


def test_theme_metrics_are_positive() -> None:
    assert all(value > 0 for value in METRICS.values())
""",
)

write(
    "tests/test_tray.py",
    """
from spotify_scheduler_pro.tray import _make_icon


def test_spoxu_tray_icon_has_brand_identity() -> None:
    icon = _make_icon()
    assert icon.mode == "RGBA"
    assert icon.size == (64, 64)
    colors = {color for _count, color in icon.getcolors(maxcolors=4096) or []}
    assert (124, 92, 252, 255) in colors
    assert (56, 214, 199, 255) in colors
    assert len(colors) >= 5
""",
)

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
subprocess.run(
    [
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    ],
    check=True,
)
subprocess.run(["git", "commit", "-m", "rebrand application as Spoxu"], check=True)
subprocess.run(["git", "push", "origin", "HEAD:agent/spotify-scheduler-pro"], check=True)
