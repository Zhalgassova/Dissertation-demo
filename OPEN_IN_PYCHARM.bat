@echo off
setlocal EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PYCHARM_EXE="

for /f "delims=" %%I in ('powershell -NoProfile -Command "$candidates = @(); $candidates += Get-ChildItem \"$env:LOCALAPPDATA\Programs\" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'PyCharm*' } | ForEach-Object { Join-Path $_.FullName 'bin\\pycharm64.exe' }; $candidates += Get-ChildItem \"$env:ProgramFiles\JetBrains\" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'PyCharm*' } | ForEach-Object { Join-Path $_.FullName 'bin\\pycharm64.exe' }; $candidates += Get-ChildItem \"$env:LOCALAPPDATA\JetBrains\Toolbox\apps\" -Recurse -Filter pycharm64.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }; $candidates += Get-ChildItem \"$env:USERPROFILE\AppData\Local\JetBrains\Toolbox\apps\" -Recurse -Filter pycharm64.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }; $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1"') do (
    set "PYCHARM_EXE=%%I"
)

if not defined PYCHARM_EXE (
    echo PyCharm табылмады.
    echo Мына папканы PyCharm-та manually ашыңыз:
    echo %PROJECT_DIR%
    pause
    exit /b 1
)

start "" "%PYCHARM_EXE%" "%PROJECT_DIR%"
exit /b 0
