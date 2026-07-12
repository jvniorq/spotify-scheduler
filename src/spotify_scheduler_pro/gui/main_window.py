from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from ..autostart import set_start_with_windows
from ..config import AppConfig, ConfigManager
from ..controller import AutomationController
from ..models import ScheduleEntry, ScheduleKind, SpotifyDevice, SpotifyPlaylist
from ..paths import AppPaths
from ..scheduler import DAY_NAMES_ES, SchedulerEngine
from ..spotify_client import SpotifyService
from ..storage import Storage
from ..system_control import set_prevent_sleep
from ..tray import TrayController
from .dialogs import ScheduleDialog

LOGGER = logging.getLogger("spotify_scheduler_pro.gui")


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        *,
        paths: AppPaths,
        config_manager: ConfigManager,
        storage: Storage,
        spotify: SpotifyService,
        start_minimized: bool = False,
    ):
        self.root = root
        self.paths = paths
        self.config_manager = config_manager
        self.storage = storage
        self.spotify = spotify
        self.config = self.config_manager.load()

        self.playlists: list[SpotifyPlaylist] = []
        self.devices: list[SpotifyDevice] = []
        self._closing = False
        self._dashboard_refresh_inflight = False
        self._ui_queue: queue.Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = queue.Queue()

        self.controller = AutomationController(
            storage=self.storage,
            spotify=self.spotify,
            config_provider=lambda: self.config,
            status_callback=self._on_controller_status_from_thread,
        )

        self.tray = TrayController(
            show_callback=lambda: self._post_to_ui(self.show),
            pause_callback=self.controller.toggle_pause,
            exit_callback=lambda: self._post_to_ui(self.exit),
        )

        self._configure_root()
        self._build_style()
        self._build_menu()
        self._build_layout()
        self._load_config_into_form()
        self.refresh_schedules()
        self.refresh_local_events()
        self.refresh_log()
        self._process_ui_queue()
        self._periodic_dashboard_refresh()

        self.controller.start()
        set_prevent_sleep(self.config.prevent_sleep)

        if self.config.minimize_to_tray:
            self.tray.start()

        if start_minimized or self.config.start_minimized:
            self.root.after(250, self.hide_to_tray)
        else:
            self.root.deiconify()

        if self.config.client_id and self.config_manager.get_client_secret():
            self.run_async(
                lambda: self.spotify.connect(self.config),
                on_success=lambda profile: self._on_connected(profile, silent=True),
                on_error=lambda exc: self._set_connection_status(
                    f"No se pudo conectar automáticamente: {exc}"
                ),
                description="conexión automática",
            )

    def _configure_root(self) -> None:
        self.root.title("Spotify Scheduler Pro")
        self.root.geometry("1180x760")
        self.root.minsize(980, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_requested)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            if "vista" in style.theme_names():
                style.theme_use("vista")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 11))
        style.configure("StatusGood.TLabel", foreground="#0b7a32", font=("Segoe UI", 11, "bold"))
        style.configure("StatusWarn.TLabel", foreground="#a35b00", font=("Segoe UI", 11, "bold"))
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)

        app_menu = tk.Menu(menu, tearoff=False)
        app_menu.add_command(label="Mostrar carpeta de datos", command=self.open_data_folder)
        app_menu.add_command(label="Actualizar datos", command=self.refresh_everything)
        app_menu.add_separator()
        app_menu.add_command(label="Salir", command=self.exit)
        menu.add_cascade(label="Aplicación", menu=app_menu)

        automation_menu = tk.Menu(menu, tearoff=False)
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

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Acerca de", command=self.show_about)
        menu.add_cascade(label="Ayuda", menu=help_menu)

        self.root.configure(menu=menu)

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")

        ttk.Label(header, text="Spotify Scheduler Pro", style="Title.TLabel").pack(side="left")

        self.connection_var = tk.StringVar(value="Spotify: desconectado")
        ttk.Label(header, textvariable=self.connection_var).pack(side="right", padx=(12, 0))

        self.automation_var = tk.StringVar(value="Automatización: iniciando")
        ttk.Label(header, textvariable=self.automation_var).pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.dashboard_tab = ttk.Frame(self.notebook)
        self.schedule_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.transfer_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dashboard_tab, text="Panel")
        self.notebook.add(self.schedule_tab, text="Horarios")
        self.notebook.add(self.settings_tab, text="Ajustes")
        self.notebook.add(self.history_tab, text="Historial")
        self.notebook.add(self.transfer_tab, text="Importar/Exportar")
        self.notebook.add(self.logs_tab, text="Registros")

        self._build_dashboard_tab()
        self._build_schedule_tab()
        self._build_settings_tab()
        self._build_history_tab()
        self._build_transfer_tab()
        self._build_logs_tab()

        footer = ttk.Frame(self.root, padding=(12, 4))
        footer.pack(fill="x")
        self.footer_var = tk.StringVar(value="Listo.")
        ttk.Label(footer, textvariable=self.footer_var).pack(side="left")
        ttk.Label(
            footer,
            text=f"Datos: {self.paths.root}",
            foreground="#666666",
        ).pack(side="right")

    def _build_dashboard_tab(self) -> None:
        container = ttk.Frame(self.dashboard_tab, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        status_card = ttk.LabelFrame(container, text="Estado de automatización", padding=16)
        status_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.dashboard_status_var = tk.StringVar(value="Iniciando…")
        ttk.Label(
            status_card,
            textvariable=self.dashboard_status_var,
            style="StatusWarn.TLabel",
            wraplength=1000,
        ).pack(anchor="w")

        self.next_schedule_var = tk.StringVar(value="")
        ttk.Label(
            status_card,
            textvariable=self.next_schedule_var,
            wraplength=1000,
        ).pack(anchor="w", pady=(8, 0))

        playback_card = ttk.LabelFrame(container, text="Reproducción actual", padding=16)
        playback_card.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        self.now_playing_var = tk.StringVar(value="Sin datos.")
        ttk.Label(
            playback_card,
            textvariable=self.now_playing_var,
            justify="left",
            wraplength=500,
            font=("Segoe UI", 11),
        ).pack(anchor="nw", fill="both", expand=True)

        device_card = ttk.LabelFrame(container, text="Dispositivos", padding=16)
        device_card.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        self.device_listbox = tk.Listbox(
            device_card,
            height=12,
            activestyle="none",
            font=("Segoe UI", 10),
        )
        self.device_listbox.pack(fill="both", expand=True)

        controls = ttk.Frame(container)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        ttk.Button(
            controls,
            text="Actualizar Spotify",
            command=self.refresh_spotify_data,
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Pausar/Reanudar automatización",
            command=self.toggle_automation,
        ).pack(side="left", padx=8)
        ttk.Button(
            controls,
            text="Pausar música",
            command=self.manual_pause,
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Ocultar en bandeja",
            command=self.hide_to_tray,
        ).pack(side="right")

    def _build_schedule_tab(self) -> None:
        container = ttk.Frame(self.schedule_tab, padding=12)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

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
        self.schedule_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.schedule_tree.bind("<Double-1>", lambda _event: self.edit_schedule())

        buttons = ttk.Frame(container)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        ttk.Button(buttons, text="Nuevo", command=self.add_schedule).pack(side="left")
        ttk.Button(buttons, text="Editar", command=self.edit_schedule).pack(side="left", padx=6)
        ttk.Button(buttons, text="Eliminar", command=self.delete_schedule).pack(side="left")
        ttk.Button(buttons, text="Habilitar/Deshabilitar", command=self.toggle_schedule).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Probar ahora", command=self.test_schedule_now).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(buttons, text="Actualizar", command=self.refresh_schedules).pack(side="right")

        self.schedule_info_var = tk.StringVar(value="")
        ttk.Label(
            container,
            textvariable=self.schedule_info_var,
            foreground="#555555",
            wraplength=1000,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_settings_tab(self) -> None:
        canvas = tk.Canvas(self.settings_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_tab, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=20)

        frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        credentials = ttk.LabelFrame(frame, text="Spotify Developer", padding=16)
        credentials.pack(fill="x", pady=(0, 12))
        credentials.columnconfigure(1, weight=1)

        self.client_id_var = tk.StringVar()
        self.client_secret_var = tk.StringVar()
        self.redirect_uri_var = tk.StringVar()

        ttk.Label(credentials, text="Client ID").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(credentials, textvariable=self.client_id_var).grid(
            row=0, column=1, sticky="ew", padx=(12, 0), pady=6
        )

        ttk.Label(credentials, text="Client Secret").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(credentials, textvariable=self.client_secret_var, show="•").grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=6
        )

        ttk.Label(credentials, text="Redirect URI").grid(row=2, column=0, sticky="w", pady=6)
        redirect_entry = ttk.Entry(credentials, textvariable=self.redirect_uri_var)
        redirect_entry.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=6)

        ttk.Label(
            credentials,
            text="Registra exactamente esta URI en Spotify Developer Dashboard.",
            foreground="#666666",
        ).grid(row=3, column=1, sticky="w")

        playback = ttk.LabelFrame(frame, text="Reproducción y automatización", padding=16)
        playback.pack(fill="x", pady=(0, 12))
        playback.columnconfigure(1, weight=1)

        self.default_device_var = tk.StringVar()
        self.polling_var = tk.DoubleVar()
        self.random_limit_var = tk.IntVar()
        self.avoid_recent_var = tk.IntVar()

        ttk.Label(playback, text="Dispositivo predeterminado").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.default_device_combo = ttk.Combobox(
            playback,
            textvariable=self.default_device_var,
        )
        self.default_device_combo.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=6)

        ttk.Label(playback, text="Intervalo de revisión (s)").grid(
            row=1, column=0, sticky="w", pady=6
        )
        ttk.Spinbox(
            playback,
            textvariable=self.polling_var,
            from_=1.0,
            to=60.0,
            increment=0.5,
        ).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=6)

        ttk.Label(playback, text="Máximo en cola aleatoria").grid(
            row=2, column=0, sticky="w", pady=6
        )
        ttk.Spinbox(
            playback,
            textvariable=self.random_limit_var,
            from_=1,
            to=1000,
        ).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)

        ttk.Label(playback, text="Evitar últimas N canciones").grid(
            row=3, column=0, sticky="w", pady=6
        )
        ttk.Spinbox(
            playback,
            textvariable=self.avoid_recent_var,
            from_=0,
            to=50,
        ).grid(row=3, column=1, sticky="w", padx=(12, 0), pady=6)

        behavior = ttk.LabelFrame(frame, text="Comportamiento", padding=16)
        behavior.pack(fill="x", pady=(0, 12))

        self.pause_outside_var = tk.BooleanVar()
        self.launch_spotify_var = tk.BooleanVar()
        self.skip_explicit_var = tk.BooleanVar()
        self.start_minimized_var = tk.BooleanVar()
        self.minimize_to_tray_var = tk.BooleanVar()
        self.start_with_windows_var = tk.BooleanVar()
        self.prevent_sleep_var = tk.BooleanVar()

        options = [
            ("Pausar música al salir del horario", self.pause_outside_var),
            ("Intentar abrir Spotify Desktop si no está activo", self.launch_spotify_var),
            ("Saltar canciones explícitas globalmente", self.skip_explicit_var),
            ("Iniciar minimizado", self.start_minimized_var),
            ("Cerrar la ventana = minimizar a bandeja", self.minimize_to_tray_var),
            ("Iniciar automáticamente con Windows", self.start_with_windows_var),
            ("Evitar suspensión de Windows mientras la app está abierta", self.prevent_sleep_var),
        ]
        for text, variable in options:
            ttk.Checkbutton(behavior, text=text, variable=variable).pack(anchor="w", pady=2)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        ttk.Button(
            buttons,
            text="Guardar ajustes",
            command=self.save_settings,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Guardar y autorizar",
            command=self.save_and_connect,
        ).pack(side="left", padx=8)
        ttk.Button(
            buttons,
            text="Cerrar sesión OAuth",
            command=self.logout_spotify,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Actualizar dispositivos",
            command=self.refresh_spotify_data,
        ).pack(side="right")

        self.settings_status_var = tk.StringVar(value="")
        ttk.Label(
            frame,
            textvariable=self.settings_status_var,
            wraplength=1000,
        ).pack(fill="x", pady=(12, 0))

    def _build_history_tab(self) -> None:
        notebook = ttk.Notebook(self.history_tab)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        recent_frame = ttk.Frame(notebook)
        local_frame = ttk.Frame(notebook)
        notebook.add(recent_frame, text="Spotify: canciones recientes")
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
        ).pack(anchor="e", pady=(8, 0))

        event_columns = (
            "timestamp",
            "type",
            "schedule",
            "playlist",
            "device",
            "details",
        )
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
        ).pack(anchor="e", pady=(8, 0))

    def _build_transfer_tab(self) -> None:
        container = ttk.Frame(self.transfer_tab, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Copias de seguridad de playlists",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            container,
            text=(
                "Exporta una playlist a JSON con sus canciones y, cuando sea posible, "
                "su portada. También puedes importar un archivo generado por esta edición."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(8, 22))

        self.transfer_playlist_var = tk.StringVar()
        self.transfer_playlist_combo = ttk.Combobox(
            container,
            textvariable=self.transfer_playlist_var,
            width=90,
        )
        self.transfer_playlist_combo.pack(fill="x")

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", pady=16)

        ttk.Button(
            buttons,
            text="Exportar playlist seleccionada",
            command=self.export_playlist,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Importar playlist desde JSON",
            command=self.import_playlist,
        ).pack(side="left", padx=8)
        ttk.Button(
            buttons,
            text="Actualizar lista",
            command=self.refresh_spotify_data,
        ).pack(side="left")

        self.transfer_status_var = tk.StringVar(value="")
        ttk.Label(
            container,
            textvariable=self.transfer_status_var,
            wraplength=900,
        ).pack(anchor="w", pady=(8, 0))

    def _build_logs_tab(self) -> None:
        container = ttk.Frame(self.logs_tab, padding=12)
        container.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            container,
            wrap="none",
            font=("Consolas", 9),
            state="disabled",
        )
        y_scroll = ttk.Scrollbar(container, orient="vertical", command=self.log_text.yview)
        x_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.log_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        controls = ttk.Frame(container)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(controls, text="Actualizar", command=self.refresh_log).pack(side="left")
        ttk.Button(controls, text="Abrir carpeta de logs", command=self.open_logs_folder).pack(
            side="left", padx=8
        )

    def _load_config_into_form(self) -> None:
        self.client_id_var.set(self.config.client_id)
        secret = self.config_manager.get_client_secret()
        self.client_secret_var.set(secret)
        self.redirect_uri_var.set(self.config.redirect_uri)
        self.default_device_var.set(self.config.default_device_name)
        self.polling_var.set(self.config.polling_seconds)
        self.random_limit_var.set(self.config.random_queue_limit)
        self.avoid_recent_var.set(self.config.avoid_recent_tracks)
        self.pause_outside_var.set(self.config.pause_outside_schedule)
        self.launch_spotify_var.set(self.config.launch_spotify_if_missing)
        self.skip_explicit_var.set(self.config.skip_explicit)
        self.start_minimized_var.set(self.config.start_minimized)
        self.minimize_to_tray_var.set(self.config.minimize_to_tray)
        self.start_with_windows_var.set(self.config.start_with_windows)
        self.prevent_sleep_var.set(self.config.prevent_sleep)

    def _read_config_from_form(self) -> AppConfig:
        polling = float(self.polling_var.get())
        random_limit = int(self.random_limit_var.get())
        avoid_recent = int(self.avoid_recent_var.get())

        if not 1 <= polling <= 60:
            raise ValueError("El intervalo de revisión debe estar entre 1 y 60 segundos.")
        if not 1 <= random_limit <= 1000:
            raise ValueError("El máximo de cola aleatoria debe estar entre 1 y 1000.")
        if not 0 <= avoid_recent <= 50:
            raise ValueError("Las canciones recientes deben estar entre 0 y 50.")

        return AppConfig(
            client_id=self.client_id_var.get().strip(),
            redirect_uri=self.redirect_uri_var.get().strip(),
            default_device_name=self.default_device_var.get().strip(),
            polling_seconds=polling,
            pause_outside_schedule=self.pause_outside_var.get(),
            launch_spotify_if_missing=self.launch_spotify_var.get(),
            skip_explicit=self.skip_explicit_var.get(),
            start_minimized=self.start_minimized_var.get(),
            minimize_to_tray=self.minimize_to_tray_var.get(),
            start_with_windows=self.start_with_windows_var.get(),
            prevent_sleep=self.prevent_sleep_var.get(),
            random_queue_limit=random_limit,
            avoid_recent_tracks=avoid_recent,
            language="es",
        )

    def save_settings(self, *, show_message: bool = True) -> bool:
        try:
            new_config = self._read_config_from_form()
            self.config_manager.save_client_secret(self.client_secret_var.get().strip())
            self.config_manager.save(new_config)
            self.config = new_config
            set_start_with_windows(new_config.start_with_windows)
            set_prevent_sleep(new_config.prevent_sleep)

            if new_config.minimize_to_tray:
                self.tray.start()
            else:
                self.tray.stop()

            self.controller.refresh()
            self.settings_status_var.set("Ajustes guardados correctamente.")
            if show_message:
                messagebox.showinfo("Ajustes", "Los ajustes fueron guardados.")
            return True
        except Exception as exc:
            self.settings_status_var.set(str(exc))
            messagebox.showerror("No se pudieron guardar los ajustes", str(exc))
            return False

    def save_and_connect(self) -> None:
        if not self.save_settings(show_message=False):
            return

        self.settings_status_var.set("Abriendo autorización de Spotify…")
        self.run_async(
            lambda: self.spotify.connect(self.config, force_dialog=True),
            on_success=self._on_connected,
            on_error=lambda exc: self._show_error("No se pudo autorizar Spotify", exc),
            description="autorización Spotify",
        )

    def _on_connected(self, profile: dict[str, Any], silent: bool = False) -> None:
        name = profile.get("display_name") or profile.get("id") or "cuenta"
        self._set_connection_status(f"Spotify: conectado como {name}")
        self.settings_status_var.set(f"Conectado como {name}.")
        self.refresh_spotify_data()
        if not silent:
            messagebox.showinfo("Spotify", f"Conexión correcta como {name}.")

    def logout_spotify(self) -> None:
        if not messagebox.askyesno(
            "Cerrar sesión",
            "Se eliminará la caché OAuth local. ¿Continuar?",
        ):
            return
        self.spotify.disconnect(delete_cache=True)
        self._set_connection_status("Spotify: desconectado")
        self.settings_status_var.set("Sesión OAuth eliminada.")

    def refresh_everything(self) -> None:
        self.refresh_schedules()
        self.refresh_local_events()
        self.refresh_spotify_data()
        self.refresh_log()

    def refresh_spotify_data(self) -> None:
        if not self.spotify.connected:
            self.footer_var.set("Spotify no está conectado.")
            return

        self.footer_var.set("Consultando playlists y dispositivos…")

        def work() -> tuple[list[SpotifyPlaylist], list[SpotifyDevice]]:
            return self.spotify.playlists(), self.spotify.devices()

        self.run_async(
            work,
            on_success=self._apply_spotify_data,
            on_error=lambda exc: self._show_error("No se pudieron actualizar los datos", exc),
            description="actualización de Spotify",
        )

    def _apply_spotify_data(
        self,
        result: tuple[list[SpotifyPlaylist], list[SpotifyDevice]],
    ) -> None:
        self.playlists, self.devices = result

        playlist_values = [
            f"{playlist.name} — {playlist.id}" for playlist in self.playlists
        ]
        device_values = [device.name for device in self.devices]

        self.transfer_playlist_combo.configure(values=playlist_values)
        self.default_device_combo.configure(values=device_values)

        self.device_listbox.delete(0, tk.END)
        for device in self.devices:
            active = "●" if device.is_active else "○"
            restricted = " · restringido" if device.is_restricted else ""
            volume = (
                f" · volumen {device.volume_percent}%"
                if device.volume_percent is not None
                else ""
            )
            self.device_listbox.insert(
                tk.END,
                f"{active} {device.name} · {device.type}{volume}{restricted}",
            )

        self.footer_var.set(
            f"Spotify actualizado: {len(self.playlists)} playlists y {len(self.devices)} dispositivos."
        )

    def refresh_schedules(self) -> None:
        entries = self.storage.list_schedules()
        self.schedule_tree.delete(*self.schedule_tree.get_children())

        for entry in entries:
            when = (
                DAY_NAMES_ES[entry.day_of_week or 0]
                if entry.kind == ScheduleKind.WEEKLY
                else entry.specific_date.isoformat() if entry.specific_date else ""
            )
            item = self.schedule_tree.insert(
                "",
                tk.END,
                iid=str(entry.id),
                values=(
                    "Sí" if entry.enabled else "No",
                    entry.name,
                    "Semanal" if entry.kind == ScheduleKind.WEEKLY else "Fecha",
                    when,
                    entry.start_time.strftime("%H:%M:%S"),
                    entry.end_time.strftime("%H:%M:%S"),
                    entry.playlist_name or entry.playlist_id,
                    entry.device_name or "Predeterminado",
                    "Sí" if entry.random_queue else "No",
                    entry.priority,
                ),
            )
            if not entry.enabled:
                self.schedule_tree.item(item, tags=("disabled",))

        self.schedule_tree.tag_configure("disabled", foreground="#888888")
        engine = SchedulerEngine(entries)
        self.schedule_info_var.set(engine.status())
        self.controller.refresh()

    def selected_schedule(self) -> ScheduleEntry | None:
        selection = self.schedule_tree.selection()
        if not selection:
            return None
        try:
            schedule_id = int(selection[0])
        except ValueError:
            return None
        return self.storage.get_schedule(schedule_id)

    def add_schedule(self) -> None:
        dialog = ScheduleDialog(
            self.root,
            playlists=self.playlists,
            devices=self.devices,
        )
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self._save_schedule_from_dialog(dialog.result)

    def edit_schedule(self) -> None:
        entry = self.selected_schedule()
        if entry is None:
            messagebox.showwarning("Horarios", "Selecciona un horario.")
            return
        dialog = ScheduleDialog(
            self.root,
            entry=entry,
            playlists=self.playlists,
            devices=self.devices,
        )
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self._save_schedule_from_dialog(dialog.result)

    def _save_schedule_from_dialog(self, entry: ScheduleEntry) -> None:
        engine = SchedulerEngine(self.storage.list_schedules())
        conflicts = engine.conflicts_for(entry)

        if conflicts:
            names = "\n".join(
                f"• {conflict.second.name}: {conflict.reason}"
                for conflict in conflicts
            )
            proceed = messagebox.askyesno(
                "Conflicto de horarios",
                "Se detectaron posibles conflictos:\n\n"
                f"{names}\n\n"
                "La prioridad decidirá qué horario domina. ¿Guardar de todas formas?",
            )
            if not proceed:
                return

        try:
            self.storage.save_schedule(entry)
        except Exception as exc:
            self._show_error("No se pudo guardar el horario", exc)
            return

        self.refresh_schedules()

    def delete_schedule(self) -> None:
        entry = self.selected_schedule()
        if entry is None or entry.id is None:
            messagebox.showwarning("Horarios", "Selecciona un horario.")
            return
        if not messagebox.askyesno(
            "Eliminar horario",
            f"¿Eliminar “{entry.name}”?",
        ):
            return
        self.storage.delete_schedule(entry.id)
        self.refresh_schedules()

    def toggle_schedule(self) -> None:
        entry = self.selected_schedule()
        if entry is None or entry.id is None:
            messagebox.showwarning("Horarios", "Selecciona un horario.")
            return
        self.storage.set_schedule_enabled(entry.id, not entry.enabled)
        self.refresh_schedules()

    def test_schedule_now(self) -> None:
        entry = self.selected_schedule()
        if entry is None:
            messagebox.showwarning("Prueba", "Selecciona un horario.")
            return
        if not self.spotify.connected:
            messagebox.showwarning("Prueba", "Conecta Spotify primero.")
            return

        self.footer_var.set(f"Probando {entry.name}…")

        def work() -> str:
            device = self.spotify.find_device(
                preferred_name=entry.device_name or self.config.default_device_name
            )
            if device is None:
                raise RuntimeError("No se encontró un dispositivo disponible.")

            playlist_id = entry.playlist_id
            playlist_name = entry.playlist_name or playlist_id

            if entry.random_queue:
                playlist_id, playlist_name, _count = self.spotify.create_random_queue(
                    entry.playlist_id,
                    max_tracks=self.config.random_queue_limit,
                    avoid_recent_count=self.config.avoid_recent_tracks,
                    skip_explicit=entry.skip_explicit or self.config.skip_explicit,
                )

            self.spotify.start_playlist(playlist_id, device_id=device.id)
            return f"Reproduciendo {playlist_name} en {device.name}."

        self.run_async(
            work,
            on_success=lambda text: self._set_footer_and_message("Prueba", text),
            on_error=lambda exc: self._show_error("La prueba falló", exc),
            description="prueba de playlist",
        )

    def manual_pause(self) -> None:
        if not self.spotify.connected:
            return
        self.run_async(
            lambda: self.spotify.pause(),
            on_success=lambda _result: self.footer_var.set("Reproducción pausada."),
            on_error=lambda exc: self._show_error("No se pudo pausar", exc),
            description="pausa manual",
        )

    def toggle_automation(self) -> None:
        paused = self.controller.toggle_pause()
        self.automation_var.set(
            "Automatización: pausada" if paused else "Automatización: activa"
        )

    def refresh_recent_tracks(self) -> None:
        if not self.spotify.connected:
            return

        self.run_async(
            lambda: self.spotify.recently_played(50),
            on_success=self._apply_recent_tracks,
            on_error=lambda exc: self._show_error("No se pudo leer el historial", exc),
            description="historial Spotify",
        )

    def _apply_recent_tracks(self, tracks: list[dict[str, Any]]) -> None:
        self.recent_tree.delete(*self.recent_tree.get_children())
        for item in tracks:
            played_at = str(item.get("played_at") or "")
            try:
                parsed = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
                played_at = parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            self.recent_tree.insert(
                "",
                tk.END,
                values=(
                    played_at,
                    item.get("name") or "",
                    item.get("artists") or "",
                    "Sí" if item.get("explicit") else "No",
                ),
            )

    def refresh_local_events(self) -> None:
        self.events_tree.delete(*self.events_tree.get_children())
        for event in self.storage.list_events(250):
            self.events_tree.insert(
                "",
                tk.END,
                values=(
                    event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    event.event_type,
                    event.schedule_id or "",
                    event.playlist_name or event.playlist_id,
                    event.device_name,
                    event.details,
                ),
            )

    def _selected_transfer_playlist_id(self) -> str:
        value = self.transfer_playlist_var.get().strip()
        if " — " in value:
            return value.rsplit(" — ", 1)[1].strip()
        if "open.spotify.com/playlist/" in value:
            return value.split("open.spotify.com/playlist/", 1)[1].split("?", 1)[0]
        return value

    def export_playlist(self) -> None:
        playlist_id = self._selected_transfer_playlist_id()
        if not playlist_id:
            messagebox.showwarning("Exportar", "Selecciona una playlist.")
            return
        target = filedialog.asksaveasfilename(
            title="Exportar playlist",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json")],
        )
        if not target:
            return

        self.run_async(
            lambda: self.spotify.export_playlist(playlist_id, Path(target)),
            on_success=lambda path: self._set_transfer_status(
                f"Playlist exportada en {path}."
            ),
            on_error=lambda exc: self._show_error("No se pudo exportar", exc),
            description="exportación de playlist",
        )

    def import_playlist(self) -> None:
        source = filedialog.askopenfilename(
            title="Importar playlist",
            filetypes=[("Archivos JSON", "*.json")],
        )
        if not source:
            return

        name = simpledialog.askstring(
            "Nombre de la playlist",
            "Nombre para la nueva playlist.\nDéjalo vacío para usar el nombre original:",
            parent=self.root,
        )
        if name is None:
            return

        self.run_async(
            lambda: self.spotify.import_playlist(Path(source), new_name=name.strip() or None),
            on_success=lambda playlist: self._set_transfer_status(
                f"Playlist creada: {playlist.name} ({playlist.id})."
            ),
            on_error=lambda exc: self._show_error("No se pudo importar", exc),
            description="importación de playlist",
        )

    def cleanup_temporary_playlists(self) -> None:
        if not self.spotify.connected:
            messagebox.showwarning("Limpieza", "Conecta Spotify primero.")
            return

        self.run_async(
            lambda: self.spotify.cleanup_temporary_playlists(older_than_hours=24),
            on_success=lambda count: self._set_footer_and_message(
                "Limpieza",
                f"Se eliminaron {count} playlists temporales antiguas.",
            ),
            on_error=lambda exc: self._show_error("La limpieza falló", exc),
            description="limpieza de playlists temporales",
        )

    def _periodic_dashboard_refresh(self) -> None:
        if self._closing:
            return

        entries = self.storage.list_schedules(enabled_only=True)
        engine = SchedulerEngine(entries)
        self.next_schedule_var.set(engine.status())

        if self.spotify.connected and not self._dashboard_refresh_inflight:
            self._dashboard_refresh_inflight = True

            def apply_playback(playback: dict[str, Any] | None) -> None:
                self._dashboard_refresh_inflight = False
                self._apply_current_playback(playback)

            def ignore_playback_error(_error: Exception) -> None:
                self._dashboard_refresh_inflight = False

            self.run_async(
                self.spotify.current_playback,
                on_success=apply_playback,
                on_error=ignore_playback_error,
                description="estado actual",
                show_busy=False,
            )

        self.refresh_local_events()
        self.root.after(5000, self._periodic_dashboard_refresh)

    def _apply_current_playback(self, playback: dict[str, Any] | None) -> None:
        if not playback or not playback.get("item"):
            self.now_playing_var.set("No hay reproducción activa.")
            return

        item = playback["item"]
        artists = ", ".join(
            str(artist.get("name") or "")
            for artist in item.get("artists", [])
            if isinstance(artist, dict)
        )
        device = playback.get("device") or {}
        context = playback.get("context") or {}
        state = "Reproduciendo" if playback.get("is_playing") else "Pausado"

        self.now_playing_var.set(
            f"{state}\n\n"
            f"Canción: {item.get('name', '')}\n"
            f"Artista: {artists}\n"
            f"Dispositivo: {device.get('name', '')}\n"
            f"Volumen: {device.get('volume_percent', '—')}%\n"
            f"Contexto: {context.get('type', '—')} · {context.get('uri', '—')}"
        )

    def _on_controller_status_from_thread(
        self,
        message: str,
        payload: dict[str, Any] | None,
    ) -> None:
        self._post_to_ui(self._apply_controller_status, message, payload)

    def _apply_controller_status(
        self,
        message: str,
        _payload: dict[str, Any] | None,
    ) -> None:
        self.dashboard_status_var.set(message)
        self.automation_var.set(
            "Automatización: pausada"
            if self.controller.paused
            else "Automatización: activa"
        )

    def _set_connection_status(self, text: str) -> None:
        self.connection_var.set(text)

    def _set_transfer_status(self, text: str) -> None:
        self.transfer_status_var.set(text)
        self.footer_var.set(text)
        self.refresh_spotify_data()

    def _set_footer_and_message(self, title: str, text: str) -> None:
        self.footer_var.set(text)
        messagebox.showinfo(title, text)

    def refresh_log(self) -> None:
        try:
            text = self.paths.log_file.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()[-1500:]
            content = "\n".join(lines)
        except OSError as exc:
            content = f"No se pudo abrir el log: {exc}"

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert("1.0", content)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def open_data_folder(self) -> None:
        self._open_folder(self.paths.root)

    def open_logs_folder(self) -> None:
        self._open_folder(self.paths.logs_dir)

    @staticmethod
    def _open_folder(path: Path) -> None:
        import os
        import platform
        import subprocess

        try:
            if platform.system() == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Carpeta", str(exc))

    def hide_to_tray(self) -> None:
        if not self.config.minimize_to_tray:
            self.root.iconify()
            return
        self.tray.start()
        self.root.withdraw()
        self.footer_var.set("La aplicación continúa funcionando en la bandeja.")

    def show(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def on_close_requested(self) -> None:
        if self.config.minimize_to_tray:
            self.hide_to_tray()
        else:
            self.exit()

    def exit(self) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            self.controller.stop()
            self.tray.stop()
            set_prevent_sleep(False)
        finally:
            self.root.after(0, self.root.destroy)

    def show_about(self) -> None:
        messagebox.showinfo(
            "Acerca de",
            "Spotify Scheduler Pro 0.1.0\n\n"
            "Edición modular inspirada en spotify-scheduler de Szymon Andrzejewski.\n"
            "Licencia MIT.\n\n"
            "Requiere Spotify Premium y un dispositivo Spotify Connect.",
        )

    def _post_to_ui(self, callback: Callable[..., Any], *args: Any) -> None:
        self._ui_queue.put((callback, args))

    def _process_ui_queue(self) -> None:
        if self._closing:
            return
        while True:
            try:
                callback, args = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except Exception:
                LOGGER.exception("Error procesando una tarea de interfaz.")
        self.root.after(100, self._process_ui_queue)

    def run_async(
        self,
        function: Callable[[], Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        description: str = "tarea",
        show_busy: bool = True,
    ) -> None:
        if show_busy:
            self.footer_var.set(f"Ejecutando {description}…")

        def runner() -> None:
            try:
                result = function()
            except Exception as exc:
                LOGGER.exception("Falló %s.", description)
                if on_error:
                    self._post_to_ui(on_error, exc)
                return

            if on_success:
                self._post_to_ui(on_success, result)
            elif show_busy:
                self._post_to_ui(self.footer_var.set, f"{description.capitalize()} completada.")

        threading.Thread(
            target=runner,
            name=f"Task-{description}",
            daemon=True,
        ).start()

    def _show_error(self, title: str, error: Exception) -> None:
        self.footer_var.set(str(error))
        messagebox.showerror(title, str(error))
