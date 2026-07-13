# Spoxu Web

**Automatización musical personal, privada y real desde el navegador.**

Spoxu Web ejecuta en un servidor el mismo motor de horarios de la edición de escritorio.
No necesitas descargar ni ejecutar un EXE: abres una URL HTTPS, inicias sesión con tu
contraseña privada y autorizas tu propia cuenta de Spotify.

> Spoxu es independiente y no está afiliado, patrocinado ni respaldado por Spotify.

## Automatización conservada

- Horarios semanales, por fecha y nocturnos como 22:00–02:00.
- Prioridades, superposiciones y detección de conflictos.
- Pausa automática fuera del horario y selección de Spotify Connect.
- Prueba inmediata de playlists.
- Random Queue, exclusión de canciones recientes y separación de artistas.
- Omisión opcional de canciones explícitas e historial de eventos.

La web no crea reproducciones falsas, no usa múltiples cuentas y no descarga música.
Controla mediante la API oficial un dispositivo Spotify Connect del único usuario.

## Arquitectura privada

- Navegador: interfaz minimalista glass.
- Servidor FastAPI: sesión privada, OAuth y API.
- Worker único: comprueba los horarios cada tres segundos.
- SQLite: horarios e historial en /data.
- Token cifrado: el token de Spotify nunca se envía al navegador.

Cerrar el navegador no detiene los horarios. El servidor debe seguir encendido y debe
existir al menos un dispositivo Spotify Connect disponible.

## Requisitos

- Servidor con Docker Engine y Docker Compose v2.
- Cuenta Spotify Premium y aplicación propia en Spotify Developer Dashboard.
- Dispositivo Spotify Connect.
- HTTPS mediante proxy inverso o acceso por VPN privada.

GitHub Pages no es suficiente: Spoxu necesita un proceso privado persistente.

## Configuración

Copia .env.example a .env. Nunca publiques ese archivo en GitHub.

    SPOXU_ENVIRONMENT=production
    SPOXU_BASE_URL=https://spoxu.example.com
    SPOXU_DATA_DIR=/data
    SPOXU_TIMEZONE=America/Lima
    SPOXU_COOKIE_SECURE=true
    SPOXU_AUTOMATION_ENABLED=true
    SPOXU_SESSION_SECRET=una-clave-aleatoria-de-al-menos-32-caracteres
    SPOXU_ADMIN_PASSWORD_HASH=un-hash-argon2id
    SPOXU_TOKEN_ENCRYPTION_KEY=una-clave-fernet
    SPOXU_SPOTIFY_CLIENT_ID=tu-client-id
    SPOXU_SPOTIFY_CLIENT_SECRET=tu-client-secret
    SPOXU_SPOTIFY_REDIRECT_URI=https://spoxu.example.com/oauth/spotify/callback

En Spotify Developer Dashboard registra exactamente la misma Redirect URI. En producción
debe utilizar HTTPS.

## Ejecutar

    docker compose up -d --build

El puerto se publica solo en 127.0.0.1:8000. Coloca un proxy HTTPS o una VPN delante.
No publiques directamente el puerto 8000 y no aumentes las réplicas: esta edición usa
SQLite y un único worker para una instalación personal.

## Seguridad

- Contraseña administrativa almacenada como hash Argon2.
- Cookie HttpOnly, Secure y SameSite=Lax.
- Protección CSRF en operaciones que modifican estado.
- Client Secret y tokens exclusivamente en el servidor.
- Token cifrado con Fernet en /data/spotify.token.
- CSP, bloqueo de iframes y permisos sensibles desactivados.
- Contenedor sin privilegios y filesystem de solo lectura.
- Sin telemetría.

Protege y respalda la carpeta data. Si un secreto se expone, revócalo y genera uno nuevo.

## Pruebas

    python -m pip install -e ".[web,dev]"
    python -m ruff check .
    python -m pytest -q
    docker build -t spoxu-web:test .

GitHub Actions ejecuta estas comprobaciones sin credenciales reales de Spotify.

## Edición de escritorio

El código Tkinter y el constructor del EXE se conservan temporalmente para mantener el
historial. Spoxu Web no necesita ese ejecutable.

## Uso personal

Spoxu Web es privado, de un solo usuario y no comercial. No debe emplearse para
reproducción pública, negocios, restaurantes, colegios, tiendas o eventos.

Consulta [Spotify para uso público o comercial](https://support.spotify.com/us-es/article/spotify-public-commercial-use/)
y la [Spotify Developer Policy](https://developer.spotify.com/policy).

## Origen y licencia

Spoxu deriva de [sandrzejewskipl/spotify-scheduler](https://github.com/sandrzejewskipl/spotify-scheduler).
Se mantienen la licencia MIT y la atribución a Szymon Andrzejewski.
