"""
Descarga ffmpeg y ffprobe para Windows desde los builds de yt-dlp.
Llamado por build.bat durante la construcción del ejecutable.
"""
import io
import os
import shutil
import sys
import urllib.request
import zipfile

URL = (
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
DEST = "ffmpeg-bin"
NEEDED = {"ffmpeg.exe", "ffprobe.exe"}


def main():
    os.makedirs(DEST, exist_ok=True)

    print("      Conectando a GitHub...")
    try:
        with urllib.request.urlopen(URL, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunks = []
            while True:
                chunk = resp.read(1 << 16)  # 64 KB
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    mb = downloaded / 1_048_576
                    print(f"\r      Descargando... {pct}% ({mb:.1f} MB)", end="", flush=True)
            print()
            data = b"".join(chunks)
    except Exception as exc:
        print(f"\n      ERROR al descargar: {exc}")
        sys.exit(1)

    print("      Extrayendo binarios...")
    found = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            basename = os.path.basename(name)
            if basename in NEEDED:
                target = os.path.join(DEST, basename)
                with z.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                print(f"      -> {basename}")
                found.add(basename)

    missing = NEEDED - found
    if missing:
        print(f"      ERROR: No se encontraron: {', '.join(missing)}")
        sys.exit(1)

    print("      ffmpeg listo.")


if __name__ == "__main__":
    main()
