@echo off
setlocal enabledelayedexpansion
title BajaMusica - Build

echo.
echo  =====================================================
echo    BajaMusica  ^|  Constructor de ejecutable Windows
echo  =====================================================
echo.

REM ── 1. Verificar Python ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en el PATH.
    echo.
    echo   Instalar Python 3.10 o superior desde https://python.org
    echo   Al instalar, marcar la opcion "Add Python to PATH".
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%
echo.

REM ── 2. Entorno virtual de build ─────────────────────────────────────────
echo [1/5] Preparando entorno virtual de build...
if exist .venv-build (
    echo       Limpiando entorno anterior...
    rmdir /s /q .venv-build
)
python -m venv .venv-build
if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
call .venv-build\Scripts\activate.bat
echo       Listo.
echo.

REM ── 3. Dependencias ─────────────────────────────────────────────────────
echo [2/5] Instalando dependencias de Python...
python -m pip install --upgrade pip --quiet
if errorlevel 1 goto :pip_error
pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 goto :pip_error
echo       Listo.
echo.
goto :ffmpeg_step

:pip_error
echo [ERROR] Fallo al instalar dependencias. Verificar conexion a internet.
pause
exit /b 1

REM ── 4. ffmpeg ────────────────────────────────────────────────────────────
:ffmpeg_step
echo [3/5] Verificando ffmpeg para Windows...
if exist ffmpeg-bin\ffmpeg.exe (
    echo       Ya descargado, omitiendo.
) else (
    python _get_ffmpeg.py
    if errorlevel 1 (
        echo [ERROR] No se pudo descargar ffmpeg. Verificar conexion a internet.
        pause
        exit /b 1
    )
)
echo.

REM ── 5. PyInstaller ──────────────────────────────────────────────────────
echo [4/5] Construyendo ejecutable con PyInstaller...
if exist dist\bajamusica rmdir /s /q dist\bajamusica
if exist build rmdir /s /q build
pyinstaller --clean --noconfirm bajamusica.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller fallo. Ver mensajes de arriba.
    pause
    exit /b 1
)
echo.

REM ── 6. Limpieza ──────────────────────────────────────────────────────────
echo [5/5] Limpiando archivos temporales de build...
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
