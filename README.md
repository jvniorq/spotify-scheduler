# Spotify Scheduler Pro

Edición modular y ampliada, inspirada en el proyecto original
[`sandrzejewskipl/spotify-scheduler`](https://github.com/sandrzejewskipl/spotify-scheduler).

## Uso permitido y limitaciones

Esta aplicación es exclusivamente para uso personal y no comercial. Spotify no
permite reproducir su servicio públicamente en restaurantes, colegios, bares,
tiendas u otros negocios, incluso con una cuenta Premium. Consulta la política
de uso público/comercial de Spotify y su Developer Policy.

Este proyecto no está afiliado, patrocinado ni aprobado por Spotify.

## Qué incorpora

- Programación semanal recurrente y por fecha específica.
- Intervalos que atraviesan medianoche, por ejemplo `22:00 → 02:00`.
- Detección básica de conflictos de horarios.
- Persistencia en SQLite.
- OAuth con Spotify Web API mediante Spotipy.
- Credenciales sensibles almacenadas con `keyring`.
- Selección de dispositivo Spotify Connect.
- Cola aleatoria que intenta evitar artistas consecutivos y canciones recientes.
- Inicio, pausa y prueba inmediata de una playlist.
- Importación y exportación de playlists como JSON.
- Inicio automático con Windows.
- Minimización a la bandeja del sistema.
- Registro rotativo de eventos y errores.
- Pruebas unitarias del motor de horarios.

## Requisitos

- Windows 10/11, Linux o macOS.
- Python 3.11 o 3.12.
- Spotify Premium.
- Spotify Desktop o un dispositivo Spotify Connect activo.
- Una aplicación creada en Spotify Developer Dashboard.
- Redirect URI configurado exactamente como:

```text
http://127.0.0.1:23918
```

## Instalación en Windows

```powershell
cd C:\Dev
git clone <TU_REPOSITORIO_O_COPIA>
cd spotify-scheduler-pro
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m spotify_scheduler_pro
```

También puedes ejecutar:

```powershell
.\run_windows.ps1
```

## Primer uso

1. Crea una app en Spotify Developer Dashboard.
2. Activa **Web API**.
3. Registra `http://127.0.0.1:23918` como Redirect URI.
4. Abre la pestaña **Ajustes**.
5. Ingresa `Client ID` y `Client Secret`.
6. Pulsa **Guardar y autorizar**.
7. Autoriza la aplicación en el navegador.
8. Actualiza la lista de dispositivos.
9. Crea un horario en la pestaña **Horarios**.

## Compilar a EXE

```powershell
.\build_exe.ps1
```

El ejecutable se generará dentro de:

```text
dist\SpotifySchedulerPro\SpotifySchedulerPro.exe
```

## Datos locales

La aplicación usa la carpeta estándar de datos de usuario:

- Windows: `%LOCALAPPDATA%\SpotifySchedulerPro`
- Linux: `~/.local/share/SpotifySchedulerPro`
- macOS: `~/Library/Application Support/SpotifySchedulerPro`

Allí se almacenan:

- `scheduler.db`
- `config.json`
- `logs/app.log`

El `Client Secret` no se almacena dentro de `config.json`; se guarda mediante el
almacén seguro de credenciales del sistema cuando `keyring` está disponible.

## Nota importante

Esta edición se entrega como base completa de desarrollo. El código fue
verificado mediante compilación estática y pruebas locales del motor de
horarios, pero la autenticación y reproducción reales requieren tus
credenciales, Spotify Premium, conexión a Internet y un dispositivo disponible.


## Automatización en GitHub

Los workflows incluidos ejecutan Ruff y pytest en GitHub Actions y permiten
construir el ejecutable Windows manualmente desde la pestaña Actions, sin
instalar dependencias en el equipo usado para administrar el repositorio.

Los tokens OAuth y el Client Secret se guardan con keyring. Al cerrar sesión se
elimina también cualquier caché OAuth heredada.
