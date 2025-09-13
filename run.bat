@echo off
setlocal
title AI-Project-PDF Launcher

REM === Projekt-Root setzen ===
cd /d C:\Users\gamin\AI-Project-PDF

REM === Optional: eigenes venv aktivieren (wenn du eins verwendest) ===
REM call "%CD%\venv\Scripts\activate.bat"

REM === Python fest verdrahtet (311). Wenn nicht vorhanden, fallback auf 'python' im PATH ===
set "PYEXE=C:\Program Files\Python311\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo ===========================================
echo   AI-Project-PDF - Modus-Auswahl
echo ===========================================
echo [1] clean_for_tts
echo [2] summary
echo [3] tts_passthrough
echo.
set "AI_MODE="
set /p choice="Bitte wähle den Modus (1-3): "

if "%choice%"=="1" set "AI_MODE=clean_for_tts"
if "%choice%"=="2" set "AI_MODE=summary"
if "%choice%"=="3" set "AI_MODE=tts_passthrough"

if not defined AI_MODE (
  echo.
  echo Ungueltige Auswahl. Beende.
  goto :end
)

echo.
echo Gewaehlter Modus: %AI_MODE%
echo.

REM === Check: LM Studio Server Port 1234 erreichbar? (nur Hinweis) ===
echo Pruefe LM Studio (Port 1234) ...
powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('localhost',1234); 'OK - LM Studio erreichbar' } catch { 'WARNUNG: Kein LM Studio Server erreichbar!' }"
echo.

REM === Optional: Tesseract kurz pruefen (nur Hinweis) ===
powershell -NoProfile -Command "try { & tesseract --version ^> $null; 'Tesseract gefunden' } catch { 'Hinweis: Tesseract nicht im PATH' }"
echo.

REM === Start: als Modul, damit 'program' als Package funktioniert ===
set "PYTHONUNBUFFERED=1"
set "AI_MODE=%AI_MODE%"
"%PYEXE%" -m program.main

:end
echo.
pause
endlocal
