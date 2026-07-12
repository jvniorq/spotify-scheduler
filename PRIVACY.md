# Privacidad

Spotify Scheduler Pro es una aplicación de escritorio para uso personal y no
comercial. No mantiene un servidor propio ni envía telemetría.

La configuración no sensible, los horarios, el historial de automatización y
los logs se guardan localmente en la carpeta de datos de la aplicación. El
Client Secret y los tokens OAuth se almacenan mediante keyring en el almacén de
credenciales del sistema.

Cerrar la sesión OAuth elimina los tokens y cualquier caché heredada. Para
eliminar todos los datos, cierra la aplicación y borra su carpeta local de
datos. Las solicitudes musicales se envían directamente a la API de Spotify
según los permisos autorizados por el usuario.
