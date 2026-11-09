@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 reawakened_installer.py
) else (
  python reawakened_installer.py
)
if errorlevel 1 (
  echo.
  echo Could not launch the installer. Install Python 3 with Tkinter, or build the EXE using BUILD_WINDOWS_EXE.bat.
  pause
)
