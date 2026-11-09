@echo off
setlocal
cd /d "%~dp0"
echo Bloodborne: Reawakened - Windows EXE builder
echo.
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)
%PY% --version || goto :fail
%PY% -m pip install --upgrade pyinstaller || goto :fail
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "Reawakened_Installer" reawakened_installer.py || goto :fail
if not exist dist\Reawakened_Installer.exe goto :fail
if not exist RELEASE mkdir RELEASE
copy /Y dist\Reawakened_Installer.exe RELEASE\Reawakened_Installer.exe >nul
if exist patch_package\manifest.json (
  if not exist RELEASE\patch_package mkdir RELEASE\patch_package
  xcopy /E /I /Y patch_package RELEASE\patch_package >nul
)
if exist xdelta3.exe copy /Y xdelta3.exe RELEASE\xdelta3.exe >nul
echo.
echo EXE created: %~dp0RELEASE\Reawakened_Installer.exe
echo Include your approved patch_package folder and xdelta3.exe in RELEASE before distributing.
echo.
pause
exit /b 0
:fail
echo.
echo Build failed. Review the error messages above.
pause
exit /b 1
