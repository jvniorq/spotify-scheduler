"use strict";

const byId = (id) => document.getElementById(id);
const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const state = {
  csrf: "",
  status: {},
  schedules: [],
  playlists: [],
  devices: [],
  polling: null
};

async function api(path, options) {
  const config = Object.assign({ credentials: "same-origin" }, options || {});
  config.headers = Object.assign({}, config.headers || {});
  const method = (config.method || "GET").toUpperCase();
  if (config.body) config.headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && state.csrf) {
    config.headers["X-CSRF-Token"] = state.csrf;
  }

  const response = await fetch(path, config);
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : null;

  if (response.status === 401) {
    showLogin();
    throw new Error(payload && payload.detail ? payload.detail : "Sesión requerida.");
  }
  if (!response.ok) {
    const detail = payload && payload.detail;
    throw new Error(typeof detail === "string" ? detail : "La operación no pudo completarse.");
  }
  return payload;
}

function showLogin() {
  clearInterval(state.polling);
  state.polling = null;
  byId("appView").hidden = true;
  byId("loginView").hidden = false;
}

function showApp() {
  byId("loginView").hidden = true;
  byId("appView").hidden = false;
  if (!state.polling) state.polling = setInterval(refreshStatus, 8000);
}

function toast(message, isError) {
  const box = byId("toast");
  box.textContent = message;
  box.classList.toggle("error", Boolean(isError));
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.hidden = true; }, 3500);
}

function button(label, action, id, danger) {
  const item = document.createElement("button");
  item.type = "button";
  item.className = "button small " + (danger ? "danger" : "secondary");
  item.textContent = label;
  item.dataset.action = action;
  item.dataset.id = String(id);
  return item;
}

function formatTime(value) {
  return value ? String(value).slice(0, 5) : "—";
}

function formatDate(value) {
  if (!value) return "";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString("es");
}

function renderStatus() {
  const data = state.status;
  const connected = Boolean(data.spotify_connected);
  const paused = Boolean(data.automation_paused);

  byId("spotifyChip").textContent = connected ? "Spotify conectado" : "Spotify desconectado";
  byId("spotifyChip").className = "chip " + (connected ? "success" : "neutral");
  byId("automationChip").textContent = paused ? "Automatización pausada" : "Automatización activa";
  byId("automationChip").className = "chip " + (paused ? "warning" : "success");
  byId("automationButton").textContent = paused ? "Reanudar" : "Pausar";
  byId("statusText").textContent = data.message || "Motor preparado.";

  const playing = data.now_playing || {};
  byId("nowPlaying").textContent = playing.name || "Sin reproducción";
  byId("nowPlayingMeta").textContent = [
    Array.isArray(playing.artists) ? playing.artists.join(", ") : "",
    playing.device || ""
  ].filter(Boolean).join(" · ") || "—";

  const next = data.next_schedule;
  byId("nextSchedule").textContent = next ? next.name : "Sin horarios próximos";
  byId("nextScheduleMeta").textContent = next ? formatDate(next.starts_at) : "—";

  const active = state.devices.find((item) => item.is_active);
  byId("deviceMetric").textContent = String(state.devices.length) + " disponibles";
  byId("activeDevice").textContent = active ? active.name + " · activo" : "Ninguno activo";

  renderHistory(data.events || []);
}

function renderSchedules() {
  const body = byId("scheduleRows");
  body.replaceChildren();
  byId("emptySchedules").hidden = state.schedules.length > 0;

  state.schedules.forEach((schedule) => {
    const row = document.createElement("tr");
    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "badge " + (schedule.enabled ? "success" : "neutral");
    badge.textContent = schedule.enabled ? "Activo" : "Deshabilitado";
    statusCell.append(badge);
    row.append(statusCell);

    const when = schedule.kind === "date"
      ? schedule.specific_date
      : DAYS[Number(schedule.day_of_week)];
    [
      schedule.name,
      when || "—",
      formatTime(schedule.start_time) + "–" + formatTime(schedule.end_time),
      schedule.playlist_name || schedule.playlist_id,
      schedule.device_name || "Predeterminado",
      String(schedule.priority)
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });

    const actions = document.createElement("td");
    actions.className = "row-actions";
    actions.append(
      button("Probar", "test", schedule.id, false),
      button("Editar", "edit", schedule.id, false),
      button(schedule.enabled ? "Deshabilitar" : "Habilitar", "toggle", schedule.id, false),
      button("Eliminar", "delete", schedule.id, true)
    );
    row.append(actions);
    body.append(row);
  });
}

function listItem(titleText, detailText, active) {
  const item = document.createElement("div");
  item.className = "list-item";
  const text = document.createElement("div");
  const title = document.createElement("strong");
  const detail = document.createElement("small");
  title.textContent = titleText;
  detail.textContent = detailText || "";
  text.append(title, detail);
  item.append(text);
  if (active !== undefined) {
    const dot = document.createElement("span");
    dot.className = "dot " + (active ? "active" : "");
    item.append(dot);
  }
  return item;
}

function renderLibrary() {
  const playlists = byId("playlistList");
  const playlistSelect = byId("schedulePlaylist");
  playlists.replaceChildren();
  playlistSelect.replaceChildren();

  if (!state.playlists.length) {
    playlists.append(listItem("Sin playlists", "Conecta Spotify para cargarlas."));
    const empty = new Option("Conecta Spotify", "");
    empty.disabled = true;
    playlistSelect.add(empty);
  } else {
    state.playlists.forEach((item) => {
      playlists.append(listItem(item.name, item.owner + " · " + item.tracks_total + " canciones"));
      const option = new Option(item.name, item.id);
      option.dataset.name = item.name;
      playlistSelect.add(option);
    });
  }

  const devices = byId("deviceList");
  const deviceSelect = byId("scheduleDevice");
  devices.replaceChildren();
  deviceSelect.replaceChildren(new Option("Predeterminado", ""));
  if (!state.devices.length) {
    devices.append(listItem("Sin dispositivos", "Abre Spotify en un dispositivo."));
  } else {
    state.devices.forEach((item) => {
      const details = [item.type, item.volume_percent == null ? "" : "Volumen " + item.volume_percent + "%"]
        .filter(Boolean).join(" · ");
      devices.append(listItem(item.name, details, item.is_active));
      deviceSelect.add(new Option(item.name, item.name));
    });
  }
}

function renderHistory(events) {
  const history = byId("historyList");
  history.replaceChildren();
  if (!events.length) {
    history.append(listItem("Sin actividad reciente", "Los eventos aparecerán aquí."));
    return;
  }
  events.slice(0, 30).forEach((event) => {
    history.append(listItem(
      event.details || event.event_type || "Evento",
      [event.playlist_name, event.device_name, formatDate(event.timestamp)].filter(Boolean).join(" · ")
    ));
  });
}

async function loadAll() {
  const statusData = await api("/api/status");
  state.csrf = statusData.csrf_token || state.csrf;
  state.status = statusData;
  showApp();

  const results = await Promise.all([
    api("/api/schedules"),
    api("/api/playlists"),
    api("/api/devices")
  ]);
  state.schedules = results[0];
  state.playlists = results[1];
  state.devices = results[2];
  renderSchedules();
  renderLibrary();
  renderStatus();
}

async function refreshStatus() {
  try {
    const data = await api("/api/status");
    state.csrf = data.csrf_token || state.csrf;
    state.status = data;
    renderStatus();
  } catch (error) {
    if (!byId("appView").hidden) console.error(error);
  }
}

function updateKind() {
  const weekly = byId("scheduleKind").value === "weekly";
  byId("dayField").hidden = !weekly;
  byId("dateField").hidden = weekly;
  byId("scheduleDay").required = weekly;
  byId("scheduleDate").required = !weekly;
}

function openDialog(schedule) {
  byId("scheduleForm").reset();
  byId("scheduleId").value = schedule ? schedule.id : "";
  byId("dialogTitle").textContent = schedule ? "Editar horario" : "Nuevo horario";
  byId("scheduleName").value = schedule ? schedule.name : "";
  byId("scheduleKind").value = schedule ? schedule.kind : "weekly";
  byId("scheduleDay").value = String(schedule && schedule.day_of_week != null ? schedule.day_of_week : 0);
  byId("scheduleDate").value = schedule && schedule.specific_date ? schedule.specific_date : "";
  byId("scheduleStart").value = formatTime(schedule ? schedule.start_time : "08:00");
  byId("scheduleEnd").value = formatTime(schedule ? schedule.end_time : "09:00");
  byId("schedulePlaylist").value = schedule ? schedule.playlist_id : "";
  byId("scheduleDevice").value = schedule ? schedule.device_name : "";
  byId("schedulePriority").value = schedule ? schedule.priority : 0;
  byId("scheduleEnabled").checked = schedule ? schedule.enabled : true;
  byId("scheduleRandom").checked = schedule ? schedule.random_queue : false;
  byId("scheduleExplicit").checked = schedule ? schedule.skip_explicit : false;
  updateKind();
  byId("scheduleDialog").showModal();
}

function closeDialog() {
  byId("scheduleDialog").close();
}

function formPayload() {
  const weekly = byId("scheduleKind").value === "weekly";
  const selected = byId("schedulePlaylist").selectedOptions[0];
  return {
    name: byId("scheduleName").value.trim(),
    kind: byId("scheduleKind").value,
    day_of_week: weekly ? Number(byId("scheduleDay").value) : null,
    specific_date: weekly ? null : byId("scheduleDate").value,
    start_time: byId("scheduleStart").value,
    end_time: byId("scheduleEnd").value,
    playlist_id: byId("schedulePlaylist").value,
    playlist_name: selected ? selected.dataset.name || selected.textContent : "",
    device_name: byId("scheduleDevice").value,
    random_queue: byId("scheduleRandom").checked,
    skip_explicit: byId("scheduleExplicit").checked,
    enabled: byId("scheduleEnabled").checked,
    priority: Number(byId("schedulePriority").value || 0)
  };
}

function schedulePayload(schedule) {
  const copy = Object.assign({}, schedule);
  delete copy.id;
  return copy;
}

byId("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  byId("loginError").textContent = "";
  try {
    const result = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ password: byId("password").value })
    });
    state.csrf = result.csrf_token;
    byId("password").value = "";
    await loadAll();
  } catch (error) {
    byId("loginError").textContent = error.message;
  }
});

byId("logoutButton").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); } finally { showLogin(); }
});

byId("refreshButton").addEventListener("click", async () => {
  try { await loadAll(); toast("Datos actualizados."); } catch (error) { toast(error.message, true); }
});

byId("automationButton").addEventListener("click", async () => {
  const action = state.status.automation_paused ? "resume" : "pause";
  try {
    await api("/api/automation/" + action, { method: "POST" });
    await refreshStatus();
  } catch (error) { toast(error.message, true); }
});

byId("newScheduleButton").addEventListener("click", () => openDialog(null));
byId("closeDialogButton").addEventListener("click", closeDialog);
byId("cancelDialogButton").addEventListener("click", closeDialog);
byId("scheduleKind").addEventListener("change", updateKind);

byId("scheduleForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = byId("scheduleId").value;
  try {
    await api(id ? "/api/schedules/" + id : "/api/schedules", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(formPayload())
    });
    closeDialog();
    await loadAll();
    toast(id ? "Horario actualizado." : "Horario creado.");
  } catch (error) { toast(error.message, true); }
});

byId("scheduleRows").addEventListener("click", async (event) => {
  const target = event.target.closest("button[data-action]");
  if (!target) return;
  const schedule = state.schedules.find((item) => String(item.id) === target.dataset.id);
  if (!schedule) return;

  try {
    if (target.dataset.action === "edit") {
      openDialog(schedule);
      return;
    }
    if (target.dataset.action === "test") {
      const result = await api("/api/schedules/" + schedule.id + "/test", { method: "POST" });
      toast("Reproduciendo en " + result.device + ".");
      return;
    }
    if (target.dataset.action === "toggle") {
      const payload = schedulePayload(schedule);
      payload.enabled = !payload.enabled;
      await api("/api/schedules/" + schedule.id, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
    }
    if (target.dataset.action === "delete") {
      if (!window.confirm("¿Eliminar “" + schedule.name + "”?")) return;
      await api("/api/schedules/" + schedule.id, { method: "DELETE" });
    }
    await loadAll();
  } catch (error) { toast(error.message, true); }
});

loadAll().catch(() => showLogin());
