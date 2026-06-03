# BajaMusica — Instalación en Windows

## Requisitos

- Windows 10 o superior (64-bit)
- **Python 3.10+** instalado desde [python.org](https://www.python.org/downloads/)
  - Al instalar, marcar la opción **"Add Python to PATH"**
- Conexión a internet durante el build (descarga ffmpeg ~90 MB, una sola vez)

---

## Cómo construir el ejecutable

1. Clonar o descargar el repositorio (rama `windows-exe`)
2. Abrir una terminal (CMD o PowerShell) en la carpeta del proyecto
3. Ejecutar:

```
build.bat
```

El script hace todo solo:

| Paso | Qué hace |
|------|----------|
| 1 | Crea un entorno virtual de build aislado (`.venv-build\`) |
| 2 | Instala Flask, yt-dlp, mutagen, musicbrainzngs y PyInstaller |
| 3 | Descarga `ffmpeg.exe` y `ffprobe.exe` desde los builds oficiales de yt-dlp |
| 4 | Genera el bundle con PyInstaller |
| 5 | Limpia archivos temporales |

Al terminar, la carpeta `dist\bajamusica\` contiene el ejecutable listo para usar.

---

## Cómo distribuir / instalar en otra PC

No hay instalador. Simplemente:

1. Comprimir la carpeta `dist\bajamusica\` en un ZIP
2. Copiarla a la máquina destino y descomprimirla donde se quiera
3. Hacer doble clic en `bajamusica.exe`

La aplicación abre el navegador automáticamente en `http://127.0.0.1:5000`.  
La PC destino **no necesita Python ni ninguna dependencia adicional**.

---

## Notas

- **Puerto ocupado:** si el puerto 5000 ya está en uso, la app muestra un diálogo de error. Cerrar la aplicación que lo ocupa y volver a intentar.
- **Carpeta de descarga por defecto:** `C:\Users\<usuario>\Music\YT-Downloads`. Se puede cambiar desde la interfaz.
- **Historial de descargas:** se guarda en `%APPDATA%\bajamusica\history.json`.
- **ffmpeg:** ya viene incluido en el bundle; no hace falta instalarlo por separado.
- **Antivirus:** algunos antivirus pueden marcar ejecutables generados con PyInstaller como sospechosos (falso positivo). Agregar una excepción para la carpeta `dist\bajamusica\` si es necesario.
- **Re-build:** si se actualiza el código fuente, volver a correr `build.bat`. La carpeta `ffmpeg-bin\` ya existe y se reutiliza (el paso de descarga se saltea automáticamente).
