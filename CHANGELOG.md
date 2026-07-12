# Cambios de Spotify Scheduler Pro

Esta edición conserva el propósito principal del repositorio original: programar
la reproducción de playlists de Spotify. La implementación fue reorganizada y
ampliada con:

1. Arquitectura modular.
2. Motor independiente de horarios.
3. Reglas semanales recurrentes.
4. Reglas por fecha específica.
5. Horarios que cruzan medianoche.
6. Prioridades y aviso de conflictos.
7. Almacenamiento SQLite.
8. Credenciales mediante keyring.
9. Bandeja del sistema.
10. Inicio automático con Windows.
11. Prevención opcional de suspensión.
12. Cola aleatoria con filtrado de canciones recientes y artistas consecutivos.
13. Importación/exportación JSON.
14. Historial local de eventos.
15. Logs rotativos.
16. Tests automatizados.
17. Script para construir un EXE con PyInstaller.

La licencia MIT y atribución del autor original se mantienen.


## Correcciones previas a publicación

- Exclusión real de canciones recientes en Random Queue.
- Detección de conflictos con precisión de segundos.
- Claves foráneas SQLite habilitadas en cada conexión.
- Estado OAuth atómico, tokens en keyring y llamadas API serializadas.
- Refrescos del dashboard sin solapamiento.
- CI y compilación Windows mediante GitHub Actions.
