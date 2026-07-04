@echo off
setlocal enabledelayedexpansion
title BajaMusica - Build

echo.
echo  =====================================================
echo    BajaMusica  ^|  Constructor de ejecutable Windows
echo  =====================================================
echo.

REM ── 1. Verificar uv ─────────────────────────────────────────────────────
uv --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv no encontrado en el PATH.
    echo.
    echo   Instalar uv con PowerShell:
    echo     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo   o con winget:
    echo     winget install --id=astral-sh.uv -e
    echo.
    echo   No hace falta instalar Python: uv baja solo la version que
    echo   pide el proyecto ^(.python-version^).
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('uv --version 2^>^&1') do set UVVER=%%v
echo [OK] uv %UVVER%
echo.

REM ── 2. Dependencias (uv crea el entorno y baja Python si hace falta) ────
echo [1/4] Instalando dependencias de Python...
uv sync --locked --no-dev --group build
if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias. Verificar conexion a internet.
    pause
    exit /b 1
)
echo       Listo.
echo.

REM ── 3. ffmpeg ────────────────────────────────────────────────────────────
echo [2/4] Verificando ffmpeg para Windows...
if exist ffmpeg-bin\ffmpeg.exe (
    echo       Ya descargado, omitiendo.
) else (
    uv run --no-sync python _get_ffmpeg.py
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar ffmpeg. Verificar conexion a internet.
        pause
        exit /b 1
    )
)
echo.

REM ── 4. PyInstaller ──────────────────────────────────────────────────────
echo [3/4] Construyendo ejecutable con PyInstaller...
if exist dist\bajamusica rmdir /s /q dist\bajamusica
if exist build rmdir /s /q build
uv run --no-sync pyinstaller --clean --noconfirm bajamusica.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller fallo. Ver mensajes de arriba.
    pause
    exit /b 1
)
echo.

REM ── 5. Limpieza ──────────────────────────────────────────────────────────
echo [4/4] Limpiando archivos temporales de build...
if exist build rmdir /s /q build
echo.

echo  =====================================================
echo    Build exitoso!
echo.
echo    Ejecutable: dist\bajamusica\bajamusica.exe
echo.
echo    Llevar la carpeta completa  dist\bajamusica\
echo    a la maquina destino y ejecutar bajamusica.exe
echo  =====================================================
echo.
pause
