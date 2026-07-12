from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from ..branding import DISPLAY_NAME
from ..models import ScheduleEntry, ScheduleKind, SpotifyDevice, SpotifyPlaylist
from ..scheduler import DAY_NAMES_ES, parse_date, parse_time
from ..theme import PALETTE


class ScheduleDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        entry: ScheduleEntry | None = None,
        playlists: list[SpotifyPlaylist] | None = None,
        devices: list[SpotifyDevice] | None = None,
    ):
        super().__init__(parent)
        self.title(
            f"{DISPLAY_NAME} · Editar horario"
            if entry
            else f"{DISPLAY_NAME} · Nuevo horario"
        )
        self.geometry("740x680")
        self.minsize(680, 620)
        self.configure(background=PALETTE["background"])
        self.transient(parent)
        self.grab_set()

        self.result: ScheduleEntry | None = None
        self._entry = entry or ScheduleEntry()
        self._playlists = playlists or []
        self._devices = devices or []

        self.name_var = tk.StringVar(value=self._entry.name)
        self.kind_var = tk.StringVar(value=self._entry.kind.value)
        self.day_var = tk.StringVar(
            value=DAY_NAMES_ES[self._entry.day_of_week or 0]
        )
        self.date_var = tk.StringVar(
            value=(self._entry.specific_date or date.today()).isoformat()
        )
        self.start_var = tk.StringVar(
            value=self._entry.start_time.strftime("%H:%M:%S")
        )
        self.end_var = tk.StringVar(
            value=self._entry.end_time.strftime("%H:%M:%S")
        )
        self.playlist_var = tk.StringVar(
            value=self._playlist_display_value(self._entry.playlist_id)
        )
        self.device_var = tk.StringVar(value=self._entry.device_name)
        self.random_var = tk.BooleanVar(value=self._entry.random_queue)
        self.skip_explicit_var = tk.BooleanVar(value=self._entry.skip_explicit)
        self.enabled_var = tk.BooleanVar(value=self._entry.enabled)
        self.priority_var = tk.IntVar(value=self._entry.priority)

        self._build()
        self.kind_var.trace_add("write", lambda *_: self._update_kind_state())
        self._update_kind_state()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._save())
        self.wait_visibility()
        self.focus_force()

    def _playlist_display_value(self, playlist_id: str) -> str:
        for playlist in self._playlists:
            if playlist.id == playlist_id:
                return f"{playlist.name} — {playlist.id}"
        return playlist_id

    @staticmethod
    def _extract_id(value: str) -> str:
        value = value.strip()
        if "open.spotify.com/playlist/" in value:
            value = value.split("open.spotify.com/playlist/", 1)[1]
            value = value.split("?", 1)[0].split("/", 1)[0]
        if "spotify:playlist:" in value:
            value = value.split("spotify:playlist:", 1)[1]
        if " — " in value:
            value = value.rsplit(" — ", 1)[1]
        return value.strip()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=18, style="Glass.TFrame")
        container.pack(fill="both", expand=True, padx=18, pady=18)
        container.columnconfigure(1, weight=1)

        row = 0

        def label(text: str) -> None:
            nonlocal row
            ttk.Label(container, text=text).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)

        label("Nombre")
        ttk.Entry(container, textvariable=self.name_var).grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        label("Tipo")
        type_frame = ttk.Frame(container, style="Glass.TFrame")
        type_frame.grid(row=row, column=1, sticky="w", pady=6)
        ttk.Radiobutton(
            type_frame,
            text="Semanal recurrente",
            variable=self.kind_var,
            value=ScheduleKind.WEEKLY.value,
        ).pack(side="left", padx=(0, 15))
        ttk.Radiobutton(
            type_frame,
            text="Fecha específica",
            variable=self.kind_var,
            value=ScheduleKind.DATE.value,
        ).pack(side="left")
        row += 1

        label("Día semanal")
        self.day_combo = ttk.Combobox(
            container,
            textvariable=self.day_var,
            values=DAY_NAMES_ES,
            state="readonly",
        )
        self.day_combo.grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        label("Fecha")
        self.date_entry = ttk.Entry(container, textvariable=self.date_var)
        self.date_entry.grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Label(
            container,
            text="Formato AAAA-MM-DD",
            style="GlassMuted.TLabel",
        ).grid(row=row + 1, column=1, sticky="w")
        row += 2

        label("Hora inicial")
        ttk.Entry(container, textvariable=self.start_var).grid(row=row, column=1, sticky="ew", pady=6)
        row += 1

        label("Hora final")
        ttk.Entry(container, textvariable=self.end_var).grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Label(
            container,
            text="Se permite cruzar medianoche: 22:00 → 02:00.",
            style="GlassMuted.TLabel",
        ).grid(row=row + 1, column=1, sticky="w")
        row += 2

        label("Playlist")
        playlist_values = [
            f"{playlist.name} — {playlist.id}" for playlist in self._playlists
        ]
        self.playlist_combo = ttk.Combobox(
            container,
            textvariable=self.playlist_var,
            values=playlist_values,
        )
        self.playlist_combo.grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Label(
            container,
            text="Puedes elegir una playlist o pegar su URL/ID.",
            style="GlassMuted.TLabel",
        ).grid(row=row + 1, column=1, sticky="w")
        row += 2

        label("Dispositivo")
        device_values = [device.name for device in self._devices]
        ttk.Combobox(
            container,
            textvariable=self.device_var,
            values=device_values,
        ).grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Label(
            container,
            text="Vacío = usar el dispositivo predeterminado de Ajustes.",
            style="GlassMuted.TLabel",
        ).grid(row=row + 1, column=1, sticky="w")
        row += 2

        label("Prioridad")
        ttk.Spinbox(
            container,
            textvariable=self.priority_var,
            from_=-100,
            to=100,
            width=12,
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        options = ttk.LabelFrame(
            container,
            text="Opciones",
            padding=12,
            style="Glass.TLabelframe",
        )
        options.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 8))
        ttk.Checkbutton(
            options,
            text="Habilitado",
            variable=self.enabled_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            options,
            text="Cola aleatoria inteligente",
            variable=self.random_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            options,
            text="Saltar canciones explícitas",
            variable=self.skip_explicit_var,
        ).pack(anchor="w")
        row += 1

        buttons = ttk.Frame(container, style="Glass.TFrame")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(
            buttons,
            text="Cancelar",
            command=self.destroy,
            style="Secondary.TButton",
        ).pack(side="right")
        ttk.Button(
            buttons,
            text="Guardar horario",
            command=self._save,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 10))

    def _update_kind_state(self) -> None:
        weekly = self.kind_var.get() == ScheduleKind.WEEKLY.value
        self.day_combo.configure(state="readonly" if weekly else "disabled")
        self.date_entry.configure(state="disabled" if weekly else "normal")

    def _save(self) -> None:
        try:
            kind = ScheduleKind(self.kind_var.get())
            day = DAY_NAMES_ES.index(self.day_var.get()) if kind == ScheduleKind.WEEKLY else None
            specific_date = parse_date(self.date_var.get()) if kind == ScheduleKind.DATE else None
            playlist_id = self._extract_id(self.playlist_var.get())
            playlist_name = ""
            for playlist in self._playlists:
                if playlist.id == playlist_id:
                    playlist_name = playlist.name
                    break

            result = ScheduleEntry(
                id=self._entry.id,
                name=self.name_var.get().strip(),
                kind=kind,
                day_of_week=day,
                specific_date=specific_date,
                start_time=parse_time(self.start_var.get()),
                end_time=parse_time(self.end_var.get()),
                playlist_id=playlist_id,
                playlist_name=playlist_name,
                device_name=self.device_var.get().strip(),
                random_queue=self.random_var.get(),
                skip_explicit=self.skip_explicit_var.get(),
                enabled=self.enabled_var.get(),
                priority=int(self.priority_var.get()),
            )
            errors = result.validate()
            if errors:
                raise ValueError("\n".join(errors))
        except Exception as exc:
            messagebox.showerror("Horario no válido", str(exc), parent=self)
            return

        self.result = result
        self.destroy()
