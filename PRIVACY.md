# Privacidad

Spoxu Web es una aplicación autohospedada para un solo usuario. No incluye
telemetría, publicidad ni servicios de análisis.

## Datos almacenados

La instalación guarda en el volumen privado /data:

- horarios y preferencias de automatización;
- historial de eventos de reproducción;
- un token OAuth de Spotify cifrado con Fernet.

La contraseña de acceso se configura únicamente como hash Argon2. El Client
Secret, la clave de sesión y la clave de cifrado se reciben mediante variables
o secretos del servidor y no se envían al navegador.

## Comunicaciones

Spoxu se comunica con la API oficial de Spotify para autorización, playlists,
dispositivos y control de reproducción. La interfaz web se comunica únicamente
con la misma instalación de Spoxu. No se envían datos a terceros adicionales.

El operador de la instalación es responsable de los registros del proxy HTTPS,
las copias de seguridad y la protección del servidor.

## Eliminación

Desconectar Spotify desde Spoxu elimina el archivo de token cifrado. Para
eliminar todos los datos, detén el contenedor y elimina el volumen o carpeta
data. Revoca también el acceso de la aplicación desde la configuración de tu
cuenta de Spotify.
