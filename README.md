
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
