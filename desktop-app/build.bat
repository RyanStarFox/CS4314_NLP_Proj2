@echo off
REM Build script for Smart Course Assistant Desktop App (Windows)
REM This script builds the Python backend and Tauri app for Windows

setlocal enabledelayedexpansion

echo =============================================
echo 🚀 Smart Course Assistant - Desktop Build
echo =============================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DESKTOP_APP_DIR=%SCRIPT_DIR%"

echo 📍 Project Root: %PROJECT_ROOT%
echo 📁 Desktop App Dir: %DESKTOP_APP_DIR%
echo.

REM Step 1: Build Python Backend
echo =============================================
echo 📦 Step 1: Building Python Backend...
echo =============================================

cd /d "%PROJECT_ROOT%"

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Install PyInstaller if needed
pip install pyinstaller --quiet

REM Run PyInstaller
echo 🔨 Running PyInstaller...
cd /d "%DESKTOP_APP_DIR%"
pyinstaller --clean --noconfirm python-backend.spec

REM Move output to python-dist
echo 📂 Moving Python build to python-dist...
if exist "python-dist" rmdir /s /q python-dist
move dist\python-backend python-dist

echo ✅ Python backend built successfully!
echo.

REM Step 2: Build Tauri App
echo =============================================
echo 🦀 Step 2: Building Tauri App...
echo =============================================

cd /d "%DESKTOP_APP_DIR%"

REM Install npm dependencies
echo 📦 Installing npm dependencies...
call npm install

REM Build Tauri app
echo 🔨 Building Tauri app...
call npm run tauri build

echo.
echo =============================================
echo ✅ Build Complete!
echo =============================================
echo.
echo 📦 Output files are in: %DESKTOP_APP_DIR%\src-tauri\target\release\bundle\
echo.

REM List output files
echo 🪟 Windows outputs:
dir /b src-tauri\target\release\bundle\msi\ 2>nul || echo   (no msi found)
dir /b src-tauri\target\release\bundle\nsis\ 2>nul || echo   (no exe installer found)

echo.
echo 🎉 Done!
pause
