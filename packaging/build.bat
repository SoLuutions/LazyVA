@echo off
setlocal enabledelayedexpansion

pushd "%~dp0.." || (
    echo [ERROR] Could not locate the project root.
    exit /b 1
)

echo =======================================================
echo          LazyVA Windows SaaS Production Build
echo =======================================================

REM 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    pause
    popd
    exit /b 1
)

REM 2. Install / verify dependencies
echo [*] Checking dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed!
    pause
    popd
    exit /b 1
)

REM 3. Build PyInstaller Executable
echo [*] Compiling LazyVA with PyInstaller...
python packaging\build_exe.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    popd
    exit /b 1
)

REM 4. Locate Inno Setup Compiler (ISCC.exe)
echo [*] Searching for Inno Setup 6...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC (
    echo [*] Compiling Inno Setup Installer with "!ISCC!"...
    "!ISCC!" "%~dp0LazyVA_Setup.iss"
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed!
        pause
        popd
        exit /b 1
    ) else (
        echo [SUCCESS] Windows Installer generated in dist\LazyVA_Setup_v1.0.0.exe!
    )
) else (
    echo [NOTE] Inno Setup (ISCC.exe) was not found in standard directories.
    echo        The standalone application is ready in dist\LazyVA\LazyVA.exe.
    echo        To build the single-file installer, download Inno Setup from https://jrsoftware.org/isdl.php
)

echo =======================================================
echo                   Build Completed!
echo =======================================================
echo Run the fresh build from: dist\LazyVA\LazyVA.exe
popd
pause
